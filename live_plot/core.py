"""
LivePlot Core — Main class that orchestrates all modules.

This is the primary public interface. It coordinates:
  - Series management (data storage)
  - Renderer (background cache + drawing)
  - FrameTimer (cross-platform frame pacing)
  - Interactions (mouse, keyboard, recording)
  - Platform fixes (timer boost, HiDPI)
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import cv2
import numpy as np

from .config import PlotConfig, SeriesConfig, AutoScaleMode
from .colors import Theme, get_theme, THEMES
from .series import Series
from .renderer import Renderer
from .frame_timer import FrameTimer, TimingStrategy
from .interactions import (
    MouseTracker, VideoRecorder, KeyAction,
    process_key, save_screenshot,
)
from .platform_utils import (
    PlatformInfo, apply_platform_fixes, cleanup_platform,
)


class LivePlot:
    """
    High-performance cross-platform real-time plotter.

    Quick Start:
        from live_plot import LivePlot, PlotConfig, SeriesConfig

        plot = LivePlot(PlotConfig(title="Sensor", y_min=-100, y_max=100))
        plot.add_series("temp", SeriesConfig(label="Temperature"))

        while True:
            value = read_sensor()
            if plot.step("temp", value):  # step = update + display + handle input
                break                     # user pressed Q

    Manual Control:
        plot = LivePlot(config)
        plot.add_series("data")

        while True:
            img = plot.update("data", value)    # update data + render
            cv2.imshow("Plot", img)             # display yourself
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    """

    def __init__(self, config: Optional[PlotConfig] = None, *,
                 window_name: str = "LivePlot"):
        self._config = config or PlotConfig()
        self._window_name = window_name

        # Apply platform fixes once
        self._platform_info = apply_platform_fixes()

        # Series storage
        self._series: dict[str, Series] = {}
        self._series_order: list[str] = []

        # Sub-systems
        self._renderer = Renderer(self._config)
        self._timer = FrameTimer(
            target_fps=self._config.target_fps,
            strategy=TimingStrategy.ADAPTIVE,
        )
        self._mouse = MouseTracker()
        self._recorder = VideoRecorder(
            self._config.width, self._config.height,
            fps=min(30.0, float(self._config.target_fps or 30)),
            directory=self._config.screenshot_dir,
        )

        # State
        self._paused = False
        self._status_text = ""
        self._status_clear_time = 0.0
        self._window_created = False
        self._mouse_attached = False
        self._theme_cycle = list(THEMES.keys())
        self._theme_index = self._theme_cycle.index(self._config.theme) \
            if self._config.theme in self._theme_cycle else 0

        # Thread safety
        self._lock = threading.Lock()

    # ──────────────────────────────────────────────────────
    # Series Management
    # ──────────────────────────────────────────────────────
    def add_series(self, name: str,
                   config: Optional[SeriesConfig] = None) -> 'LivePlot':
        """Add a data series. Returns self for chaining."""
        if config is None:
            colors = self._renderer.theme.series_colors
            idx = len(self._series) % len(colors)
            config = SeriesConfig(label=name, color=colors[idx])
        with self._lock:
            self._series[name] = Series(config, self._config.buffer_size)
            self._series_order.append(name)
            self._renderer.mark_dirty()
        return self

    def remove_series(self, name: str) -> 'LivePlot':
        """Remove a data series."""
        with self._lock:
            if name in self._series:
                del self._series[name]
                self._series_order.remove(name)
                self._renderer.mark_dirty()
        return self

    # ──────────────────────────────────────────────────────
    # Data Update (render only, no display)
    # ──────────────────────────────────────────────────────
    def update(self, name_or_value, value=None, color=None) -> np.ndarray:
        """
        Push data and render. Returns canvas (numpy array).

        Flexible signatures:
            plot.update(42.0)                   # single value, auto-series
            plot.update("temp", 42.0)           # named series
        """
        with self._lock:
            if value is None:
                actual_value = name_or_value
                series_name = self._ensure_default_series(color)
                if color is not None:
                    self._series[series_name].config.color = color
            else:
                actual_value = value
                series_name = name_or_value

            if series_name not in self._series:
                raise KeyError(f"Series '{series_name}' not found. Use add_series() first.")

            if not self._paused:
                self._series[series_name].push(actual_value)

            return self._do_render()

    def update_all(self, data: dict) -> np.ndarray:
        """Push data for multiple series and render once."""
        with self._lock:
            if not self._paused:
                for name, value in data.items():
                    if name not in self._series:
                        raise KeyError(f"Series '{name}' not found.")
                    self._series[name].push(value)

            return self._do_render()

    # ──────────────────────────────────────────────────────
    # Step = update + display + handle input (all-in-one)
    # ──────────────────────────────────────────────────────
    def step(self, name_or_value, value=None, color=None) -> bool:
        """
        All-in-one: update data → render → display → handle input.

        Returns True if user wants to quit (pressed Q/ESC).

        Usage:
            while True:
                if plot.step("sensor", read_value()):
                    break
        """
        img = self.update(name_or_value, value, color)
        return self._display_and_handle(img)

    def step_all(self, data: dict) -> bool:
        """All-in-one for multiple series. Returns True on quit."""
        img = self.update_all(data)
        return self._display_and_handle(img)

    # ──────────────────────────────────────────────────────
    # Display + Input handling
    # ──────────────────────────────────────────────────────
    def _display_and_handle(self, img: np.ndarray) -> bool:
        """Show image, handle frame timing and keyboard. Returns True on quit."""
        self._ensure_window()
        cv2.imshow(self._window_name, img)

        # Record if active
        if self._recorder.is_recording:
            self._recorder.write_frame(img)

        # Frame pacing + keyboard
        key = self._timer.tick()
        if key < 0:
            return False

        return self._handle_key(key)

    def _handle_key(self, key: int) -> bool:
        """Process keyboard input. Returns True on quit."""
        if not self._config.enable_keyboard:
            return key == ord('q') or key == 27

        action = process_key(key)

        if action.quit:
            self.close()
            return True

        if action.toggle_pause:
            self._paused = not self._paused

        if action.screenshot:
            path = save_screenshot(
                self._renderer.canvas,
                self._config.screenshot_dir
            )
            self._set_status(f"Saved: {path}", duration=2.0)

        if action.reset:
            self.clear()
            self._set_status("Data cleared", duration=1.5)

        if action.toggle_recording:
            if self._recorder.is_recording:
                path = self._recorder.stop()
                self._set_status(f"Recorded: {path}", duration=2.0)
            else:
                try:
                    path = self._recorder.start()
                    self._set_status(f"Recording...", duration=1.0)
                except RuntimeError as e:
                    self._set_status(f"Record failed: {e}", duration=3.0)

        if action.cycle_theme:
            self._theme_index = (self._theme_index + 1) % len(self._theme_cycle)
            theme_name = self._theme_cycle[self._theme_index]
            self._renderer.theme = get_theme(theme_name)
            self._set_status(f"Theme: {theme_name}", duration=1.5)

        if action.fps_delta != 0:
            new_fps = max(10, self._timer.target_fps + action.fps_delta)
            self._timer.target_fps = new_fps
            self._set_status(f"Target FPS: {new_fps}", duration=1.0)

        return False

    def _set_status(self, text: str, duration: float = 2.0) -> None:
        self._status_text = text
        self._status_clear_time = time.perf_counter() + duration

    # ──────────────────────────────────────────────────────
    # Utility methods
    # ──────────────────────────────────────────────────────
    def clear(self, name: Optional[str] = None) -> None:
        """Clear data from one or all series."""
        with self._lock:
            if name:
                if name in self._series:
                    self._series[name].clear()
            else:
                for s in self._series.values():
                    s.clear()

    def set_y_limits(self, y_min: float, y_max: float) -> None:
        """Update Y-axis limits at runtime."""
        with self._lock:
            self._renderer.set_y_limits(y_min, y_max)

    def set_theme(self, theme_name: str) -> None:
        """Switch theme by name."""
        self._renderer.theme = get_theme(theme_name)

    @property
    def fps(self) -> float:
        return self._timer.fps

    @property
    def paused(self) -> bool:
        return self._paused

    @paused.setter
    def paused(self, val: bool) -> None:
        self._paused = val

    @property
    def canvas(self) -> np.ndarray:
        """Current rendered image (H×W×3 uint8 BGR)."""
        return self._renderer.canvas

    def close(self) -> None:
        """Cleanup all resources."""
        if self._recorder.is_recording:
            self._recorder.stop()
        self._timer.stop()
        cleanup_platform()

    # ──────────────────────────────────────────────────────
    # Backward-compatible API
    # ──────────────────────────────────────────────────────
    @classmethod
    def from_legacy(cls, w=640, h=480, yLimit=None,
                    interval=0.001, invert=True, char='Y') -> 'LivePlot':
        """Drop-in replacement for v1 LivePlot constructor."""
        if yLimit is None:
            yLimit = [0, 100]
        config = PlotConfig(
            width=w, height=h,
            y_min=yLimit[0], y_max=yLimit[1],
            min_update_interval=interval,
            invert_y=invert,
            title=char,
        )
        return cls(config)

    # ──────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────
    def _ensure_default_series(self, color=None) -> str:
        name = "_default"
        if name not in self._series:
            colors = self._renderer.theme.series_colors
            idx = len(self._series) % len(colors)
            cfg = SeriesConfig(
                label="Value",
                color=color if color is not None else colors[idx]
            )
            self._series[name] = Series(cfg, self._config.buffer_size)
            self._series_order.append(name)
            self._renderer.mark_dirty()
        return name

    def _ensure_window(self) -> None:
        if not self._window_created:
            cv2.namedWindow(self._window_name, cv2.WINDOW_AUTOSIZE)
            # Qt backend (especially on Wayland/Linux) needs at least one
            # event loop iteration before the window handle becomes valid.
            # Without this, setMouseCallback crashes with "NULL window handler".
            cv2.waitKey(1)
            self._mouse_attached = False
            self._window_created = True

        if not self._mouse_attached and self._config.enable_mouse_tooltip:
            self._mouse_attached = self._mouse.attach(self._window_name)

    def _do_render(self) -> np.ndarray:
        """Internal render call. Must be called under lock."""
        # Clear expired status text
        if self._status_text and time.perf_counter() > self._status_clear_time:
            self._status_text = ""

        return self._renderer.render(
            series_map=self._series,
            series_order=self._series_order,
            fps=self._timer.fps,
            paused=self._paused,
            mouse_pos=self._mouse.position,
            status_text=self._status_text,
        )
