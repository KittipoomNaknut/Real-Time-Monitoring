"""
LivePlot v3.0 — Cross-Platform High-Performance Real-Time OpenCV Plotter
=========================================================================

Quick Start:
    from live_plot import LivePlot, PlotConfig, SeriesConfig

    plot = LivePlot(PlotConfig(title="My Plot", y_min=-100, y_max=100))
    plot.add_series("data", SeriesConfig(label="Sensor"))

    while True:
        value = get_data()
        if plot.step("data", value):    # render + display + handle input
            break                        # user pressed Q

Keyboard Shortcuts:
    Q/ESC  → Quit          P/Space → Pause/Resume
    S      → Screenshot    V       → Start/Stop Recording
    R      → Reset Data    T       → Cycle Theme
    +/-    → Adjust FPS
"""

__version__ = "3.0.0"

# Core class
from .core import LivePlot

# Configuration
from .config import PlotConfig, SeriesConfig, AutoScaleMode

# Colors & themes
from .colors import (
    Theme, DARK_THEME, LIGHT_THEME, MIDNIGHT_THEME,
    get_theme, register_theme,
)

# Frame timing
from .frame_timer import FrameTimer, TimingStrategy

# Platform utilities
from .platform_utils import (
    PlatformInfo, apply_platform_fixes, cleanup_platform,
)

# Interactions
from .interactions import (
    MouseTracker, VideoRecorder,
    save_screenshot, process_key,
)

__all__ = [
    # Core
    "LivePlot",
    # Config
    "PlotConfig", "SeriesConfig", "AutoScaleMode",
    # Colors
    "Theme", "DARK_THEME", "LIGHT_THEME", "MIDNIGHT_THEME",
    "get_theme", "register_theme",
    # Frame timing
    "FrameTimer", "TimingStrategy",
    # Platform
    "PlatformInfo", "apply_platform_fixes", "cleanup_platform",
    # Interactions
    "MouseTracker", "VideoRecorder",
    "save_screenshot", "process_key",
]
