"""
LivePlot v3.0 — Full Feature Test
===================================
ทดสอบทุกฟีเจอร์ กราฟละ 5 วินาที แล้วสลับไปอันถัดไปอัตโนมัติ

โครงสร้าง folder:
    project/
    ├── live_plot/          ← library (copy มาวางตรงนี้)
    │   ├── __init__.py
    │   ├── core.py
    │   └── ...
    └── test_all.py         ← ไฟล์นี้
"""

import math
import time
import numpy as np

from live_plot import (
    LivePlot, PlotConfig, SeriesConfig, AutoScaleMode,
    Theme, register_theme, TimingStrategy,
    PlatformInfo,
)

DURATION = 5.0  # วินาทีต่อกราฟ


def wait_between(name: str):
    """แสดงชื่อ test ถัดไป"""
    print(f"\n{'='*60}")
    print(f"  ▶ {name}")
    print(f"{'='*60}\n")


# ══════════════════════════════════════════════════════════════
# Test 1: Single Series — ง่ายที่สุด ค่าเดียว ไม่ต้อง add_series
# ══════════════════════════════════════════════════════════════
def test_01_single_value():
    wait_between("Test 01: Single Value (auto-create _default series)")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 01: Single Value",
            y_min=-100, y_max=100,
            target_fps=60,
        ),
        window_name="Test 01",
    )

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x = (x + 1) % 360
        value = math.sin(math.radians(x)) * 100
        if plot.step(value):
            return True  # user quit
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 2: Single Series + สีกำหนดเอง + color เปลี่ยนตาม runtime
# ══════════════════════════════════════════════════════════════
def test_02_single_with_color():
    wait_between("Test 02: Single Value + Dynamic Color")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 02: Color Changes Every 1s",
            y_min=-100, y_max=100,
            target_fps=60,
        ),
        window_name="Test 02",
    )

    colors = [
        (255, 100, 255),  # Magenta
        (100, 255, 100),  # Green
        (100, 200, 255),  # Cyan
        (80, 180, 255),   # Orange
    ]

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        elapsed = time.time() - start
        color_idx = int(elapsed) % len(colors)
        value = math.sin(math.radians(x * 2)) * 80

        if plot.step(value, color=colors[color_idx]):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 3: Multi-Series — 3 waveforms + legend + tooltip
# ══════════════════════════════════════════════════════════════
def test_03_multi_series():
    wait_between("Test 03: Multi-Series (sin/cos/sawtooth)")

    plot = LivePlot(
        PlotConfig(
            width=1200, height=500,
            title="Test 03: Multi-Series Signal Monitor",
            y_min=-120, y_max=120,
            buffer_size=300,
            target_fps=60,
            show_legend=True,
            enable_mouse_tooltip=True,
        ),
        window_name="Test 03",
    )

    plot.add_series("sin", SeriesConfig(
        label="sin(x)", color=(255, 100, 255), line_width=2,
        show_dot=True, show_glow=True, show_value=True,
    ))
    plot.add_series("cos", SeriesConfig(
        label="cos(x)", color=(100, 255, 150), line_width=2,
        show_dot=True, show_glow=True, show_value=True,
    ))
    plot.add_series("saw", SeriesConfig(
        label="sawtooth", color=(100, 180, 255), line_width=1,
        show_dot=True, show_glow=False, show_value=True,
    ))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        data = {
            "sin": math.sin(math.radians(x)) * 100,
            "cos": math.cos(math.radians(x)) * 80,
            "saw": ((x % 180) / 180.0) * 200 - 100,
        }
        if plot.step_all(data):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 4: Auto-Scale AUTO — y-axis ปรับตาม data (ขยาย+หด)
# ══════════════════════════════════════════════════════════════
def test_04_auto_scale():
    wait_between("Test 04: AutoScaleMode.AUTO (grows + shrinks)")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=500,
            title="Test 04: AUTO Scale — Amplitude Grows",
            auto_scale=AutoScaleMode.AUTO,
            auto_scale_padding=0.15,
            smooth_auto_scale=True,
            auto_scale_speed=0.12,
            buffer_size=200,
            target_fps=60,
        ),
        window_name="Test 04",
    )
    plot.add_series("signal", SeriesConfig(label="Growing Signal"))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        amplitude = 10 + (x / 3)
        noise = np.random.normal(0, amplitude * 0.1)
        y = math.sin(math.radians(x * 3)) * amplitude + noise

        if plot.step("signal", y):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 5: Auto-Scale AUTO_EXPAND — ขยายอย่างเดียว ไม่หดกลับ
# ══════════════════════════════════════════════════════════════
def test_05_auto_expand():
    wait_between("Test 05: AutoScaleMode.AUTO_EXPAND (only grows)")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=500,
            title="Test 05: AUTO_EXPAND — Y-axis Only Expands",
            auto_scale=AutoScaleMode.AUTO_EXPAND,
            smooth_auto_scale=True,
            auto_scale_speed=0.1,
            buffer_size=200,
            target_fps=60,
        ),
        window_name="Test 05",
    )
    plot.add_series("sig", SeriesConfig(label="Spike Signal"))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        # ปกติ amplitude 30 แต่มี spike ทุก 1 วินาที
        elapsed = time.time() - start
        if int(elapsed * 2) % 2 == 0:
            y = math.sin(math.radians(x * 5)) * 30
        else:
            y = math.sin(math.radians(x * 5)) * (30 + elapsed * 20)

        if plot.step("sig", y):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 6: NaN / None / inf handling — เส้นขาดแล้วต่อ
# ══════════════════════════════════════════════════════════════
def test_06_nan_handling():
    wait_between("Test 06: NaN/None/inf Gaps — Line Breaks")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 06: NaN Gaps (line breaks every 0.5s)",
            y_min=-100, y_max=100,
            buffer_size=300,
            target_fps=60,
        ),
        window_name="Test 06",
    )
    plot.add_series("data", SeriesConfig(label="Signal with Gaps"))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        elapsed = time.time() - start

        # สร้าง gap ทุก 0.5 วินาที (duration 0.1s)
        in_gap = (elapsed % 0.5) < 0.1

        if in_gap:
            values_to_test = [None, float('nan'), float('inf')]
            value = values_to_test[x % 3]
        else:
            value = math.sin(math.radians(x * 3)) * 80

        if plot.step("data", value):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 7: Theme cycling — 3 built-in + 1 custom
# ══════════════════════════════════════════════════════════════
def test_07_themes():
    wait_between("Test 07: Theme Cycling (auto every 1.2s)")

    # สร้าง custom theme
    cyber = Theme(
        name="cyberpunk",
        bg=(10, 5, 25),
        grid_major=(40, 20, 60),
        grid_minor=(25, 12, 40),
        grid_center=(60, 30, 80),
        border=(50, 25, 70),
        axis_label=(150, 100, 200),
        title=(220, 150, 255),
        value_text=(200, 130, 240),
        fps_text=(80, 50, 110),
        legend_bg=(15, 8, 30),
        legend_alpha=0.75,
        series_colors=(
            (255, 0, 255),
            (0, 255, 200),
            (0, 200, 255),
            (255, 100, 0),
        ),
    )
    register_theme(cyber)

    themes = ["dark", "light", "midnight", "cyberpunk"]

    plot = LivePlot(
        PlotConfig(
            width=1000, height=500,
            title="Test 07: Theme Demo",
            y_min=-100, y_max=100,
            buffer_size=250,
            target_fps=60,
            theme="dark",
        ),
        window_name="Test 07",
    )
    plot.add_series("wave1", SeriesConfig(label="Wave A"))
    plot.add_series("wave2", SeriesConfig(label="Wave B"))

    start = time.time()
    x = 0
    last_theme_change = 0
    while time.time() - start < DURATION:
        x += 1
        elapsed = time.time() - start

        # สลับ theme ทุก 1.2 วินาที
        theme_idx = int(elapsed / 1.2) % len(themes)
        if theme_idx != last_theme_change:
            plot.set_theme(themes[theme_idx])
            last_theme_change = theme_idx
            print(f"  → Theme: {themes[theme_idx]}")

        data = {
            "wave1": math.sin(math.radians(x)) * 80,
            "wave2": math.cos(math.radians(x * 1.5)) * 60,
        }
        if plot.step_all(data):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 8: ทุกตัวเลือก PlotConfig + SeriesConfig เต็มพิกัด
# ══════════════════════════════════════════════════════════════
def test_08_full_config():
    wait_between("Test 08: FULL PlotConfig + SeriesConfig")

    plot = LivePlot(
        PlotConfig(
            # ── ขนาด ──
            width=1200,
            height=600,

            # ── Margins ──
            margin_left=80,
            margin_top=60,
            margin_right=25,
            margin_bottom=45,

            # ── Y-axis ──
            y_min=-150.0,
            y_max=150.0,
            auto_scale=AutoScaleMode.FIXED,
            auto_scale_padding=0.1,
            smooth_auto_scale=False,
            auto_scale_speed=0.15,

            # ── Data ──
            buffer_size=400,
            min_update_interval=0,

            # ── Grid ──
            grid_x_spacing=40,
            grid_y_divisions=10,

            # ── Visual ──
            title="Test 08: Full Config — Every Option Set",
            theme="dark",
            show_fps=True,
            show_legend=True,
            show_zero_line=True,
            show_shortcuts_hint=True,
            antialiased=True,
            invert_y=True,

            # ── Interaction ──
            enable_mouse_tooltip=True,
            enable_keyboard=True,
            screenshot_dir=".",

            # ── Frame rate ──
            target_fps=60,
        ),
        window_name="Test 08",
    )

    # SeriesConfig — ทุก field กำหนดชัดเจน
    plot.add_series("main", SeriesConfig(
        label="Main Signal",
        color=(255, 100, 255),
        line_width=2,
        show_dot=True,
        dot_radius=6,
        show_value=True,
        show_glow=True,
    ))
    plot.add_series("secondary", SeriesConfig(
        label="Secondary",
        color=(100, 255, 150),
        line_width=1,
        show_dot=True,
        dot_radius=4,
        show_value=True,
        show_glow=False,
    ))
    plot.add_series("noise", SeriesConfig(
        label="Noise Floor",
        color=(80, 180, 255),
        line_width=1,
        show_dot=False,          # ไม่มีจุด
        dot_radius=3,
        show_value=False,        # ไม่แสดงค่า
        show_glow=False,
    ))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        data = {
            "main": math.sin(math.radians(x)) * 120,
            "secondary": math.cos(math.radians(x * 0.7)) * 80 + 20,
            "noise": np.random.normal(0, 15),
        }
        if plot.step_all(data):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 9: invert_y=False — ค่ามากอยู่ข้างล่าง (แบบ screen coords)
# ══════════════════════════════════════════════════════════════
def test_09_invert_y_false():
    wait_between("Test 09: invert_y=False (higher values at bottom)")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 09: invert_y=False (Y increases downward)",
            y_min=0, y_max=100,
            invert_y=False,
            target_fps=60,
        ),
        window_name="Test 09",
    )
    plot.add_series("depth", SeriesConfig(label="Depth (cm)"))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        y = 50 + math.sin(math.radians(x * 2)) * 40

        if plot.step("depth", y):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 10: Zero Line — ข้อมูลข้าม 0 ไปมา
# ══════════════════════════════════════════════════════════════
def test_10_zero_line():
    wait_between("Test 10: Zero Line Highlight")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 10: Zero Line (y crosses 0)",
            y_min=-80, y_max=80,
            show_zero_line=True,
            target_fps=60,
        ),
        window_name="Test 10",
    )
    plot.add_series("signal", SeriesConfig(label="Oscillator"))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        y = math.sin(math.radians(x * 3)) * 60 + math.sin(math.radians(x * 7)) * 15

        if plot.step("signal", y):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 11: Rate Limiting — min_update_interval
# ══════════════════════════════════════════════════════════════
def test_11_rate_limit():
    wait_between("Test 11: Rate Limiting (min_update_interval=0.05 → ~20 FPS render)")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 11: Rate Limited to ~20 updates/sec",
            y_min=-100, y_max=100,
            min_update_interval=0.05,  # 50ms = ~20 Hz
            target_fps=60,
        ),
        window_name="Test 11",
    )

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        value = math.sin(math.radians(x)) * 100
        if plot.step(value):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 12: Dynamic Y-limits — set_y_limits() ตอน runtime
# ══════════════════════════════════════════════════════════════
def test_12_dynamic_y_limits():
    wait_between("Test 12: set_y_limits() — changes every 1s")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 12: Dynamic Y-Limits",
            y_min=-50, y_max=50,
            target_fps=60,
        ),
        window_name="Test 12",
    )
    plot.add_series("data", SeriesConfig(label="Signal"))

    limits = [(-50, 50), (-100, 100), (-200, 200), (-30, 30)]

    start = time.time()
    x = 0
    last_limit = -1
    while time.time() - start < DURATION:
        x += 1
        elapsed = time.time() - start

        limit_idx = int(elapsed) % len(limits)
        if limit_idx != last_limit:
            lo, hi = limits[limit_idx]
            plot.set_y_limits(lo, hi)
            last_limit = limit_idx
            print(f"  → Y-limits: [{lo}, {hi}]")

        y = math.sin(math.radians(x * 2)) * 40

        if plot.step("data", y):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 13: Pause/Resume — ทดสอบ .paused property
# ══════════════════════════════════════════════════════════════
def test_13_pause_resume():
    wait_between("Test 13: Pause/Resume (auto-toggle every 1s)")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 13: Auto Pause/Resume",
            y_min=-100, y_max=100,
            target_fps=60,
        ),
        window_name="Test 13",
    )

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        elapsed = time.time() - start

        # toggle pause ทุก 1 วินาที
        plot.paused = (int(elapsed) % 2 == 1)

        value = math.sin(math.radians(x * 3)) * 100
        if plot.step(value):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 14: Clear Data — clear() + clear("name")
# ══════════════════════════════════════════════════════════════
def test_14_clear():
    wait_between("Test 14: Clear Data (auto-clear every 2s)")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 14: Auto-Clear Every 2s",
            y_min=-100, y_max=100,
            buffer_size=200,
            target_fps=60,
        ),
        window_name="Test 14",
    )
    plot.add_series("a", SeriesConfig(label="Series A"))
    plot.add_series("b", SeriesConfig(label="Series B"))

    start = time.time()
    x = 0
    last_clear = 0
    while time.time() - start < DURATION:
        x += 1
        elapsed = time.time() - start

        clear_cycle = int(elapsed / 2)
        if clear_cycle != last_clear:
            if clear_cycle % 2 == 1:
                plot.clear("a")   # clear เฉพาะ A
                print("  → Cleared series A only")
            else:
                plot.clear()      # clear ทั้งหมด
                print("  → Cleared ALL series")
            last_clear = clear_cycle

        data = {
            "a": math.sin(math.radians(x * 2)) * 80,
            "b": math.cos(math.radians(x * 3)) * 60,
        }
        if plot.step_all(data):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 15: Add/Remove Series — dynamic
# ══════════════════════════════════════════════════════════════
def test_15_add_remove_series():
    wait_between("Test 15: Dynamic Add/Remove Series")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 15: Series Added/Removed Dynamically",
            y_min=-100, y_max=100,
            target_fps=60,
        ),
        window_name="Test 15",
    )
    plot.add_series("base", SeriesConfig(label="Base"))

    start = time.time()
    x = 0
    extra_added = False
    while time.time() - start < DURATION:
        x += 1
        elapsed = time.time() - start

        # 0-2s: base only → 2-3.5s: add "extra" → 3.5-5s: remove "extra"
        if elapsed > 2.0 and not extra_added:
            plot.add_series("extra", SeriesConfig(
                label="Extra (added at 2s)", color=(100, 255, 255),
            ))
            extra_added = True
            print("  → Added 'extra' series")
        elif elapsed > 3.5 and extra_added:
            plot.remove_series("extra")
            extra_added = False
            print("  → Removed 'extra' series")

        data = {"base": math.sin(math.radians(x * 2)) * 80}
        if extra_added:
            data["extra"] = math.cos(math.radians(x * 3)) * 50

        if plot.step_all(data):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 16: Chain API — method chaining add_series
# ══════════════════════════════════════════════════════════════
def test_16_chain_api():
    wait_between("Test 16: Method Chaining (.add_series().add_series())")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 16: Chained API",
            y_min=-100, y_max=100,
            target_fps=60,
        ),
        window_name="Test 16",
    )

    # Chain!
    (plot
        .add_series("a", SeriesConfig(label="Alpha"))
        .add_series("b", SeriesConfig(label="Beta"))
        .add_series("c", SeriesConfig(label="Gamma"))
    )

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        data = {
            "a": math.sin(math.radians(x)) * 80,
            "b": math.sin(math.radians(x + 120)) * 80,
            "c": math.sin(math.radians(x + 240)) * 80,
        }
        if plot.step_all(data):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 17: Stress Test — 8 series × 500 buffer, unlimited FPS
# ══════════════════════════════════════════════════════════════
def test_17_stress():
    wait_between("Test 17: Stress Test — 8 Series × 500 Buffer (UNLIMITED FPS)")

    plot = LivePlot(
        PlotConfig(
            width=1400, height=700,
            title="Test 17: STRESS TEST",
            y_min=-150, y_max=150,
            buffer_size=500,
            target_fps=0,         # UNLIMITED
            show_legend=True,
            show_fps=True,
        ),
        window_name="Test 17",
    )

    names = []
    for i in range(8):
        name = f"ch{i}"
        names.append(name)
        plot.add_series(name, SeriesConfig(
            label=f"Channel {i}",
            show_glow=(i < 3),
            line_width=1 + (i % 2),
        ))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        data = {}
        for i, name in enumerate(names):
            freq = 1 + i * 0.3
            amp = 50 + i * 12
            phase = i * 45
            data[name] = math.sin(math.radians(x * freq + phase)) * amp + np.random.normal(0, 3)

        if plot.step_all(data):
            return True

    final_fps = plot.fps
    plot.close()
    print(f"  → Peak FPS: {final_fps:.0f}")
    return False


# ══════════════════════════════════════════════════════════════
# Test 18: Antialiased OFF vs ON
# ══════════════════════════════════════════════════════════════
def test_18_antialiased_off():
    wait_between("Test 18: Antialiased=False (pixelated lines)")

    plot = LivePlot(
        PlotConfig(
            width=1000, height=400,
            title="Test 18: antialiased=False",
            y_min=-100, y_max=100,
            antialiased=False,     # LINE_8 instead of LINE_AA
            target_fps=60,
        ),
        window_name="Test 18",
    )
    plot.add_series("data", SeriesConfig(label="Jagged Line", line_width=2))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        if plot.step("data", math.sin(math.radians(x * 2)) * 80):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 19: No FPS, No Legend, No Hints — minimal mode
# ══════════════════════════════════════════════════════════════
def test_19_minimal():
    wait_between("Test 19: Minimal Mode (no FPS, no legend, no hints)")

    plot = LivePlot(
        PlotConfig(
            width=800, height=300,
            title="",                         # no title
            y_min=-50, y_max=50,
            show_fps=False,
            show_legend=False,
            show_zero_line=False,
            show_shortcuts_hint=False,
            enable_mouse_tooltip=False,
            enable_keyboard=False,            # only Q works
            target_fps=60,
        ),
        window_name="Test 19",
    )

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        if plot.step(math.sin(math.radians(x * 4)) * 40):
            return True
    plot.close()
    return False


# ══════════════════════════════════════════════════════════════
# Test 20: Legacy API — from_legacy() backward compatibility
# ══════════════════════════════════════════════════════════════
def test_20_legacy():
    wait_between("Test 20: Legacy API — from_legacy()")

    import cv2

    # v1-style constructor
    plot = LivePlot.from_legacy(
        w=1000, h=400,
        yLimit=[-100, 100],
        interval=0.001,
        invert=True,
        char="Test 20: Legacy Mode",
    )

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        y = int(math.sin(math.radians(x)) * 100)
        img = plot.update(y, color=(255, 100, 255))  # v1-style update
        cv2.imshow("Test 20", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return True

    cv2.destroyWindow("Test 20")
    return False


# ══════════════════════════════════════════════════════════════
# Test 21: update() (manual) + embed plot on blank canvas
# ══════════════════════════════════════════════════════════════
def test_21_manual_embed():
    wait_between("Test 21: Manual update() + Embed on Custom Canvas")

    import cv2

    plot = LivePlot(
        PlotConfig(
            width=400, height=200,
            title="Embedded",
            y_min=-100, y_max=100,
            margin_left=50, margin_top=30,
            margin_bottom=25, margin_right=15,
            show_shortcuts_hint=False,
        ),
        window_name="_hidden_",
    )
    plot.add_series("sig", SeriesConfig(label="Signal"))

    start = time.time()
    x = 0
    while time.time() - start < DURATION:
        x += 1
        plot_img = plot.update("sig", math.sin(math.radians(x * 3)) * 80)

        # สร้าง canvas ใหญ่ แล้ว embed plot ลงไป
        canvas = np.zeros((500, 800, 3), dtype=np.uint8)
        canvas[:] = (40, 30, 20)

        # วาง title
        cv2.putText(canvas, "Test 21: Custom Canvas with Embedded Plot",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 220), 1)

        # วาง plot ที่มุมขวาล่าง
        h, w = plot_img.shape[:2]
        canvas[canvas.shape[0]-h-20:canvas.shape[0]-20,
               canvas.shape[1]-w-20:canvas.shape[1]-20] = plot_img

        cv2.imshow("Test 21", canvas)
        if cv2.waitKey(16) & 0xFF == ord('q'):
            return True

    cv2.destroyWindow("Test 21")
    return False


# ══════════════════════════════════════════════════════════════
# MAIN — รันทุก test ต่อกัน
# ══════════════════════════════════════════════════════════════
ALL_TESTS = [
    test_01_single_value,
    test_02_single_with_color,
    test_03_multi_series,
    test_04_auto_scale,
    test_05_auto_expand,
    test_06_nan_handling,
    test_07_themes,
    test_08_full_config,
    test_09_invert_y_false,
    test_10_zero_line,
    test_11_rate_limit,
    test_12_dynamic_y_limits,
    test_13_pause_resume,
    test_14_clear,
    test_15_add_remove_series,
    test_16_chain_api,
    test_17_stress,
    test_18_antialiased_off,
    test_19_minimal,
    test_20_legacy,
    test_21_manual_embed,
]


if __name__ == "__main__":
    print(f"╔══════════════════════════════════════════════════════════╗")
    print(f"║  LivePlot v3.0 — Full Feature Test Suite                ║")
    print(f"║  {len(ALL_TESTS)} tests × {DURATION}s each = ~{len(ALL_TESTS) * DURATION:.0f}s total                      ║")
    print(f"║  Platform: {PlatformInfo.summary():44s} ║")
    print(f"║  Press Q during any test to quit early                  ║")
    print(f"╚══════════════════════════════════════════════════════════╝")

    passed = 0
    for i, test_fn in enumerate(ALL_TESTS):
        user_quit = test_fn()
        if user_quit:
            print(f"\n⛔ User quit at test {i+1}/{len(ALL_TESTS)}")
            break
        passed += 1
        print(f"  ✅ Test {i+1:02d} passed ({passed}/{len(ALL_TESTS)})")

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{len(ALL_TESTS)} tests completed")
    if passed == len(ALL_TESTS):
        print(f"  🎉 ALL TESTS PASSED!")
    print(f"{'='*60}")