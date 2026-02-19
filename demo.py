"""
LivePlot v3.0 — Demo Scripts
==============================

Usage:
    python -m live_plot.demo                # default: multi-series
    python -m live_plot.demo single         # single sine wave
    python -m live_plot.demo multi          # 3 waveforms
    python -m live_plot.demo auto           # auto-scaling amplitude
    python -m live_plot.demo theme          # cycle through themes
    python -m live_plot.demo stress         # 8 series performance test

Keyboard shortcuts active in all demos:
    Q/ESC=quit  P/Space=pause  S=screenshot  V=record  T=theme  R=reset
"""

from __future__ import annotations

import math
import sys
import numpy as np

from .core import LivePlot
from .config import PlotConfig, SeriesConfig, AutoScaleMode
from .frame_timer import TimingStrategy


def demo_single():
    """Single sine wave — simplest usage."""
    plot = LivePlot(
        PlotConfig(
            width=1200, height=500,
            title="Single Series — Sine Wave",
            y_min=-100, y_max=100,
            target_fps=60,
        ),
        window_name="LivePlot v3 — Single",
    )

    x = 0
    while True:
        x = (x + 1) % 360
        y = math.sin(math.radians(x)) * 100

        if plot.step(y):
            break


def demo_multi():
    """Multiple waveforms with legend and tooltips."""
    plot = LivePlot(
        PlotConfig(
            width=1200, height=600,
            title="Multi-Series — Signal Monitor",
            y_min=-120, y_max=120,
            buffer_size=300,
            target_fps=60,
        ),
        window_name="LivePlot v3 — Multi",
    )

    plot.add_series("sin", SeriesConfig(label="sin(x)", color=(255, 100, 255)))
    plot.add_series("cos", SeriesConfig(label="cos(x)", color=(100, 255, 150)))
    plot.add_series("saw", SeriesConfig(label="sawtooth", color=(100, 180, 255), line_width=1))

    x = 0
    while True:
        x += 1
        data = {
            "sin": math.sin(math.radians(x)) * 100,
            "cos": math.cos(math.radians(x)) * 80,
            "saw": ((x % 180) / 180.0) * 200 - 100,
        }
        if plot.step_all(data):
            break


def demo_auto_scale():
    """Auto-scaling Y-axis with growing amplitude + noise."""
    plot = LivePlot(
        PlotConfig(
            width=1000, height=500,
            title="Auto-Scale — Growing Signal",
            auto_scale=AutoScaleMode.AUTO,
            smooth_auto_scale=True,
            auto_scale_speed=0.1,
            buffer_size=200,
            target_fps=60,
        ),
        window_name="LivePlot v3 — Auto Scale",
    )

    plot.add_series("signal", SeriesConfig(label="Growing Signal", color=(100, 200, 255)))

    x = 0
    while True:
        x += 1
        amplitude = 10 + (x / 5)
        noise = np.random.normal(0, amplitude * 0.1)
        y = math.sin(math.radians(x * 3)) * amplitude + noise

        if plot.step("signal", y):
            break


def demo_theme():
    """Cycle through built-in themes. Press T to switch."""
    plot = LivePlot(
        PlotConfig(
            width=1000, height=500,
            title="Theme Demo — Press [T] to cycle",
            y_min=-100, y_max=100,
            buffer_size=250,
            target_fps=60,
        ),
        window_name="LivePlot v3 — Themes",
    )

    plot.add_series("wave1", SeriesConfig(label="Wave A"))
    plot.add_series("wave2", SeriesConfig(label="Wave B"))

    x = 0
    while True:
        x += 1
        data = {
            "wave1": math.sin(math.radians(x)) * 80,
            "wave2": math.cos(math.radians(x * 1.5)) * 60,
        }
        if plot.step_all(data):
            break


def demo_stress():
    """8 series at once — performance test."""
    plot = LivePlot(
        PlotConfig(
            width=1400, height=700,
            title="Stress Test — 8 Series × 500 Buffer",
            y_min=-150, y_max=150,
            buffer_size=500,
            target_fps=0,  # unlimited — see max FPS
        ),
        window_name="LivePlot v3 — Stress Test",
    )

    names = []
    for i in range(8):
        name = f"ch{i}"
        names.append(name)
        plot.add_series(name, SeriesConfig(
            label=f"Channel {i}",
            show_glow=(i < 3),     # glow only on first 3 for perf
            line_width=1 + (i % 2),
        ))

    x = 0
    while True:
        x += 1
        data = {}
        for i, name in enumerate(names):
            freq = 1 + i * 0.3
            amp = 50 + i * 12
            phase = i * 45
            noise = np.random.normal(0, 3)
            data[name] = math.sin(math.radians(x * freq + phase)) * amp + noise

        if plot.step_all(data):
            break


# ────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────
DEMOS = {
    "single": demo_single,
    "multi": demo_multi,
    "auto": demo_auto_scale,
    "theme": demo_theme,
    "stress": demo_stress,
}


def main():
    if len(sys.argv) > 1 and sys.argv[1] in DEMOS:
        DEMOS[sys.argv[1]]()
    else:
        print(f"LivePlot v3.0 — Available demos:")
        print()
        for name, fn in DEMOS.items():
            doc = fn.__doc__.strip().split('\n')[0] if fn.__doc__ else ""
            print(f"  python -m live_plot.demo {name:8s}  →  {doc}")
        print()
        print("Running default: multi-series demo...")
        print("Shortcuts: [Q]uit [P]ause [S]creenshot [V]ideo [T]heme [R]eset [+/-]FPS")
        print()
        demo_multi()


if __name__ == "__main__":
    main()