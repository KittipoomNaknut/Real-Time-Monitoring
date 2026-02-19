"""
Renderer — Background caching and drawing pipeline.

Architecture:
=============
    _bg_cache (static)     ──► np.copyto ──► _canvas (per-frame)
    [grid, labels, border]                    [+ series lines]
                                              [+ legend]
                                              [+ tooltips]
                                              [+ FPS/status]

The background is rebuilt only when y-limits change (bg_dirty flag).
This avoids redrawing ~20 grid lines + labels every frame, giving
a ~3-5x speedup over naive full redraw.
"""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .config import PlotConfig, AutoScaleMode
from .colors import Theme, get_theme
from .series import Series


class Renderer:
    """Stateful renderer with background caching."""

    def __init__(self, config: PlotConfig, theme: Optional[Theme] = None):
        self._config = config
        self._theme = theme or get_theme(config.theme)
        self._line_type = cv2.LINE_AA if config.antialiased else cv2.LINE_8

        # Buffers
        self._bg_cache: Optional[np.ndarray] = None
        self._bg_dirty = True
        self._canvas = np.zeros(
            (config.height, config.width, 3), dtype=np.uint8
        )

        # Y-axis state
        self._display_y_min = config.y_min
        self._display_y_max = config.y_max
        self._target_y_min = config.y_min
        self._target_y_max = config.y_max

    @property
    def canvas(self) -> np.ndarray:
        return self._canvas

    @property
    def theme(self) -> Theme:
        return self._theme

    @theme.setter
    def theme(self, t: Theme) -> None:
        self._theme = t
        self._bg_dirty = True

    def mark_dirty(self) -> None:
        """Force background rebuild on next render."""
        self._bg_dirty = True

    def set_y_limits(self, y_min: float, y_max: float) -> None:
        self._config.y_min = y_min
        self._config.y_max = y_max
        self._target_y_min = y_min
        self._target_y_max = y_max
        self._display_y_min = y_min
        self._display_y_max = y_max
        self._bg_dirty = True

    # ──────────────────────────────────────────────────────
    # Main render pipeline
    # ──────────────────────────────────────────────────────
    def render(
        self,
        series_map: dict[str, Series],
        series_order: list[str],
        fps: float = 0.0,
        paused: bool = False,
        mouse_pos: Optional[tuple[int, int]] = None,
        status_text: str = "",
    ) -> np.ndarray:
        """Full render pipeline. Returns canvas (H×W×3 uint8 BGR)."""

        cfg = self._config
        t = self._theme

        # 1. Auto-scale
        if cfg.auto_scale != AutoScaleMode.FIXED:
            self._compute_auto_scale(series_map)

        # 2. Smooth Y-axis transition
        if cfg.smooth_auto_scale:
            self._lerp_y_axis()

        # 3. Rebuild background if dirty
        if self._bg_dirty or self._bg_cache is None:
            self._rebuild_background()
            self._bg_dirty = False

        # 4. Blit background
        np.copyto(self._canvas, self._bg_cache)

        px, py = cfg.plot_x, cfg.plot_y
        pw, ph = cfg.plot_w, cfg.plot_h

        # 5. Draw series
        for name in series_order:
            if name in series_map:
                series = series_map[name]
                if series.count >= 2:
                    self._draw_series(series, px, py, pw, ph)

        # 6. Legend
        if cfg.show_legend and len(series_map) > 1:
            self._draw_legend(series_map, series_order, px + 10, py + 10)

        # 7. Current values
        self._draw_current_values(series_map, series_order, px + pw, py)

        # 8. Mouse tooltip
        if cfg.enable_mouse_tooltip and mouse_pos is not None:
            self._draw_tooltip(series_map, series_order, mouse_pos, px, py, pw, ph)

        # 9. FPS + status bar
        self._draw_status_bar(fps, paused, status_text)

        return self._canvas

    # ──────────────────────────────────────────────────────
    # Background
    # ──────────────────────────────────────────────────────
    def _rebuild_background(self) -> None:
        cfg = self._config
        t = self._theme
        bg = np.zeros((cfg.height, cfg.width, 3), dtype=np.uint8)
        bg[:] = t.bg

        px, py = cfg.plot_x, cfg.plot_y
        pw, ph = cfg.plot_w, cfg.plot_h
        y_min, y_max = self._display_y_min, self._display_y_max
        y_range = y_max - y_min if y_max != y_min else 1.0

        # Vertical grid (minor)
        for x in range(0, pw + 1, cfg.grid_x_spacing):
            cv2.line(bg, (px + x, py), (px + x, py + ph),
                     t.grid_minor, 1, self._line_type)

        # Horizontal grid + Y labels
        n_div = cfg.grid_y_divisions
        for i in range(n_div + 1):
            frac = i / n_div
            y_abs = py + int(frac * ph)

            cv2.line(bg, (px, y_abs), (px + pw, y_abs),
                     t.grid_major, 1, self._line_type)

            y_val = (y_max - frac * y_range) if cfg.invert_y else (y_min + frac * y_range)
            label = _format_number(y_val)
            cv2.putText(bg, label, (5, y_abs + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                        t.axis_label, 1, self._line_type)

        # Zero line
        if cfg.show_zero_line and y_min < 0 < y_max:
            zero_frac = (y_max / y_range) if cfg.invert_y else (-y_min / y_range)
            zero_y = py + int(zero_frac * ph)
            cv2.line(bg, (px, zero_y), (px + pw, zero_y),
                     t.grid_center, 2, self._line_type)

        # Border
        cv2.rectangle(bg, (px, py), (px + pw, py + ph),
                      t.border, 1, self._line_type)

        # Title
        if cfg.title:
            ts = cv2.getTextSize(cfg.title, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
            tx = px + (pw - ts[0]) // 2
            cv2.putText(bg, cfg.title, (tx, py - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        t.title, 1, self._line_type)

        self._bg_cache = bg

    # ──────────────────────────────────────────────────────
    # Series drawing
    # ──────────────────────────────────────────────────────
    def _draw_series(self, series: Series, px: int, py: int,
                     pw: int, ph: int) -> None:
        data = series.get_data()
        n = len(data)
        if n < 2:
            return

        cfg = self._config
        color = series.config.color
        y_min, y_max = self._display_y_min, self._display_y_max
        y_range = y_max - y_min if y_max != y_min else 1.0

        # Vectorized coordinate mapping
        x_coords = np.linspace(px, px + pw, n, dtype=np.float64)
        y_norm = np.clip((data - y_min) / y_range, 0.0, 1.0)

        if cfg.invert_y:
            y_coords = py + (1.0 - y_norm) * ph
        else:
            y_coords = py + y_norm * ph

        # NaN-safe point array
        valid = ~np.isnan(data)
        y_draw = np.where(valid, y_coords, 0)
        points = np.column_stack((x_coords, y_draw)).astype(np.int32)

        # Segment by NaN gaps
        segments = []
        seg: list = []
        for i in range(n):
            if valid[i]:
                seg.append(points[i])
            else:
                if len(seg) >= 2:
                    segments.append(np.array(seg))
                seg = []
        if len(seg) >= 2:
            segments.append(np.array(seg))

        for s in segments:
            cv2.polylines(self._canvas, [s], False,
                          color, series.config.line_width,
                          self._line_type)

        # Latest point dot with glow
        if series.config.show_dot and valid[-1]:
            pt = (int(x_coords[-1]), int(y_coords[-1]))

            if series.config.show_glow:
                glow = tuple(max(0, min(255, c // 3)) for c in color)
                cv2.circle(self._canvas, pt,
                           series.config.dot_radius + 6,
                           glow, -1, self._line_type)

            cv2.circle(self._canvas, pt,
                       series.config.dot_radius,
                       color, -1, self._line_type)
            cv2.circle(self._canvas, pt, 2,
                       (255, 255, 255), -1, self._line_type)

    # ──────────────────────────────────────────────────────
    # Legend
    # ──────────────────────────────────────────────────────
    def _draw_legend(self, series_map: dict, order: list,
                     x: int, y: int) -> None:
        t = self._theme
        entries = []
        for name in order:
            if name in series_map:
                s = series_map[name]
                entries.append((s.config.label or name, s.config.color))

        if not entries:
            return

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale, line_h = 0.4, 20
        max_w = max(cv2.getTextSize(e[0], font, scale, 1)[0][0] for e in entries)
        box_w = max_w + 35
        box_h = len(entries) * line_h + 10

        # Semi-transparent overlay
        overlay = self._canvas[y:y+box_h, x:x+box_w].copy()
        bg_rect = np.full_like(overlay, t.legend_bg, dtype=np.uint8)
        blended = cv2.addWeighted(bg_rect, t.legend_alpha, overlay, 1.0 - t.legend_alpha, 0)
        self._canvas[y:y+box_h, x:x+box_w] = blended

        cv2.rectangle(self._canvas, (x, y), (x + box_w, y + box_h),
                      t.border, 1, self._line_type)

        for i, (label, color) in enumerate(entries):
            cy = y + 15 + i * line_h
            cv2.line(self._canvas, (x + 8, cy - 3), (x + 22, cy - 3),
                     color, 2, self._line_type)
            cv2.putText(self._canvas, label, (x + 28, cy),
                        font, scale, t.axis_label, 1, self._line_type)

    # ──────────────────────────────────────────────────────
    # Current values
    # ──────────────────────────────────────────────────────
    def _draw_current_values(self, series_map: dict, order: list,
                             right_x: int, top_y: int) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_offset = 0

        for name in order:
            if name not in series_map:
                continue
            series = series_map[name]
            if not series.config.show_value:
                continue

            val = series.latest
            text = "---" if np.isnan(val) else _format_number(val)
            label = series.config.label or name
            display = f"{label}: {text}"

            ts = cv2.getTextSize(display, font, 0.45, 1)[0]
            tx = right_x - ts[0] - 10
            ty = top_y - 8 - y_offset

            if ty > 10:
                cv2.putText(self._canvas, display, (tx, ty),
                            font, 0.45, series.config.color, 1, self._line_type)
                y_offset += 18

    # ──────────────────────────────────────────────────────
    # Mouse tooltip
    # ──────────────────────────────────────────────────────
    def _draw_tooltip(self, series_map: dict, order: list,
                      mouse_pos: tuple[int, int],
                      px: int, py: int, pw: int, ph: int) -> None:
        """Draw vertical crosshair line and value at mouse X position."""
        mx, my = mouse_pos
        cfg = self._config
        t = self._theme

        # Only if mouse is inside plot area
        if not (px <= mx <= px + pw and py <= my <= py + ph):
            return

        # Vertical crosshair
        cv2.line(self._canvas, (mx, py), (mx, py + ph),
                 t.grid_center, 1, self._line_type)

        # For each series, find the value at this X position
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_off = 0

        for name in order:
            if name not in series_map:
                continue
            series = series_map[name]
            if series.count < 2:
                continue

            data = series.get_data()
            n = len(data)

            # Map mouse X to data index
            frac = (mx - px) / pw
            idx = int(frac * (n - 1))
            idx = max(0, min(idx, n - 1))

            val = data[idx]
            if np.isnan(val):
                continue

            # Map value to Y pixel
            y_range = self._display_y_max - self._display_y_min
            if y_range == 0:
                y_range = 1.0
            y_norm = np.clip((val - self._display_y_min) / y_range, 0, 1)
            y_pixel = int(py + (1.0 - y_norm) * ph) if cfg.invert_y else int(py + y_norm * ph)

            # Draw dot at intersection
            cv2.circle(self._canvas, (mx, y_pixel), 4,
                       series.config.color, -1, self._line_type)

            # Tooltip text
            text = f"{series.config.label or name}: {_format_number(val)}"
            tx = mx + 10
            ty = py + 20 + y_off
            if tx + 150 > px + pw:
                tx = mx - 150

            cv2.putText(self._canvas, text, (tx, ty),
                        font, 0.38, series.config.color, 1, self._line_type)
            y_off += 16

    # ──────────────────────────────────────────────────────
    # Status bar
    # ──────────────────────────────────────────────────────
    def _draw_status_bar(self, fps: float, paused: bool,
                         status_text: str) -> None:
        cfg = self._config
        t = self._theme
        font = cv2.FONT_HERSHEY_SIMPLEX
        y = cfg.height - 12

        parts = []
        if cfg.show_fps:
            parts.append(f"{fps:.0f} FPS")
        if paused:
            parts.append("|| PAUSED")
        if status_text:
            parts.append(status_text)

        # Left side: hints
        if cfg.show_shortcuts_hint:
            hint = "[S]ave [P]ause [R]eset [Q]uit"
            cv2.putText(self._canvas, hint, (8, y),
                        font, 0.33, t.fps_text, 1, self._line_type)

        # Right side: FPS + status
        right_text = " | ".join(parts)
        ts = cv2.getTextSize(right_text, font, 0.38, 1)[0]
        cv2.putText(self._canvas, right_text, (cfg.width - ts[0] - 10, y),
                    font, 0.38, t.fps_text, 1, self._line_type)

    # ──────────────────────────────────────────────────────
    # Auto-scale helpers
    # ──────────────────────────────────────────────────────
    def _compute_auto_scale(self, series_map: dict) -> None:
        all_min, all_max = float('inf'), float('-inf')

        for series in series_map.values():
            lo, hi = series.get_min_max()
            if not np.isnan(lo):
                all_min = min(all_min, lo)
                all_max = max(all_max, hi)

        if all_min == float('inf'):
            return

        pad = self._config.auto_scale_padding
        data_range = all_max - all_min
        if data_range < 1e-6:
            data_range = 1.0

        new_min = all_min - data_range * pad
        new_max = all_max + data_range * pad

        if self._config.auto_scale == AutoScaleMode.AUTO_EXPAND:
            new_min = min(new_min, self._target_y_min)
            new_max = max(new_max, self._target_y_max)

        self._target_y_min = new_min
        self._target_y_max = new_max

        if not self._config.smooth_auto_scale:
            if new_min != self._display_y_min or new_max != self._display_y_max:
                self._display_y_min = new_min
                self._display_y_max = new_max
                self._bg_dirty = True

    def _lerp_y_axis(self) -> None:
        """Smooth transition for auto-scale using linear interpolation."""
        a = self._config.auto_scale_speed
        old_min, old_max = self._display_y_min, self._display_y_max

        self._display_y_min += (self._target_y_min - self._display_y_min) * a
        self._display_y_max += (self._target_y_max - self._display_y_max) * a

        # Only rebuild bg if change is visible (>0.1 pixel difference)
        cfg = self._config
        threshold = (self._display_y_max - self._display_y_min) / max(cfg.plot_h, 1) * 0.1
        if (abs(self._display_y_min - old_min) > threshold or
                abs(self._display_y_max - old_max) > threshold):
            self._bg_dirty = True


# ──────────────────────────────────────────────────────
# Utility
# ──────────────────────────────────────────────────────
def _format_number(val: float) -> str:
    """Smart number formatting for labels."""
    av = abs(val)
    if av >= 1000:
        return f"{val:.0f}"
    elif av >= 10:
        return f"{val:.1f}"
    elif av >= 1:
        return f"{val:.2f}"
    else:
        return f"{val:.3f}"