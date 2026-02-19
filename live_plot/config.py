"""
Configuration — Dataclasses for plot and series settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AutoScaleMode(Enum):
    """Y-axis scaling behavior."""
    FIXED = "fixed"          # Use user-defined y_min/y_max
    AUTO = "auto"            # Fit to visible data each frame
    AUTO_EXPAND = "expand"   # Only expand range, never shrink


@dataclass
class SeriesConfig:
    """Visual configuration for a single data series."""
    label: str = ""
    color: tuple[int, int, int] = (255, 100, 255)
    line_width: int = 2
    show_dot: bool = True
    dot_radius: int = 5
    show_value: bool = True
    show_glow: bool = True


@dataclass
class PlotConfig:
    """
    Master configuration for the plot window.

    Layout diagram:
    ┌────────────────────────── width ──────────────────────────┐
    │                      margin_top                           │
    │   ┌── title ──┐                    ┌─ current values ─┐  │
    │ m ├───────────┴────────────────────┴──────────────────┤ m │
    │ a │                                                    │ a │
    │ r │              PLOT AREA                             │ r │
    │ g │           (plot_w × plot_h)                        │ g │
    │ _ │                                                    │ _ │
    │ l │  Y labels    data lines    legend                  │ r │
    │   ├────────────────────────────────────────────────────┤   │
    │   │                    margin_bottom        FPS / keys │   │
    └───┴────────────────────────────────────────────────────┴───┘
    """

    # ── Dimensions ──
    width: int = 800
    height: int = 480

    # ── Margins ──
    margin_left: int = 70
    margin_top: int = 50
    margin_right: int = 20
    margin_bottom: int = 40

    # ── Y-axis ──
    y_min: float = 0.0
    y_max: float = 100.0
    auto_scale: AutoScaleMode = AutoScaleMode.FIXED
    auto_scale_padding: float = 0.1
    smooth_auto_scale: bool = True    # animate y-axis transitions
    auto_scale_speed: float = 0.15    # lerp factor (0=frozen, 1=instant)

    # ── Data ──
    buffer_size: int = 200
    min_update_interval: float = 0

    # ── Grid ──
    grid_x_spacing: int = 50
    grid_y_divisions: int = 8

    # ── Visual ──
    title: str = ""
    theme: str = "dark"              # "dark", "light", "midnight", or custom
    show_fps: bool = True
    show_legend: bool = True
    show_zero_line: bool = True
    show_shortcuts_hint: bool = True  # show keyboard shortcut hints
    antialiased: bool = True
    invert_y: bool = True

    # ── Interaction ──
    enable_mouse_tooltip: bool = True
    enable_keyboard: bool = True
    screenshot_dir: str = "."         # directory for screenshots

    # ── Frame rate ──
    target_fps: int = 60              # 0 = unlimited

    # ── Computed properties ──
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
