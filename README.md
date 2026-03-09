# 📊 LivePlot v3.0

> **Cross-Platform High-Performance Real-Time OpenCV Plotter**
> เวอร์ชัน 3.0.1 | Python 3.10+ | Windows & Linux (รวม Wayland)
> Dependencies: `numpy >= 1.21` · `opencv-python >= 4.5`

---

## สารบัญ

**ส่วนที่ 1 — การใช้งาน**

1. [ติดตั้งและโครงสร้างโปรเจกต์](#1-ติดตั้งและโครงสร้างโปรเจกต์)
2. [Quick Start — เริ่มต้นใน 2 นาที](#2-quick-start)
3. [API Reference — ทุก method ที่ใช้ได้](#3-api-reference)
4. [การตั้งค่ากราฟ (PlotConfig)](#4-การตั้งค่ากราฟ)
5. [การตั้งค่าเส้นข้อมูล (SeriesConfig)](#5-การตั้งค่าเส้นข้อมูล)
6. [Auto-Scale — ปรับ Y-axis อัตโนมัติ](#6-auto-scale)
7. [Theme System — เปลี่ยน/สร้าง ธีมสี](#7-theme-system)
8. [Keyboard Shortcuts & Mouse Interaction](#8-keyboard-shortcuts--mouse)
9. [Screenshot & Video Recording](#9-screenshot--video-recording)
10. [ตัวอย่างการใช้งานจริง](#10-ตัวอย่างการใช้งานจริง)
11. [Backward Compatibility — ใช้กับโค้ดเดิม](#11-backward-compatibility)
12. [Troubleshooting & FAQ](#12-troubleshooting--faq)

**ส่วนที่ 2 — อธิบายโค้ดแต่ละ Module**

13. [ภาพรวมสถาปัตยกรรม (Architecture Overview)](#13-ภาพรวมสถาปัตยกรรม)
14. [platform_utils.py — แก้ปัญหา Cross-Platform](#14-platform_utilspy)
15. [frame_timer.py — ควบคุม Frame Rate ข้าม OS](#15-frame_timerpy)
16. [colors.py — ระบบธีมสี](#16-colorspy)
17. [config.py — โครงสร้างการตั้งค่า](#17-configpy)
18. [series.py — Circular Buffer](#18-seriespy)
19. [renderer.py — ท่อวาดภาพ (Render Pipeline)](#19-rendererpy)
20. [interactions.py — Mouse, Keyboard, Recording](#20-interactionspy)
21. [core.py — คลาสหลัก LivePlot](#21-corepy)

---

# ส่วนที่ 1 — การใช้งาน

---

## 1. ติดตั้งและโครงสร้างโปรเจกต์

### ติดตั้ง Dependencies

```bash
pip install numpy opencv-python
```

### โครงสร้างไฟล์

```
live_plot/
├── __init__.py          # Public API exports + Wayland early fix
├── __main__.py          # python -m live_plot
├── platform_utils.py    # OS detection, timer boost, HiDPI, key normalization, Wayland fix
├── colors.py            # Theme system (dark / light / midnight / custom)
├── config.py            # PlotConfig, SeriesConfig, AutoScaleMode
├── series.py            # Circular buffer data container
├── renderer.py          # Background cache + drawing pipeline
├── frame_timer.py       # Cross-platform frame rate controller
├── interactions.py      # Mouse (with retry), keyboard shortcuts, screenshot, video
├── core.py              # Main LivePlot class (window init with waitKey fix)
└── demo.py              # 5 demo scripts
```

### วางไฟล์ในโปรเจกต์

```
your_project/
├── live_plot/           ← วาง folder ทั้งหมดตรงนี้
│   ├── __init__.py
│   ├── ...
├── main.py              ← โค้ดของคุณ
```

### รัน Demo

```bash
python -m live_plot.demo              # default: multi-series
python -m live_plot.demo single       # sine wave เส้นเดียว
python -m live_plot.demo multi        # 3 waveforms
python -m live_plot.demo auto         # auto-scaling
python -m live_plot.demo theme        # สลับ theme ด้วยปุ่ม T
python -m live_plot.demo stress       # 8 เส้น × 500 buffer (benchmark)
```

---

## 2. Quick Start

### 2.1 แบบง่ายที่สุด — `step()` API (แนะนำ)

```python
import math
from live_plot import LivePlot, PlotConfig

plot = LivePlot(PlotConfig(
    title="My First Plot",
    y_min=-100, y_max=100,
))

x = 0
while True:
    x = (x + 1) % 360
    value = math.sin(math.radians(x)) * 100

    if plot.step(value):        # update + render + display + input
        break                   # user pressed Q or ESC
```

`step()` ทำทุกอย่างให้ในคำสั่งเดียว:
1. push ข้อมูลลง buffer
2. render กราฟ
3. แสดงบน OpenCV window
4. จัดการ frame rate
5. รับ keyboard input
6. return `True` เมื่อ user กด Q

### 2.2 หลายเส้น

```python
from live_plot import LivePlot, PlotConfig, SeriesConfig

plot = LivePlot(PlotConfig(
    title="Sensor Dashboard",
    y_min=-50, y_max=150,
    buffer_size=300,
))

plot.add_series("temp", SeriesConfig(label="Temp °C", color=(100, 200, 255)))
plot.add_series("hum",  SeriesConfig(label="Humidity %", color=(100, 255, 100)))

while True:
    data = {"temp": read_temp(), "hum": read_humidity()}
    if plot.step_all(data):
        break
```

### 2.3 แบบ Manual Control (แยก render กับ display)

```python
import cv2
from live_plot import LivePlot, PlotConfig

plot = LivePlot(PlotConfig(y_min=0, y_max=100))

while True:
    img = plot.update(42.0)          # render เฉยๆ ได้ np.ndarray กลับมา
    cv2.imshow("Plot", img)          # แสดงเอง
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
```

ใช้วิธีนี้เมื่อต้องการวาง plot ลงบนภาพอื่น หรือ embed ใน GUI framework

---

## 3. API Reference

### 3.1 Constructor

```python
LivePlot(config=None, *, window_name="LivePlot")
```

| Parameter | Type | Default | คำอธิบาย |
|---|---|---|---|
| `config` | `PlotConfig` | `PlotConfig()` | การตั้งค่าทั้งหมดของกราฟ |
| `window_name` | `str` | `"LivePlot"` | ชื่อหน้าต่าง OpenCV (keyword-only) |

### 3.2 Series Management

```python
plot.add_series(name, config=None)    # เพิ่มเส้น → return self (chainable)
plot.remove_series(name)              # ลบเส้น → return self
```

### 3.3 Data Update (render เฉยๆ ไม่แสดง)

```python
img = plot.update(42.0)              # เส้นเดียว (auto-create "_default")
img = plot.update(42.0, color=BGR)   # เส้นเดียว + กำหนดสี
img = plot.update("temp", 42.0)      # named series
img = plot.update_all({"temp": 25, "hum": 60})  # หลายเส้นพร้อมกัน
```

**Return:** `np.ndarray` shape `(height, width, 3)` dtype `uint8` BGR

### 3.4 Step (All-in-One)

```python
quit = plot.step(42.0)               # update + render + display + input
quit = plot.step("temp", 42.0)       # named series
quit = plot.step_all({"a": 1, "b": 2})
```

**Return:** `True` ถ้า user กด Q/ESC (ต้องการออก)

### 3.5 Utilities

```python
plot.clear()                  # ล้างข้อมูลทุก series
plot.clear("temp")            # ล้างเฉพาะ series
plot.set_y_limits(-200, 200)  # เปลี่ยน Y-axis ตอน runtime
plot.set_theme("light")       # สลับ theme
plot.close()                  # ปิดทุกอย่าง (window, recording, timer)
```

### 3.6 Properties

```python
plot.fps          # float — FPS ปัจจุบัน
plot.paused       # bool  — กำลัง pause อยู่หรือไม่ (อ่าน/เขียนได้)
plot.canvas       # np.ndarray — ภาพล่าสุดที่ render
```

### 3.7 Backward-Compatible Factory

```python
# สำหรับโค้ด v1/v2 เดิม
plot = LivePlot.from_legacy(w=1200, h=600, yLimit=[-100, 100], interval=0.01)
```

---

## 4. การตั้งค่ากราฟ

```python
PlotConfig(
    # ── ขนาดหน้าต่าง ──
    width=800,                     # pixels
    height=480,

    # ── Margins ──
    margin_left=70,                # พื้นที่ Y labels
    margin_top=50,                 # พื้นที่ title + current values
    margin_right=20,
    margin_bottom=40,              # พื้นที่ status bar

    # ── Y-axis ──
    y_min=0.0,
    y_max=100.0,
    auto_scale=AutoScaleMode.FIXED,   # FIXED / AUTO / AUTO_EXPAND
    auto_scale_padding=0.1,           # 10% เว้นขอบ
    smooth_auto_scale=True,           # animation เมื่อ y-axis เปลี่ยน
    auto_scale_speed=0.15,            # ความเร็ว lerp (0=หยุด, 1=ทันที)

    # ── Data ──
    buffer_size=200,                  # จำนวนจุดที่เก็บ
    min_update_interval=0,            # rate limit (0 = ไม่จำกัด)

    # ── Grid ──
    grid_x_spacing=50,                # pixels ระหว่างเส้น grid แนวตั้ง
    grid_y_divisions=8,               # จำนวนช่องแนวนอน

    # ── Visual ──
    title="",                         # ข้อความ title
    theme="dark",                     # "dark" / "light" / "midnight"
    show_fps=True,
    show_legend=True,                 # แสดงเมื่อมี >1 series
    show_zero_line=True,              # เส้น y=0
    show_shortcuts_hint=True,         # แสดง [S]ave [P]ause ด้านล่าง
    antialiased=True,
    invert_y=True,                    # True = ค่ามากอยู่ข้างบน (ปกติ)

    # ── Interaction ──
    enable_mouse_tooltip=True,        # เลื่อนเมาส์ดูค่า
    enable_keyboard=True,             # keyboard shortcuts
    screenshot_dir=".",               # folder เก็บ screenshot/video

    # ── Frame rate ──
    target_fps=60,                    # 0 = ไม่จำกัด (benchmark mode)
)
```

### Layout Diagram

```
┌──────────────────────────── width ───────────────────────────┐
│                        margin_top (50px)                      │
│    ┌── title (centered) ──┐      ┌── current values ──┐     │
│ m  ├──────────────────────┴──────┴────────────────────┤  m  │
│ a  │ (plot_x, plot_y)                                  │  a  │
│ r  │                                                    │  r  │
│ g  │  Y labels         PLOT AREA                       │  g  │
│ _  │  (left)          (plot_w × plot_h)                │  _  │
│ l  │                                                    │  r  │
│ e  │                    data lines                      │  i  │
│ f  │                    legend box                      │  g  │
│ t  │                    tooltip                         │  h  │
│    ├────────────────────────────────────────────────────┤  t  │
│    │ [S]ave [P]ause [R]eset [Q]uit          60 FPS     │     │
│    │              margin_bottom (40px)                   │     │
└────┴────────────────────────────────────────────────────┴─────┘
```

---

## 5. การตั้งค่าเส้นข้อมูล

```python
SeriesConfig(
    label="Temperature",       # ชื่อแสดงใน legend
    color=(100, 200, 255),     # BGR (ไม่ใช่ RGB!)
    line_width=2,              # ความหนาเส้น (1-3 ดีที่สุด)
    show_dot=True,             # จุดที่ปลายเส้น
    dot_radius=5,              # ขนาดจุด
    show_value=True,           # แสดงค่าปัจจุบันด้านบน
    show_glow=True,            # เอฟเฟกต์เรืองแสง
)
```

### Auto-assign สี

ถ้าไม่ระบุ config เลย สีจะถูกเลือกจาก palette ของ theme ปัจจุบันอัตโนมัติ:

```python
plot.add_series("ch0")    # สี #1 จาก theme
plot.add_series("ch1")    # สี #2 จาก theme
plot.add_series("ch2")    # สี #3 ...
```

---

## 6. Auto-Scale

### 3 โหมด

```python
from live_plot import AutoScaleMode

# 1. FIXED — ค่า y_min/y_max คงที่ตลอด
PlotConfig(y_min=0, y_max=100, auto_scale=AutoScaleMode.FIXED)

# 2. AUTO — ปรับให้พอดีกับข้อมูลใน buffer (ขยาย+หด)
PlotConfig(auto_scale=AutoScaleMode.AUTO)

# 3. AUTO_EXPAND — ขยายได้อย่างเดียว ไม่หดกลับ
PlotConfig(auto_scale=AutoScaleMode.AUTO_EXPAND)
```

### Smooth Transition (ใหม่ใน v3)

```python
PlotConfig(
    auto_scale=AutoScaleMode.AUTO,
    smooth_auto_scale=True,       # เปิด animation
    auto_scale_speed=0.15,        # 0.05=ช้านุ่มนวล, 0.5=เร็ว, 1.0=ทันที
)
```

เมื่อข้อมูลเปลี่ยน range ทันที Y-axis จะค่อยๆ เลื่อนด้วย linear interpolation (lerp) แทนที่จะกระโดด:

```
display_y_min += (target_y_min - display_y_min) × speed
display_y_max += (target_y_max - display_y_max) × speed
```

---

## 7. Theme System

### 3 Built-in Themes

```python
plot.set_theme("dark")       # default — พื้นเข้ม ตาไม่ล้า
plot.set_theme("light")      # พื้นขาว — สำหรับ screenshot/report
plot.set_theme("midnight")   # พื้นดำอมน้ำเงิน — โทนอบอุ่น
```

หรือกด **T** ขณะรัน demo เพื่อสลับ theme แบบ live

### สร้าง Custom Theme

```python
from live_plot import Theme, register_theme

my_theme = Theme(
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
        (255, 0, 255),     # Neon pink
        (0, 255, 200),     # Cyan
        (0, 200, 255),     # Amber
        (255, 100, 0),     # Blue
    ),
)

register_theme(my_theme)

plot = LivePlot(PlotConfig(theme="cyberpunk"))
# หรือตอน runtime:
plot.set_theme("cyberpunk")
```

---

## 8. Keyboard Shortcuts & Mouse

### Keyboard Shortcuts

ทำงานอัตโนมัติเมื่อใช้ `step()` / `step_all()`:

| ปุ่ม | การทำงาน |
|---|---|
| **Q** หรือ **ESC** | ออกจากโปรแกรม |
| **P** หรือ **Space** | Pause / Resume (หยุดรับข้อมูลชั่วคราว) |
| **S** | บันทึก Screenshot (PNG) |
| **V** | เริ่ม/หยุด บันทึก Video (MP4) |
| **R** | Reset — ล้างข้อมูลทุก series |
| **T** | สลับ Theme (dark → light → midnight → ...) |
| **+** / **-** | เพิ่ม/ลด target FPS ทีละ 10 |

ปิด keyboard shortcuts:

```python
PlotConfig(enable_keyboard=False)
```

### Mouse Tooltip

เลื่อนเมาส์เข้าไปใน plot area → เห็นเส้น crosshair แนวตั้ง + ค่าของทุก series ที่ตำแหน่งนั้น

ปิด tooltip:

```python
PlotConfig(enable_mouse_tooltip=False)
```

---

## 9. Screenshot & Video Recording

### Screenshot (กด S)

```
liveplot_20260219_143052_123.png   ← บันทึกที่ screenshot_dir
```

### Screenshot จากโค้ด

```python
from live_plot import save_screenshot

img = plot.update("data", value)
path = save_screenshot(img, directory="./captures")
print(f"Saved to {path}")
```

### Video Recording (กด V)

กด V ครั้งแรก → เริ่มบันทึก
กด V อีกครั้ง → หยุดบันทึก

```
liveplot_20260219_143100.mp4    ← codec: mp4v (ทำงานทั้ง Windows/Linux)
```

### Video จากโค้ด

```python
from live_plot import VideoRecorder

recorder = VideoRecorder(width=800, height=480, fps=30)
recorder.start()

while True:
    img = plot.update("data", value)
    recorder.write_frame(img)
    if should_stop:
        break

path = recorder.stop()
print(f"Recorded to {path}")
```

---

## 10. ตัวอย่างการใช้งานจริง

### 10.1 Arduino Sensor Monitoring

```python
import serial
from live_plot import LivePlot, PlotConfig, SeriesConfig

plot = LivePlot(PlotConfig(
    title="Arduino ADC", y_min=0, y_max=1023,
    buffer_size=500, target_fps=30,
))
plot.add_series("a0", SeriesConfig(label="A0"))

ser = serial.Serial('/dev/ttyUSB0', 9600)

while True:
    line = ser.readline().decode().strip()
    try:
        value = float(line)
    except ValueError:
        value = None              # LivePlot handles None gracefully

    if plot.step("a0", value):
        break
```

### 10.2 Computer Vision + Plot Overlay

```python
import cv2
from live_plot import LivePlot, PlotConfig, SeriesConfig

plot = LivePlot(PlotConfig(
    width=400, height=200,
    title="Confidence", y_min=0, y_max=100,
    margin_left=50, margin_top=35, margin_bottom=25,
    show_shortcuts_hint=False,
))
plot.add_series("conf", SeriesConfig(label="Confidence %"))

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    confidence = detect_face(frame)              # your function

    plot_img = plot.update("conf", confidence)   # render only (no display)

    # Overlay plot on bottom-right corner of camera frame
    h, w = plot_img.shape[:2]
    frame[-h:, -w:] = plot_img

    cv2.imshow("Camera", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
```

### 10.3 Multi-Thread Network Monitor

```python
import time, threading, psutil
from live_plot import LivePlot, PlotConfig, SeriesConfig, AutoScaleMode

plot = LivePlot(PlotConfig(
    title="Network Traffic",
    auto_scale=AutoScaleMode.AUTO,
    buffer_size=300,
    target_fps=30,
))
plot.add_series("rx", SeriesConfig(label="RX KB/s", color=(100, 255, 100)))
plot.add_series("tx", SeriesConfig(label="TX KB/s", color=(255, 100, 100)))

def monitor():
    """Background thread — thread-safe!"""
    prev = psutil.net_io_counters()
    while True:
        time.sleep(0.1)
        curr = psutil.net_io_counters()
        # update() is thread-safe → call from any thread
        plot.update_all({
            "rx": (curr.bytes_recv - prev.bytes_recv) / 102.4,
            "tx": (curr.bytes_sent - prev.bytes_sent) / 102.4,
        })
        prev = curr

threading.Thread(target=monitor, daemon=True).start()

# Main thread handles display
while True:
    if plot.step_all({}):   # empty dict → just display latest render
        break
```

### 10.4 ML Training Loss with Auto-Scale

```python
from live_plot import LivePlot, PlotConfig, SeriesConfig, AutoScaleMode

plot = LivePlot(PlotConfig(
    title="Training Progress",
    auto_scale=AutoScaleMode.AUTO_EXPAND,
    smooth_auto_scale=True,
    auto_scale_speed=0.08,
    buffer_size=1000,
    show_fps=False,
))
plot.add_series("train", SeriesConfig(label="Train Loss", color=(255, 100, 100)))
plot.add_series("val",   SeriesConfig(label="Val Loss",   color=(100, 200, 255)))

for epoch in range(100):
    train_loss = train_one_epoch(model, train_loader)
    val_loss   = evaluate(model, val_loader)

    if plot.step_all({"train": train_loss, "val": val_loss}):
        break
```

---

## 11. Backward Compatibility

### จากโค้ด v1 เดิม

```python
# ──── v1 (เดิม) ────
from live_plot_v1 import LivePlot
xPlot = LivePlot(w=1200, yLimit=[-100, 100], interval=0.01)
img = xPlot.update(int(math.sin(math.radians(x)) * 100))
cv2.imshow("Image", img)

# ──── v3 (ใหม่) ── เปลี่ยนแค่ 2 บรรทัด ────
from live_plot import LivePlot
xPlot = LivePlot.from_legacy(w=1200, yLimit=[-100, 100], interval=0.01)
img = xPlot.update(int(math.sin(math.radians(x)) * 100))
cv2.imshow("Image", img)
```

### จากโค้ด v2

v2 API (`update`, `update_all`, `clear`, `set_y_limits`) ทำงานเหมือนเดิมทุกประการ
v3 เพิ่ม `step()`, `step_all()`, theme system, interactions เข้ามาโดยไม่กระทบ API เดิม

---

## 12. Troubleshooting & FAQ

### Q: หน้าต่างไม่ขึ้น / ค้าง

ถ้าใช้ `update()` แบบ manual ต้องมี `cv2.waitKey()` ใน loop:

```python
img = plot.update(value)
cv2.imshow("Plot", img)
cv2.waitKey(1)             # ← จำเป็น! OpenCV ต้องการเพื่อ process GUI events
```

ถ้าใช้ `step()` ไม่ต้องเรียก `waitKey` เอง — `step()` จัดการให้แล้ว

### Q: ขยับเมาส์แล้วกราฟเร่ง (v1/v2 เท่านั้น)

ปัญหานี้**แก้แล้วใน v3** — `FrameTimer` คำนวณ delay แบบ adaptive ไม่ขึ้นกับ `waitKey(1)` อีกต่อไป

### Q: ข้อมูลเป็น NaN / None / inf

LivePlot จัดการได้อัตโนมัติ — เส้นจะ**ขาด**ตรงจุดที่เป็น NaN แล้วต่อใหม่เมื่อได้ข้อมูลปกติ

### Q: KeyError: Series 'xxx' not found

ต้อง `add_series()` ก่อน `update()` เสมอ:

```python
plot.add_series("temp")         # ← ต้องเพิ่มก่อน
plot.update("temp", 25.0)       # ✓ ใช้ได้
```

ยกเว้นแบบค่าเดียว `plot.update(25.0)` → auto-create

### Q: "Could not find the Qt platform plugin 'wayland'" (Linux)

เกิดบน Linux ที่ใช้ Wayland session (เช่น Ubuntu 22.04+, Fedora 38+)
OpenCV ที่ build มาด้วย Qt backend อาจไม่มี Wayland plugin รวมมาด้วย

**v3 แก้ให้อัตโนมัติแล้ว** — `__init__.py` ตรวจว่า `XDG_SESSION_TYPE=wayland` แล้วตั้ง `QT_QPA_PLATFORM=xcb` **ก่อน** import `cv2` ทำให้ OpenCV ใช้ X11 ผ่าน XWayland แทน

ถ้ายังเจอ warning ให้ตั้ง environment variable เองก่อนรัน:

```bash
export QT_QPA_PLATFORM=xcb
python -m live_plot.demo
```

### Q: "NULL window handler" crash ตอนเริ่ม (Linux Qt)

เกิดเมื่อ `cv2.setMouseCallback()` ถูกเรียกก่อน window handle พร้อม
พบบ่อยบน Qt backend + Wayland เพราะ `cv2.namedWindow()` return ก่อนที่ Qt จะ init window จริง

**v3 แก้ให้แล้ว 3 ชั้น:**
1. `__init__.py` → force `QT_QPA_PLATFORM=xcb` ก่อน import cv2
2. `core.py` → เพิ่ม `cv2.waitKey(1)` หลัง `namedWindow()` ให้ Qt process event loop 1 รอบ
3. `interactions.py` → `MouseTracker.attach()` ครอบ `try/except` + retry ทุก frame จนสำเร็จ

### Q: วิดีโอบันทึกไม่ได้ (Linux)

ติดตั้ง ffmpeg:

```bash
sudo apt install ffmpeg
```

### Q: บันทึก screenshot ไปไหน?

Default อยู่ที่ working directory ปัจจุบัน เปลี่ยนได้:

```python
PlotConfig(screenshot_dir="/home/user/captures")
```

### Q: ต้องการ cv2.imshow อยู่ใน main thread

OpenCV GUI **ต้อง**อยู่ใน main thread เสมอ (ทั้ง Windows และ Linux) `update()` เรียกจาก thread ไหนก็ได้ แต่ `step()` / `cv2.imshow()` ต้อง main thread:

```python
# ✓ ถูก
threading.Thread(target=lambda: plot.update("data", value)).start()   # data push จาก thread อื่น
plot.step_all({})                                                      # display ใน main thread

# ✗ ผิด
threading.Thread(target=lambda: plot.step("data", value)).start()     # imshow ใน non-main thread
```

---

# ส่วนที่ 2 — อธิบายโค้ดแต่ละ Module

---

## 13. ภาพรวมสถาปัตยกรรม

### Dependency Graph

```
__init__.py (early Wayland fix — BEFORE cv2 import)
  │
  ▼
core.py (LivePlot)
  ├── config.py        (PlotConfig, SeriesConfig, AutoScaleMode)
  ├── colors.py        (Theme, get_theme, register_theme)
  ├── series.py        (Series — circular buffer)
  ├── renderer.py      (Renderer — drawing pipeline)
  │     ├── config.py
  │     ├── colors.py
  │     └── series.py
  ├── frame_timer.py   (FrameTimer — frame pacing)
  │     └── platform_utils.py
  ├── interactions.py   (MouseTracker, VideoRecorder, KeyAction)
  │     └── platform_utils.py
  └── platform_utils.py (PlatformInfo, timer boost, HiDPI, key normalize, Wayland fix)
```

### Data Flow Diagram

```
user code
    │
    ▼
  step("sensor", 42.0) ─── หรือ ─── update("sensor", 42.0)
    │                                       │
    ├── acquire Lock ──────────────────────┐│
    │                                      ││
    ▼                                      ▼│
  Series.push(42.0)                        ││
  ├── sanitize (None/NaN/inf → NaN)        ││
  ├── buffer[head] = 42.0                  ││
  └── head = (head+1) % size              ││
    │                                      ││
    ▼                                      ▼│
  Renderer.render()                        ││
  ├── auto_scale? → compute min/max        ││
  ├── smooth? → lerp y-axis               ││
  ├── bg_dirty? → rebuild_background()     ││
  ├── np.copyto(canvas, bg_cache)          ││
  ├── draw_series() × N                   ││
  ├── draw_legend()                        ││
  ├── draw_current_values()                ││
  ├── draw_tooltip()                       ││
  └── draw_status_bar()                    ││
    │                                      ││
    ├── release Lock ──────────────────────┘│
    │                                       │
    ▼                                       ▼
  return np.ndarray ◄──────────────────────┘
    │
    │ (step only ↓)
    ▼
  _ensure_window()                    ← ทำครั้งเดียว
  ├── cv2.namedWindow()
  ├── cv2.waitKey(1)                  ← ให้ Qt init window handle
  └── mouse.attach() → retry if fail  ← Wayland safety
    │
    ▼
  cv2.imshow(window_name, canvas)
    │
    ▼
  FrameTimer.tick()
  ├── compute remaining time
  ├── cv2.waitKey(adaptive_delay)
  ├── update overshoot EMA
  ├── update FPS
  └── return normalized key code
    │
    ▼
  process_key(key) → KeyAction
  ├── quit? → close() → return True
  ├── pause? → toggle _paused
  ├── screenshot? → save_screenshot()
  ├── recording? → VideoRecorder.start/stop()
  ├── theme? → cycle to next theme
  └── fps_delta? → adjust target_fps
    │
    ▼
  return False (continue) หรือ True (quit)
```

---

## 14. platform_utils.py

**หน้าที่:** แก้ปัญหาความแตกต่างระหว่าง Windows กับ Linux ทั้ง 4 เรื่อง

### 14.1 PlatformInfo — ตรวจ OS

```python
class PlatformInfo:
    OS = platform.system()         # 'Windows' | 'Linux' | 'Darwin'
    IS_WINDOWS = (OS == 'Windows')
    IS_LINUX = (OS == 'Linux')
    ARCH = platform.machine()      # 'x86_64', 'AMD64', 'aarch64'
```

คำนวณครั้งเดียวตอน import module (class-level attributes) ไม่เสียเวลาตรวจซ้ำทุก frame

### 14.2 _TimerResolution — แก้ปัญหา Windows 15.6ms Timer

**ปัญหา:** Windows default timer interrupt = 64 Hz (15.625ms) ทำให้ `cv2.waitKey(1)` จริงๆ รอ ~15ms

**วิธีแก้:** เรียก Windows kernel API ผ่าน `ntdll.dll` เพื่อขอ timer resolution 1ms:

```python
ntdll.NtSetTimerResolution(
    ctypes.c_ulong(10000),    # 10000 × 100ns = 1ms
    ctypes.c_long(1),         # True = set
    ctypes.byref(current)     # output: ค่า resolution จริงที่ได้
)
```

**ทำไมใช้ `NtSetTimerResolution` แทน `timeBeginPeriod`:**
- สามารถขอ resolution ต่ำกว่า 1ms ได้ (เช่น 0.5ms = 5000)
- ได้รับ feedback ว่า resolution จริงที่ OS ให้คือเท่าไร
- เป็น underlying API ที่ `timeBeginPeriod(1)` เรียกอยู่แล้ว

**ผลกระทบต่อ battery:** ~1-3% บน laptop, มี `restore()` เพื่อคืนค่าเดิมเมื่อจบโปรแกรม

**บน Linux:** function นี้ return `False` ทันที (ไม่ต้องทำอะไร เพราะ kernel HZ=1000 อยู่แล้ว)

### 14.3 enable_hidpi_awareness — แก้ภาพเบลอบน Windows

**ปัญหา:** Windows 10/11 อาจ auto-scale หน้าต่าง OpenCV ทำให้ text จาก `cv2.putText` เบลอ

**วิธีแก้:** ประกาศ DPI awareness ก่อนสร้าง window:

```python
ctypes.windll.shcore.SetProcessDpiAwareness(2)   # Per-Monitor V2
```

**ต้องเรียกก่อน** `cv2.imshow()` ครั้งแรก — ซึ่ง `LivePlot.__init__` จัดการให้แล้วผ่าน `apply_platform_fixes()`

### 14.4 normalize_key — แก้ Key Code ต่างกันระหว่าง OS

**ปัญหา:**
- Windows: `waitKey` return `113` สำหรับ 'q' (clean 8-bit)
- Linux (GTK): `waitKey` อาจ return `0x100071` สำหรับ 'q' (NumLock flag bit 20 ติดมา)

**วิธีแก้:**

```python
def normalize_key(raw_key: int) -> int:
    if raw_key < 0:
        return -1
    return raw_key & 0xFF    # mask เอาแค่ 8 bit ล่าง
```

`0x100071 & 0xFF = 0x71 = 113 = ord('q')` → ทำงานเหมือนกันทั้งสอง OS

### 14.5 Qt/Wayland Fix — แก้ปัญหา Linux Wayland Session

**ปัญหา:** OpenCV ที่ build ด้วย Qt backend อาจไม่มี Wayland plugin → เกิด warning:
```
qt.qpa.plugin: Could not find the Qt platform plugin "wayland"
```
แย่กว่านั้น — บาง setup Qt จะ init window ช้าเพราะ Wayland fallback ทำให้ `namedWindow()` return ก่อน window handle พร้อม → `setMouseCallback()` crash: `NULL window handler`

**วิธีแก้ (2 ชั้น):**

**ชั้นที่ 1 — Early environment fix ใน `__init__.py`:**

```python
# __init__.py (บรรทัดบนสุด ก่อน import cv2)
import os, platform
if (platform.system() == 'Linux'
        and os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland'
        and 'QT_QPA_PLATFORM' not in os.environ):
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
```

ต้องตั้ง **ก่อน** `import cv2` เพราะ cv2 อ่าน `QT_QPA_PLATFORM` ตอน import แล้ว init Qt backend ทันที ถ้าตั้งทีหลังจะไม่มีผล

`xcb` = X11 protocol ซึ่งทำงานผ่าน XWayland (compatibility layer ที่มีเกือบทุก Wayland compositor)

**ชั้นที่ 2 — Runtime check ใน `apply_platform_fixes()`:**

```python
if PlatformInfo.IS_LINUX:
    session = os.environ.get('XDG_SESSION_TYPE', '').lower()
    if session == 'wayland' and 'QT_QPA_PLATFORM' not in os.environ:
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
```

เป็น safety net สำหรับกรณีที่ user import module ย่อยตรงโดยไม่ผ่าน `__init__.py`

### 14.6 apply_platform_fixes — เรียกครั้งเดียว

`LivePlot.__init__` เรียก `apply_platform_fixes()` ซึ่งรันทุก fix ข้างต้นพร้อมกัน แล้วคืน dict บอกผลลัพธ์:

```python
# Windows:
{'os': 'Windows', 'timer_boosted': True, 'hidpi_set': True, 'qt_backend_fixed': False}

# Linux Wayland:
{'os': 'Linux', 'timer_boosted': False, 'hidpi_set': False, 'qt_backend_fixed': True}
```

---

## 15. frame_timer.py

**หน้าที่:** ควบคุม frame rate ให้คงที่ข้าม OS — แก้ปัญหา "ขยับเมาส์แล้วกราฟเร่ง"

### 15.1 สาเหตุของปัญหา (ทบทวน)

```
ไม่ขยับเมาส์: render(1ms) → waitKey(1) รอ 15ms ← OS timer tick → ~60 FPS
ขยับเมาส์:    render(1ms) → waitKey(1) มี mouse event → return ทันที → ~500 FPS
```

### 15.2 TimingStrategy — 3 โหมด

```python
class TimingStrategy(Enum):
    ADAPTIVE  = auto()    # คำนวณ delay อัตโนมัติ (default, แนะนำ)
    HYBRID    = auto()    # sleep + busy-wait (แม่นยำที่สุด)
    UNLIMITED = auto()    # ไม่จำกัด FPS (benchmark)
```

### 15.3 ADAPTIVE — วิธีทำงาน

```python
def _tick_adaptive(self, remaining: float) -> int:
    # 1. คำนวณ delay ที่ต้อง wait
    adjusted_ms = max(1, int((remaining - overshoot_avg) * 1000))
    #                                     ↑ หักค่า overshoot ออก

    # 2. วัดเวลาจริงที่ waitKey ใช้
    t_before = time.perf_counter()
    raw_key = cv2.waitKey(adjusted_ms)
    t_after = time.perf_counter()

    # 3. อัปเดต overshoot ด้วย EMA
    actual_wait = t_after - t_before
    overshoot = actual_wait - (adjusted_ms / 1000.0)
    overshoot_avg = α × overshoot + (1-α) × overshoot_avg
```

**EMA (Exponential Moving Average)** ติดตามว่า `waitKey` overshoot กี่ ms โดยเฉลี่ย แล้ว**หักออกจาก delay ครั้งถัดไป** ทำให้ frame rate คงที่แม้ OS timer ไม่แม่นยำ

ตัวอย่าง: target 60 FPS (16.67ms/frame), render ใช้ 2ms, overshoot_avg = 1.5ms

```
remaining = 16.67 - 2.0 = 14.67ms
adjusted  = 14.67 - 1.5 = 13.17ms → waitKey(13)
จริงรอ ≈ 14.5ms → total ≈ 16.5ms → ~60.6 FPS ✓
```

### 15.4 HYBRID — ความแม่นยำสูงสุด

```python
def _tick_hybrid(self, remaining: float) -> int:
    target_time = last_tick + frame_duration

    if remaining > 3ms:
        cv2.waitKey(remaining - 2ms)     # sleep หยาบๆ
    else:
        cv2.waitKey(1)                    # process GUI events

    while perf_counter() < target_time:  # busy-wait ช่วงสุดท้าย
        pass
```

ให้ความแม่นยำ ±0.1ms แต่**ใช้ CPU ~1-2% บน 1 core** จาก spin loop

**2ms safety margin** สำหรับ: OS scheduling jitter (~0.5ms) + waitKey overhead (~0.1ms) + context switch (~0.5ms)

### 15.5 FPS Measurement

```python
self._frame_times: deque[float] = deque(maxlen=120)
```

ใช้ `deque` ขนาดจำกัด 120 ตัว (ประมาณ 2 วินาทีที่ 60 FPS) คำนวณ FPS จาก sliding window:

```
FPS = (จำนวน timestamps - 1) / (timestamp ล่าสุด - timestamp เก่าสุด)
```

ใช้ `deque` แทน `list` เพราะ `deque.append` + auto-eviction เป็น O(1) ไม่ต้อง filter เอง

---

## 16. colors.py

**หน้าที่:** จัดการ color palette ในรูปแบบ **Theme** dataclass

### 16.1 Theme Structure

```python
@dataclass
class Theme:
    name: str
    bg: tuple[int, int, int]             # พื้นหลัง
    grid_major: tuple[int, int, int]     # เส้น grid หลัก
    grid_minor: tuple[int, int, int]     # เส้น grid รอง
    grid_center: tuple[int, int, int]    # เส้น y=0
    border: tuple[int, int, int]         # กรอบ plot area
    axis_label: tuple[int, int, int]     # ตัวเลข Y-axis
    title: tuple[int, int, int]          # ข้อความ title
    value_text: tuple[int, int, int]     # ค่าปัจจุบัน
    fps_text: tuple[int, int, int]       # FPS counter
    legend_bg: tuple[int, int, int]      # พื้น legend box
    legend_alpha: float = 0.7            # ความโปร่งใส legend
    series_colors: tuple = ()            # palette 8 สีสำหรับเส้นข้อมูล
```

ทุกสีเป็น **BGR tuple** (OpenCV convention) ไม่ใช่ RGB

### 16.2 Built-in Themes

| Theme | bg | เหมาะกับ |
|---|---|---|
| `DARK_THEME` | near-black (18,18,24) | monitoring ยาวๆ ตาไม่ล้า |
| `LIGHT_THEME` | near-white (245,245,248) | screenshot, presentation, printing |
| `MIDNIGHT_THEME` | deep blue-black (12,8,4) | aesthetic, warm tone |

### 16.3 Registry Pattern

`THEMES` dict เก็บ theme ทั้งหมด, `register_theme()` เพิ่ม theme ใหม่, `get_theme()` ดึงมาใช้ ทำให้ `core.py` สลับ theme ด้วยชื่อ string ได้โดยไม่ต้องส่ง object ตรงๆ

---

## 17. config.py

**หน้าที่:** กำหนดโครงสร้างข้อมูลสำหรับ configuration ทั้งหมด

### 17.1 AutoScaleMode (Enum)

```python
FIXED       # y_min/y_max ตามที่ตั้ง
AUTO        # ปรับทุก frame ให้พอดีกับ data
AUTO_EXPAND # ขยายได้อย่างเดียว ไม่หด
```

### 17.2 SeriesConfig (Dataclass)

Configuration ต่อ 1 เส้นข้อมูล ใช้ `@dataclass` เพื่อ auto-generate `__init__`, `__repr__`, `__eq__`

### 17.3 PlotConfig (Dataclass + Properties)

Configuration หลักของ plot มี **computed properties** 4 ตัวที่คำนวณ plot area จาก margins:

```python
@property
def plot_w(self) -> int:
    return self.width - self.margin_left - self.margin_right
```

**ฟีเจอร์ใหม่ใน v3:**
- `smooth_auto_scale` + `auto_scale_speed` → lerp animation สำหรับ Y-axis
- `theme` → ชื่อ theme string
- `enable_mouse_tooltip`, `enable_keyboard` → toggle interactions
- `screenshot_dir` → ที่บันทึกไฟล์
- `target_fps` → FrameTimer target
- `show_shortcuts_hint` → แสดง shortcut ด้านล่าง

---

## 18. series.py

**หน้าที่:** เก็บข้อมูล time series ใน circular buffer ที่ push เป็น O(1)

### 18.1 Circular Buffer Mechanism

```
capacity=8, head=5:

  index:  0   1   2   3   4   5   6   7
  data: [ 50  60  70  10  20  30  40  __ ]
                              ↑ head (จะเขียนที่นี่ต่อไป)

  logical order: 30 40 50 60 70 10 20
                 ↑ oldest         ↑ newest (head-1)
```

**push(value):**
1. `buffer[head] = value` → O(1)
2. `head = (head+1) % size` → wrap around
3. ข้อมูลเก่าถูกเขียนทับอัตโนมัติ

**get_data():**
- Buffer ยังไม่เต็ม → `buffer[:count].copy()` (ข้อมูลเรียงอยู่แล้ว)
- Buffer เต็มแล้ว → `np.roll(buffer, -head)` unwrap ให้เรียงเก่า→ใหม่

### 18.2 Input Sanitization

```python
def push(self, value):
    if value is None:             clean = NaN
    elif isinstance(float) and isnan/isinf:  clean = NaN
    else:
        clean = float(value)      # try convert int, np.int64, etc.
        if isnan/isinf(clean):    clean = NaN   # catch numpy inf
```

ครอบคลุมทุก edge case: `None`, `float('nan')`, `float('inf')`, `np.nan`, `np.inf`, string (→ NaN)

### 18.3 `__slots__` Optimization

```python
__slots__ = ('config', '_buffer', '_size', '_head', '_count',
             '_running_sum', '_running_sq_sum')
```

- Python ปกติเก็บ attributes ใน `__dict__` (hash table, ~200 bytes per instance)
- `__slots__` บอก Python จอง fixed-size struct (~64 bytes)
- **ผลลัพธ์:** RAM ลด ~40%, attribute access เร็วขึ้น ~15%

### 18.4 Running Statistics

```python
self._running_sum += clean          # sum ของข้อมูลที่ valid
self._running_sq_sum += clean²      # sum of squares
```

เมื่อ buffer เต็มและเขียนทับ → ลบค่าเก่าออกจาก running sum ก่อน เพื่อให้คำนวณ mean/std เป็น O(1) ได้ในอนาคต

### 18.5 get_min_max()

```python
def get_min_max(self) -> tuple[float, float]:
    data = self._buffer[:count] if count < size else self._buffer
    valid = data[~np.isnan(data)]
    return (valid.min(), valid.max())
```

ใช้โดย `Renderer._compute_auto_scale()` เพื่อหา y-limits จากข้อมูลใน buffer — ไม่เรียก `get_data()` ที่ต้อง copy + roll เพราะ min/max ไม่ต้องการลำดับ

---

## 19. renderer.py

**หน้าที่:** วาดทุกอย่างบน canvas — เป็น module ที่ใหญ่ที่สุดและทำงานหนักที่สุด

### 19.1 Double Buffering (Background Cache)

```
_bg_cache (วาดครั้งเดียว)        _canvas (วาดทุก frame)
┌──────────────────────┐         ┌──────────────────────┐
│ background color     │         │ background color     │
│ grid lines           │ ──copy──│ grid lines           │
│ Y-axis labels        │         │ Y-axis labels        │
│ border               │         │ + series lines       │
│ title                │         │ + legend             │
│ zero line            │         │ + tooltip            │
└──────────────────────┘         │ + status bar         │
                                 └──────────────────────┘
```

- `np.copyto(canvas, bg_cache)` ≈ **0.1-0.3ms** (SIMD-accelerated memcpy)
- `_rebuild_background()` ≈ **1-3ms** (วาด grid + labels) — เรียกเฉพาะเมื่อ `_bg_dirty = True`
- `_bg_dirty` ถูก set เมื่อ: y-limits เปลี่ยน, theme เปลี่ยน, series เพิ่ม/ลบ

### 19.2 Render Pipeline (9 ขั้นตอน)

เรียงตามลำดับใน `render()`:

| Step | Method | เมื่อไร | ทำอะไร |
|---|---|---|---|
| 1 | `_compute_auto_scale` | AUTO/AUTO_EXPAND | scan min/max จากทุก series |
| 2 | `_lerp_y_axis` | smooth_auto_scale=True | lerp display limits เข้าหา target |
| 3 | `_rebuild_background` | bg_dirty=True | วาด grid, labels, border, title |
| 4 | `np.copyto` | ทุก frame | copy bg_cache → canvas |
| 5 | `_draw_series` | ทุก frame × N series | วาดเส้นข้อมูล + glow dot |
| 6 | `_draw_legend` | >1 series | กล่อง legend semi-transparent |
| 7 | `_draw_current_values` | show_value=True | ค่าปัจจุบันด้านบนขวา |
| 8 | `_draw_tooltip` | mouse อยู่ใน plot area | crosshair + ค่าที่เมาส์ชี้ |
| 9 | `_draw_status_bar` | ทุก frame | FPS, shortcuts hint, status messages |

### 19.3 _draw_series — Vectorized Coordinate Mapping

```python
# 1. กระจาย N จุดเต็มความกว้าง plot
x_coords = np.linspace(px, px + pw, n)          # vectorized

# 2. Normalize ค่า y ไปช่วง [0, 1]
y_norm = np.clip((data - y_min) / y_range, 0, 1) # vectorized

# 3. แปลงเป็น pixel coordinates
y_coords = py + (1.0 - y_norm) * ph              # vectorized (invert_y)
```

ทั้ง 3 ขั้นตอนเป็น **NumPy vectorized operations** — ไม่มี Python loop, คำนวณใน C level ทีเดียวทุกจุด

### 19.4 NaN Gap Segmentation

เมื่อข้อมูลมี NaN (จาก sanitize) ต้องแบ่ง polyline เป็น segment:

```
data:     [10, 20, NaN, NaN, 50, 60]
segments: [[10,20], [50,60]]    ← เส้นขาดตรง NaN
```

แต่ละ segment วาดด้วย `cv2.polylines()` ครั้งเดียว (ไม่ใช่ loop `cv2.line()`) เพราะ cross Python→C boundary ครั้งเดียวเร็วกว่า N ครั้ง

### 19.5 Glow Dot — เอฟเฟกต์จุดเรืองแสง

วาด 3 วงซ้อน:

```
1. glow   (radius + 6, สี ÷ 3)  — วงใหญ่ สีจาง = halo
2. dot    (radius,     สีเต็ม)  — วงหลัก
3. center (2px,        ขาว)     — จุดกลาง = ไฮไลท์
```

### 19.6 Semi-Transparent Legend (v3 improvement)

v2 ใช้ `canvas.copy()` ทั้งภาพ + `addWeighted` → copy 2 MB ต่อ frame

v3 ใช้ **ROI slicing** — copy แค่พื้นที่ legend box:

```python
overlay = canvas[y:y+h, x:x+w].copy()        # copy แค่กล่อง (~200 bytes)
bg_rect = np.full_like(overlay, legend_bg)
blended = cv2.addWeighted(bg_rect, 0.7, overlay, 0.3, 0)
canvas[y:y+h, x:x+w] = blended               # paste กลับ
```

เร็วกว่า v2 ประมาณ **10-50x** สำหรับ legend (copy ~200 bytes แทน ~2 MB)

### 19.7 Smooth Y-axis (Lerp)

```python
def _lerp_y_axis(self):
    a = auto_scale_speed    # 0.15 default
    display_y_min += (target_y_min - display_y_min) × a
    display_y_max += (target_y_max - display_y_max) × a
```

**Linear Interpolation** — แต่ละ frame เลื่อน display limits เข้าหา target 15% ของระยะที่เหลือ ผลลัพธ์คือ **exponential ease-out** ที่ดูนุ่มนวล

Threshold สำหรับ rebuild background:

```python
threshold = (display_y_max - display_y_min) / plot_h × 0.1
```

ถ้าการเปลี่ยนแปลง < 0.1 pixel → ไม่ rebuild (ประหยัด CPU)

### 19.8 Mouse Tooltip

```python
def _draw_tooltip(self, ..., mouse_pos, px, py, pw, ph):
    mx, my = mouse_pos

    # ตรวจว่าเมาส์อยู่ใน plot area
    if not (px <= mx <= px+pw and py <= my <= py+ph):
        return

    # วาดเส้น crosshair แนวตั้ง
    cv2.line(canvas, (mx, py), (mx, py+ph), ...)

    # สำหรับแต่ละ series: map mouse X → data index → อ่านค่า
    frac = (mx - px) / pw           # 0.0 ← ซ้ายสุด, 1.0 → ขวาสุด
    idx = int(frac × (n - 1))       # แปลงเป็น index ใน buffer
    val = data[idx]                  # อ่านค่าที่ตำแหน่งนั้น

    # วาดจุด + text ที่ตำแหน่ง
    cv2.circle(canvas, (mx, y_pixel), 4, series_color, ...)
    cv2.putText(canvas, f"Label: {val}", (mx+10, ty), ...)
```

---

## 20. interactions.py

**หน้าที่:** จัดการ input ทั้งหมด — mouse, keyboard, screenshot, video

### 20.1 MouseTracker

```python
class MouseTracker:
    def attach(self, window_name) -> bool:
        self._attached_window = window_name
        try:
            cv2.setMouseCallback(window_name, self._callback)
            return True
        except cv2.error:
            # Window not ready (Qt/Wayland race condition)
            return False     # caller จะ retry frame ถัดไป

    def _callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self._pos = (x, y)
            self._inside = True
        elif event == cv2.EVENT_MOUSELEAVE:
            self._inside = False

    @property
    def position(self) -> Optional[tuple[int, int]]:
        return self._pos if self._inside else None
```

ใช้ OpenCV mouse callback ซึ่งทำงานบน **HighGUI thread เดียวกับ `cv2.imshow()`** จึงไม่มี cross-thread issue ถ้าอ่าน `position` จาก thread เดียวกัน

**ทำไมต้อง `try/except`?** — บน Linux Qt backend (โดยเฉพาะ Wayland session) `cv2.namedWindow()` อาจ return ก่อนที่ window handle จะพร้อมจริง ถ้าเรียก `setMouseCallback()` ตอนนั้นจะได้ `cv2.error: NULL window handler` แทนที่จะ crash ทั้งโปรแกรม เราดัก error แล้ว return `False` ให้ `core.py` retry ใน frame ถัดไป

### 20.2 VideoRecorder

```python
class VideoRecorder:
    def start(self) -> str:
        # ลอง codec ตามลำดับ: mp4v → avc1 → XVID
        for codec in ['mp4v', 'avc1', 'XVID']:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(filepath, fourcc, fps, (w, h))
            if writer.isOpened():
                return filepath
```

**Cross-platform codec selection:**
- `mp4v` (MPEG-4 Part 2) — ใช้ได้ทั้ง Windows/Linux ไม่ต้องติดตั้งอะไรเพิ่ม
- `avc1` (H.264) — คุณภาพดีกว่า แต่อาจไม่มีบน Linux ถ้าไม่ติด ffmpeg
- `XVID` — fallback เก่าแก่ ใช้ได้เกือบทุกที่

### 20.3 KeyAction — Keyboard Dispatch

```python
@dataclass
class KeyAction:
    quit: bool = False
    toggle_pause: bool = False
    screenshot: bool = False
    reset: bool = False
    toggle_recording: bool = False
    cycle_theme: bool = False
    fps_delta: int = 0
    status_message: str = ""

def process_key(key: int) -> KeyAction:
    if key == ord('q') or key == 27:    return KeyAction(quit=True)
    elif key == ord('p') or key == 32:  return KeyAction(toggle_pause=True)
    ...
```

**ออกแบบเป็น dataclass แทน if-else chain ใน core.py** เพราะ:
- testable — ทดสอบ `process_key(ord('q')).quit == True` ได้โดยไม่ต้องสร้าง LivePlot
- extensible — เพิ่ม action ใหม่ได้โดยเพิ่ม field ใน KeyAction
- separation of concerns — core.py ไม่ต้องรู้ว่าปุ่มไหน map กับ action ไหน

---

## 21. core.py

**หน้าที่:** ประสานทุก module เข้าด้วยกัน เป็น public interface หลัก

### 21.1 Constructor — สิ่งที่เกิดขึ้นตอนสร้าง LivePlot

```python
def __init__(self, config, *, window_name):
    # 1. เก็บ config
    self._config = config or PlotConfig()

    # 2. แก้ปัญหา OS (timer boost + HiDPI + Wayland) ← ทำครั้งเดียว
    self._platform_info = apply_platform_fixes()

    # 3. สร้าง sub-systems
    self._renderer = Renderer(config)           # drawing
    self._timer = FrameTimer(target_fps=60)     # frame pacing
    self._mouse = MouseTracker()                 # mouse input
    self._recorder = VideoRecorder(w, h)         # video recording

    # 4. Internal state
    self._paused = False
    self._window_created = False
    self._mouse_attached = False     # retry flag สำหรับ Qt/Wayland
    self._lock = threading.Lock()                # thread safety
```

### 21.2 update() — Overloaded Signatures

```python
def update(self, name_or_value, value=None, color=None):
    if value is None:
        # → single value mode: plot.update(42.0)
        actual_value = name_or_value
        series_name = "_default"      # auto-create ถ้ายังไม่มี
    else:
        # → named mode: plot.update("temp", 42.0)
        actual_value = value
        series_name = name_or_value
```

ใช้ pattern **"optional second argument"** เพื่อ support 2 call signatures โดยไม่ต้อง overload (Python ไม่มี function overloading)

### 21.3 step() → _display_and_handle() → _ensure_window()

```python
def step(self, name_or_value, value=None, color=None) -> bool:
    img = self.update(name_or_value, value, color)   # 1. push data + render
    return self._display_and_handle(img)              # 2. display + input

def _display_and_handle(self, img):
    self._ensure_window()                    # สร้าง window ครั้งแรก
    cv2.imshow(self._window_name, img)       # แสดงภาพ
    if self._recorder.is_recording:
        self._recorder.write_frame(img)      # บันทึก video (ถ้ากำลังอัด)
    key = self._timer.tick()                 # frame pacing + keyboard
    if key < 0: return False
    return self._handle_key(key)             # process shortcuts
```

**`_ensure_window()` — Lazy Init + Wayland Retry:**

```python
def _ensure_window(self):
    if not self._window_created:
        cv2.namedWindow(self._window_name, WINDOW_AUTOSIZE)
        cv2.waitKey(1)                    # ← ให้ Qt process event loop 1 รอบ
        self._mouse_attached = False
        self._window_created = True

    # Retry mouse attach ทุก frame จนสำเร็จ
    if not self._mouse_attached and self._config.enable_mouse_tooltip:
        self._mouse_attached = self._mouse.attach(self._window_name)
```

**ทำไมต้อง `waitKey(1)` ตรงนี้?**

บน Linux Qt backend (โดยเฉพาะ Wayland) ลำดับเหตุการณ์คือ:

```
cv2.namedWindow()
    → Qt สร้าง QWindow object           ← return ทันที
    → Qt ยังไม่สร้าง native window handle  ← ต้องรอ event loop

cv2.setMouseCallback()
    → ถ้า handle = NULL → crash!          ← เกิดตรงนี้

cv2.waitKey(1)
    → บังคับ Qt process pending events
    → native window handle ถูกสร้าง         ← แก้ปัญหา
```

**ทำไมต้อง retry pattern?**

แม้จะมี `waitKey(1)` แล้ว บาง environment (Docker, WSL, remote X11) อาจต้องใช้ >1 event loop iteration ดังนั้น `_mouse_attached` flag จะ retry `attach()` ทุก frame จนสำเร็จ ถ้า attach fail → tooltip แค่ไม่ทำงานชั่วคราว โปรแกรมไม่ crash

### 21.4 _handle_key() — จัดการ Keyboard Shortcuts

```python
def _handle_key(self, key):
    action = process_key(key)    # map key → KeyAction

    if action.quit:          self.close(); return True
    if action.toggle_pause:  self._paused = not self._paused
    if action.screenshot:    save_screenshot(canvas, dir)
    if action.toggle_recording: recorder.start() or recorder.stop()
    if action.cycle_theme:   renderer.theme = next_theme
    if action.fps_delta:     timer.target_fps += delta

    return False
```

### 21.5 Theme Cycling

```python
self._theme_cycle = list(THEMES.keys())   # ['dark', 'light', 'midnight']
self._theme_index = 0

# เมื่อกด T:
self._theme_index = (self._theme_index + 1) % len(self._theme_cycle)
theme_name = self._theme_cycle[self._theme_index]
self._renderer.theme = get_theme(theme_name)
```

ถ้า `register_theme()` เพิ่ม custom theme เข้า `THEMES` dict ก่อนสร้าง LivePlot → theme ใหม่จะอยู่ใน cycle ด้วย

### 21.6 Status Messages (Temporary)

```python
def _set_status(self, text, duration=2.0):
    self._status_text = text
    self._status_clear_time = perf_counter() + duration

# ใน _do_render():
if status_text and perf_counter() > status_clear_time:
    self._status_text = ""    # auto-clear เมื่อหมดเวลา
```

ข้อความ status (เช่น "Saved: screenshot.png") แสดงที่ status bar แล้วหายไปเองหลัง N วินาที

### 21.7 Thread Safety

ทุก public method (`update`, `update_all`, `add_series`, `remove_series`, `clear`) ใช้ `with self._lock:`

**แต่** `step()` และ `step_all()` ที่เรียก `cv2.imshow()` ต้องอยู่ใน **main thread เท่านั้น** เพราะ OpenCV HighGUI จำกัดการทำงานกับ GUI ไว้ที่ main thread (ทั้ง Windows และ Linux GTK/Qt)

### 21.8 close() — Cleanup

```python
def close(self):
    if self._recorder.is_recording:
        self._recorder.stop()          # ปิด video file
    self._timer.stop()                 # cv2.destroyAllWindows()
    cleanup_platform()                 # restore Windows timer resolution
```

---

> **LivePlot v3.0.1** — Cross-platform. Production-grade. Wayland-safe. Built for real-time.
