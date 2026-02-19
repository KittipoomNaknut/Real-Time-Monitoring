"""
LivePlot v2.0 — High-Performance Real-Time OpenCV Plotter
==========================================================
A production-grade real-time plotting library using OpenCV.

Features:
  - Multiple data series with independent colors and labels
  - Cached background rendering for high FPS
  - Auto-scaling Y-axis with optional fixed limits
  - Anti-aliased smooth line rendering
  - Modern dark theme with customizable color palette
  - Current value indicator and floating tooltip
  - FPS counter and performance monitoring
  - Thread-safe update mechanism
  - Robust input validation (handles NaN, inf, None)
  - Configurable buffer size, grid density, and margins

Author: Upgraded from original LivePlot
Version: 2.0.0
"""

import math
import sys
import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

import cv2
import numpy as np


# ============================================================
# Color Palette — Modern Dark Theme
# ============================================================
class Colors:
    """Centralized color definitions (BGR format for OpenCV)."""

    # Background & Grid
    BG_DARK = (18, 18, 24)           # Near-black background
    GRID_MAJOR = (45, 45, 55)        # Major grid lines
    GRID_MINOR = (32, 32, 40)        # Minor grid lines
    GRID_CENTER = (60, 60, 75)       # Center/zero line
    AXIS_LABEL = (140, 140, 160)     # Axis text
    TITLE_COLOR = (200, 200, 220)    # Title text
    VALUE_COLOR = (180, 180, 200)    # Current value text
    FPS_COLOR = (80, 80, 100)        # FPS counter
    BORDER = (50, 50, 65)            # Plot area border

    # Data Series — vibrant, high-contrast palette
    SERIES = [
        (255, 100, 255),   # Magenta
        (100, 255, 100),   # Green
        (100, 200, 255),   # Cyan-blue
        (80, 180, 255),    # Orange (BGR)
        (100, 100, 255),   # Red
        (255, 255, 100),   # Light cyan
        (150, 100, 255),   # Coral
        (255, 200, 50),    # Sky blue
    ]


# ============================================================
# Data Structures
# ============================================================
class AutoScaleMode(Enum):
    """Y-axis scaling mode."""
    FIXED = "fixed"          # Use user-defined limits
    AUTO = "auto"            # Scale to fit all visible data
    AUTO_EXPAND = "expand"   # Only expand, never shrink


@dataclass
class SeriesConfig:
    """Configuration for a single data series."""
    label: str = ""
    color: tuple = (255, 100, 255)
    line_width: int = 2
    show_dot: bool = True         # Show dot at latest point
    dot_radius: int = 5
    show_value: bool = True       # Show current value text
    show_glow: bool = True        # Glow effect on dot


@dataclass
class PlotConfig:
    """Master configuration for the plot."""
    # Dimensions
    width: int = 800
    height: int = 480

    # Margins (left, top, right, bottom) — space for labels
    margin_left: int = 70
    margin_top: int = 50
    margin_right: int = 20
    margin_bottom: int = 40

    # Y-axis
    y_min: float = 0.0
    y_max: float = 100.0
    auto_scale: AutoScaleMode = AutoScaleMode.FIXED
    auto_scale_padding: float = 0.1   # 10% padding above/below data

    # Data
    buffer_size: int = 200          # Number of points to keep
    min_update_interval: float = 0  # Minimum seconds between updates (0 = no limit)

    # Grid
    grid_x_spacing: int = 50        # Pixels between vertical grid lines
    grid_y_divisions: int = 8       # Number of horizontal divisions

    # Visual
    title: str = ""
    show_fps: bool = True
    show_legend: bool = True
    show_zero_line: bool = True     # Highlight y=0 line
    antialiased: bool = True

    # Invert
    invert_y: bool = True           # True = higher values at top (natural)

    @property
    def plot_x(self) -> int:
        return self.margin_left

    @property
    def plot_y(self) -> int:
        return self.margin_top

    @property
    def plot_w(self) -> int:
        return self.width - self.margin_left - self.margin_right

    @property
    def plot_h(self) -> int:
        return self.height - self.margin_top - self.margin_bottom


# ============================================================
# Series — manages data buffer for one data stream
# ============================================================
class Series:
    """A single data series with a circular buffer."""

    __slots__ = ('config', '_buffer', '_size', '_head', '_count')

    def __init__(self, config: SeriesConfig, buffer_size: int):
        self.config = config
        self._size = buffer_size
        self._buffer = np.full(buffer_size, np.nan, dtype=np.float64)
        self._head = 0    # Next write position
        self._count = 0   # Total points written

    def push(self, value: float) -> None:
        """Add a new value to the circular buffer."""
        # Sanitize input
        if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
            value = np.nan
        self._buffer[self._head] = float(value)
        self._head = (self._head + 1) % self._size
        self._count = min(self._count + 1, self._size)

    def get_data(self) -> np.ndarray:
        """Return data in chronological order (oldest → newest)."""
        if self._count < self._size:
            return self._buffer[:self._count].copy()
        # Buffer is full — unwrap from head
        return np.roll(self._buffer, -self._head).copy()

    @property
    def latest(self) -> float:
        if self._count == 0:
            return np.nan
        idx = (self._head - 1) % self._size
        return self._buffer[idx]

    @property
    def count(self) -> int:
        return self._count

    def clear(self) -> None:
        self._buffer[:] = np.nan
        self._head = 0
        self._count = 0


# ============================================================
# LivePlot v2.0
# ============================================================
class LivePlot:
    """
    High-performance real-time plotter using OpenCV.

    Usage:
        # Single series (simple API)
        plot = LivePlot(PlotConfig(title="Sensor", y_min=-100, y_max=100))
        plot.add_series("temperature", SeriesConfig(label="Temp °C", color=(100, 200, 255)))

        while True:
            value = read_sensor()
            img = plot.update("temperature", value)
            cv2.imshow("Plot", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Multi-series
        plot.add_series("humidity", SeriesConfig(label="Humidity %", color=(100, 255, 100)))
        img = plot.update_all({"temperature": 25.3, "humidity": 60.1})
    """

    def __init__(self, config: Optional[PlotConfig] = None):
        self._config = config or PlotConfig()
        self._series: dict[str, Series] = {}
        self._series_order: list[str] = []  # Maintain insertion order

        # Rendering buffers
        self._bg_cache: Optional[np.ndarray] = None
        self._bg_dirty = True
        self._canvas = np.zeros(
            (self._config.height, self._config.width, 3), dtype=np.uint8
        )

        # Y-axis state (for auto-scale)
        self._current_y_min = self._config.y_min
        self._current_y_max = self._config.y_max

        # Timing
        self._last_update = 0.0
        self._frame_times: list[float] = []
        self._fps = 0.0

        # Thread safety
        self._lock = threading.Lock()

        # Line type
        self._line_type = cv2.LINE_AA if self._config.antialiased else cv2.LINE_8

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------
    def add_series(self, name: str, config: Optional[SeriesConfig] = None) -> 'LivePlot':
        """Add a data series. Returns self for chaining."""
        if config is None:
            idx = len(self._series) % len(Colors.SERIES)
            config = SeriesConfig(label=name, color=Colors.SERIES[idx])
        with self._lock:
            self._series[name] = Series(config, self._config.buffer_size)
            self._series_order.append(name)
            self._bg_dirty = True
        return self

    def update(self, name_or_value, value=None, color=None) -> np.ndarray:
        """
        Update a series and render.

        Flexible call signatures:
            plot.update("series_name", 42.0)   # Named series
            plot.update(42.0)                   # Default series (auto-created)
        """
        with self._lock:
            if value is None:
                # Single-value mode: use default series
                actual_value = name_or_value
                series_name = "_default"
                if series_name not in self._series:
                    idx = len(self._series) % len(Colors.SERIES)
                    cfg = SeriesConfig(label="Value", color=Colors.SERIES[idx] if color is None else color)
                    self._series[series_name] = Series(cfg, self._config.buffer_size)
                    self._series_order.append(series_name)
                    self._bg_dirty = True
                if color is not None:
                    self._series[series_name].config.color = color
            else:
                actual_value = value
                series_name = name_or_value

            if series_name not in self._series:
                raise KeyError(f"Series '{series_name}' not found. Add it with add_series() first.")

            # Rate limiting
            now = time.perf_counter()
            if self._config.min_update_interval > 0:
                if (now - self._last_update) < self._config.min_update_interval:
                    return self._canvas

            self._series[series_name].push(actual_value)
            self._last_update = now

            return self._render(now)

    def update_all(self, data: dict) -> np.ndarray:
        """Update multiple series at once and render."""
        with self._lock:
            now = time.perf_counter()
            for name, value in data.items():
                if name not in self._series:
                    raise KeyError(f"Series '{name}' not found.")
                self._series[name].push(value)
            self._last_update = now
            return self._render(now)

    def clear(self, name: Optional[str] = None) -> None:
        """Clear data from one or all series."""
        with self._lock:
            if name:
                self._series[name].clear()
            else:
                for s in self._series.values():
                    s.clear()

    def set_y_limits(self, y_min: float, y_max: float) -> None:
        """Update Y-axis limits at runtime."""
        with self._lock:
            self._config.y_min = y_min
            self._config.y_max = y_max
            self._current_y_min = y_min
            self._current_y_max = y_max
            self._bg_dirty = True

    @property
    def fps(self) -> float:
        return self._fps

    # ----------------------------------------------------------
    # Backward-compatible API (drop-in replacement)
    # ----------------------------------------------------------
    @classmethod
    def from_legacy(cls, w=640, h=480, yLimit=None,
                    interval=0.001, invert=True, char='Y') -> 'LivePlot':
        """
        Create a LivePlot with the same signature as the original.
        For backward compatibility.
        """
        if yLimit is None:
            yLimit = [0, 100]
        config = PlotConfig(
            width=w, height=h,
            y_min=yLimit[0], y_max=yLimit[1],
            min_update_interval=interval,
            invert_y=invert,
            title=char,
        )
        plot = cls(config)
        return plot

    # ----------------------------------------------------------
    # Internal Rendering
    # ----------------------------------------------------------
    def _render(self, now: float) -> np.ndarray:
        """Main render pipeline. Must be called under lock."""

        # 1. Auto-scale Y if needed
        if self._config.auto_scale != AutoScaleMode.FIXED:
            self._compute_auto_scale()

        # 2. Rebuild background cache if dirty
        if self._bg_dirty or self._bg_cache is None:
            self._rebuild_background()
            self._bg_dirty = False

        # 3. Blit cached background
        np.copyto(self._canvas, self._bg_cache)

        cfg = self._config
        px, py = cfg.plot_x, cfg.plot_y
        pw, ph = cfg.plot_w, cfg.plot_h

        # 4. Draw each series
        for name in self._series_order:
            series = self._series[name]
            if series.count < 2:
                continue
            self._draw_series(series, px, py, pw, ph)

        # 5. Draw legend
        if cfg.show_legend and len(self._series) > 1:
            self._draw_legend(px + 10, py + 10)

        # 6. Draw current values panel (right side)
        self._draw_current_values(px + pw, py)

        # 7. FPS counter
        if cfg.show_fps:
            self._update_fps(now)
            fps_text = f"{self._fps:.0f} FPS"
            cv2.putText(self._canvas, fps_text,
                        (cfg.width - 90, cfg.height - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                        Colors.FPS_COLOR, 1, self._line_type)

        return self._canvas

    def _rebuild_background(self) -> None:
        """Render static background elements to cache."""
        cfg = self._config
        bg = np.zeros((cfg.height, cfg.width, 3), dtype=np.uint8)

        # Fill background
        bg[:] = Colors.BG_DARK

        px, py = cfg.plot_x, cfg.plot_y
        pw, ph = cfg.plot_w, cfg.plot_h

        # --- Minor grid (vertical) ---
        for x in range(0, pw, cfg.grid_x_spacing):
            x_abs = px + x
            cv2.line(bg, (x_abs, py), (x_abs, py + ph),
                     Colors.GRID_MINOR, 1, self._line_type)

        # --- Horizontal grid + Y labels ---
        n_div = cfg.grid_y_divisions
        y_min, y_max = self._current_y_min, self._current_y_max
        y_range = y_max - y_min if y_max != y_min else 1.0

        for i in range(n_div + 1):
            frac = i / n_div
            y_abs = py + int(frac * ph)

            # Grid line
            line_color = Colors.GRID_MAJOR
            cv2.line(bg, (px, y_abs), (px + pw, y_abs),
                     line_color, 1, self._line_type)

            # Y label
            if cfg.invert_y:
                y_val = y_max - frac * y_range
            else:
                y_val = y_min + frac * y_range

            label = self._format_number(y_val)
            cv2.putText(bg, label,
                        (5, y_abs + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                        Colors.AXIS_LABEL, 1, self._line_type)

        # --- Zero line (if visible) ---
        if cfg.show_zero_line and y_min < 0 < y_max:
            zero_frac = (y_max - 0) / y_range if cfg.invert_y else (0 - y_min) / y_range
            zero_y = py + int(zero_frac * ph)
            cv2.line(bg, (px, zero_y), (px + pw, zero_y),
                     Colors.GRID_CENTER, 1, self._line_type)

        # --- Plot area border ---
        cv2.rectangle(bg, (px, py), (px + pw, py + ph),
                      Colors.BORDER, 1, self._line_type)

        # --- Title ---
        if cfg.title:
            title_size = cv2.getTextSize(cfg.title, cv2.FONT_HERSHEY_SIMPLEX,
                                         0.7, 1)[0]
            title_x = px + (pw - title_size[0]) // 2
            cv2.putText(bg, cfg.title, (title_x, py - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        Colors.TITLE_COLOR, 1, self._line_type)

        self._bg_cache = bg

    def _draw_series(self, series: Series, px: int, py: int,
                     pw: int, ph: int) -> None:
        """Draw one data series onto the canvas."""
        data = series.get_data()
        n = len(data)
        if n < 2:
            return

        cfg = self._config
        color = series.config.color
        y_min, y_max = self._current_y_min, self._current_y_max
        y_range = y_max - y_min if y_max != y_min else 1.0

        # Compute pixel coordinates for all points
        x_coords = np.linspace(px, px + pw, n, dtype=np.float64)

        # Normalize y values to [0, 1]
        y_norm = (data - y_min) / y_range
        np.clip(y_norm, 0.0, 1.0, out=y_norm)

        if cfg.invert_y:
            y_coords = py + (1.0 - y_norm) * ph
        else:
            y_coords = py + y_norm * ph

        # Build points array for polylines (skip NaN)
        valid = ~np.isnan(data)
        # Fill NaN positions with 0 to avoid cast warning (they'll be skipped)
        y_draw = np.where(valid, y_coords, 0)
        points = np.column_stack((x_coords, y_draw)).astype(np.int32)

        # Draw segments (handle NaN gaps)
        segments = []
        current_segment = []
        for i in range(n):
            if valid[i]:
                current_segment.append(points[i])
            else:
                if len(current_segment) >= 2:
                    segments.append(np.array(current_segment))
                current_segment = []
        if len(current_segment) >= 2:
            segments.append(np.array(current_segment))

        for seg in segments:
            cv2.polylines(self._canvas, [seg], isClosed=False,
                          color=color, thickness=series.config.line_width,
                          lineType=self._line_type)

        # Draw dot at latest valid point
        if series.config.show_dot and valid[-1]:
            latest_pt = (int(x_coords[-1]), int(y_coords[-1]))

            # Glow effect
            if series.config.show_glow:
                glow_color = tuple(max(0, min(255, c // 3)) for c in color)
                cv2.circle(self._canvas, latest_pt,
                           series.config.dot_radius + 6,
                           glow_color, -1, self._line_type)

            # Dot
            cv2.circle(self._canvas, latest_pt,
                       series.config.dot_radius,
                       color, -1, self._line_type)

            # White center
            cv2.circle(self._canvas, latest_pt, 2,
                       (255, 255, 255), -1, self._line_type)

    def _draw_legend(self, x: int, y: int) -> None:
        """Draw a compact legend box."""
        entries = []
        for name in self._series_order:
            s = self._series[name]
            label = s.config.label or name
            entries.append((label, s.config.color))

        if not entries:
            return

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.4
        line_h = 20
        max_w = max(cv2.getTextSize(e[0], font, scale, 1)[0][0] for e in entries)
        box_w = max_w + 35
        box_h = len(entries) * line_h + 10

        # Semi-transparent background
        overlay = self._canvas.copy()
        cv2.rectangle(overlay, (x, y), (x + box_w, y + box_h),
                      (30, 30, 40), -1)
        cv2.addWeighted(overlay, 0.7, self._canvas, 0.3, 0, self._canvas)
        cv2.rectangle(self._canvas, (x, y), (x + box_w, y + box_h),
                      Colors.BORDER, 1, self._line_type)

        for i, (label, color) in enumerate(entries):
            cy = y + 15 + i * line_h
            # Color swatch
            cv2.line(self._canvas, (x + 8, cy - 3), (x + 22, cy - 3),
                     color, 2, self._line_type)
            # Label
            cv2.putText(self._canvas, label, (x + 28, cy),
                        font, scale, Colors.AXIS_LABEL, 1, self._line_type)

    def _draw_current_values(self, right_x: int, top_y: int) -> None:
        """Draw current values for each series."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_offset = 0

        for name in self._series_order:
            series = self._series[name]
            if not series.config.show_value:
                continue

            val = series.latest
            if np.isnan(val):
                text = "---"
            else:
                text = self._format_number(val)

            label = series.config.label or name
            display = f"{label}: {text}"

            text_size = cv2.getTextSize(display, font, 0.45, 1)[0]
            tx = right_x - text_size[0] - 10
            ty = top_y - 8 - y_offset

            # Only show if there's room above the plot
            if ty > 10:
                cv2.putText(self._canvas, display, (tx, ty),
                            font, 0.45, series.config.color, 1, self._line_type)
                y_offset += 18

    def _compute_auto_scale(self) -> None:
        """Compute Y limits from all visible data."""
        all_min = float('inf')
        all_max = float('-inf')

        for series in self._series.values():
            data = series.get_data()
            valid = data[~np.isnan(data)]
            if len(valid) > 0:
                all_min = min(all_min, valid.min())
                all_max = max(all_max, valid.max())

        if all_min == float('inf'):
            return  # No data yet

        # Add padding
        pad = self._config.auto_scale_padding
        data_range = all_max - all_min
        if data_range < 1e-6:
            data_range = 1.0

        new_min = all_min - data_range * pad
        new_max = all_max + data_range * pad

        if self._config.auto_scale == AutoScaleMode.AUTO_EXPAND:
            new_min = min(new_min, self._current_y_min)
            new_max = max(new_max, self._current_y_max)

        if new_min != self._current_y_min or new_max != self._current_y_max:
            self._current_y_min = new_min
            self._current_y_max = new_max
            self._bg_dirty = True  # Need to redraw grid labels

    def _update_fps(self, now: float) -> None:
        """Track FPS using a sliding window."""
        self._frame_times.append(now)
        # Keep last 30 frames
        cutoff = now - 1.0
        self._frame_times = [t for t in self._frame_times if t > cutoff]
        if len(self._frame_times) >= 2:
            elapsed = self._frame_times[-1] - self._frame_times[0]
            self._fps = (len(self._frame_times) - 1) / elapsed if elapsed > 0 else 0
        else:
            self._fps = 0

    @staticmethod
    def _format_number(val: float) -> str:
        """Smart number formatting."""
        if abs(val) >= 1000:
            return f"{val:.0f}"
        elif abs(val) >= 10:
            return f"{val:.1f}"
        elif abs(val) >= 1:
            return f"{val:.2f}"
        else:
            return f"{val:.3f}"


# ============================================================
# Demo — Showcase all features
# ============================================================
def demo_single_series():
    """Simple single-series demo (backward-compatible style)."""
    plot = LivePlot(PlotConfig(
        width=1200, height=500,
        title="Single Series — Sine Wave",
        y_min=-100, y_max=100,
        show_fps=True,
    ))

    x = 0
    while True:
        x += 1
        if x >= 360:
            x = 0
        y = int(math.sin(math.radians(x)) * 100)
        img = plot.update(y, color=(255, 100, 255))

        cv2.imshow("LivePlot v2.0 — Single", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()


def demo_multi_series():
    """Multi-series demo with different waveforms."""
    plot = LivePlot(PlotConfig(
        width=1200, height=600,
        title="Multi-Series — Signal Monitor",
        y_min=-120, y_max=120,
        buffer_size=300,
        show_fps=True,
        show_legend=True,
    ))

    plot.add_series("sin", SeriesConfig(
        label="sin(x)", color=(255, 100, 255), line_width=2))
    plot.add_series("cos", SeriesConfig(
        label="cos(x)", color=(100, 255, 150), line_width=2))
    plot.add_series("saw", SeriesConfig(
        label="sawtooth", color=(100, 180, 255), line_width=1))

    x = 0
    while True:
        x += 1
        sin_val = math.sin(math.radians(x)) * 100
        cos_val = math.cos(math.radians(x)) * 80
        saw_val = ((x % 180) / 180.0) * 200 - 100  # Sawtooth

        img = plot.update_all({
            "sin": sin_val,
            "cos": cos_val,
            "saw": saw_val,
        })

        cv2.imshow("LivePlot v2.0 — Multi", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()


def demo_auto_scale():
    """Auto-scaling Y-axis demo with growing amplitude."""
    plot = LivePlot(PlotConfig(
        width=1000, height=500,
        title="Auto-Scale Demo",
        auto_scale=AutoScaleMode.AUTO,
        buffer_size=200,
        show_fps=True,
    ))

    plot.add_series("signal", SeriesConfig(
        label="Growing Signal", color=(100, 200, 255)))

    x = 0
    while True:
        x += 1
        # Amplitude grows over time
        amplitude = 10 + (x / 5)
        noise = np.random.normal(0, amplitude * 0.1)
        y = math.sin(math.radians(x * 3)) * amplitude + noise

        img = plot.update("signal", y)

        cv2.imshow("LivePlot v2.0 — Auto Scale", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import sys

    demos = {
        "single": demo_single_series,
        "multi": demo_multi_series,
        "auto": demo_auto_scale,
    }

    if len(sys.argv) > 1 and sys.argv[1] in demos:
        demos[sys.argv[1]]()
    else:
        print("LivePlot v2.0 — Available demos:")
        print("  python live_plot.py single   → Single series sine wave")
        print("  python live_plot.py multi    → Multi-series signal monitor")
        print("  python live_plot.py auto     → Auto-scaling amplitude")
        print()
        print("Running default: multi-series demo...")
        demo_multi_series()