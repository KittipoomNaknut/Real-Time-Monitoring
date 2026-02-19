"""
Platform Utilities — OS-specific optimizations for consistent behavior.

Cross-Platform Issues Addressed:
=================================

┌─────────────────────┬──────────────────────────┬─────────────────────────┐
│ Issue               │ Windows                  │ Linux                   │
├─────────────────────┼──────────────────────────┼─────────────────────────┤
│ waitKey(1) actual   │ ~15.6ms (timer tick)     │ ~1-2ms (HZ=1000)       │
│ time.sleep(0.001)   │ ~15ms                    │ ~1.5ms                  │
│ Key codes           │ 8-bit clean              │ modifier flag bits      │
│ HiDPI               │ auto-scale → blurry      │ usually no scaling      │
│ perf_counter resolution │ ~100ns (QPC)         │ ~1ns (clock_gettime)    │
└─────────────────────┴──────────────────────────┴─────────────────────────┘

Timer Resolution Deep Dive (Windows):
======================================
Windows uses a global timer interrupt at 64 Hz by default (15.625ms period).
ALL timing functions are quantized to this tick:
  - time.sleep(0.001) → actually 15.6ms
  - threading.Event.wait(0.001) → actually 15.6ms
  - WaitForSingleObject(handle, 1) → actually 15.6ms
  - cv2.waitKey(1) → actually 15.6ms (uses MsgWaitForMultipleObjects)

We fix this by calling NtSetTimerResolution(10000) via ntdll.dll, which
requests a 1ms timer interrupt. This is the same mechanism used by:
  - timeBeginPeriod(1) in winmm.dll
  - Chrome/Firefox for requestAnimationFrame
  - Game engines for frame pacing

After boost: time.sleep(0.001) → ~1-2ms, waitKey(1) → ~1-2ms
"""

from __future__ import annotations

import ctypes
import platform
import warnings
from typing import Optional


class PlatformInfo:
    """Immutable platform detection — computed once at import time."""

    OS: str = platform.system()                  # 'Windows' | 'Linux' | 'Darwin'
    IS_WINDOWS: bool = (OS == 'Windows')
    IS_LINUX: bool = (OS == 'Linux')
    IS_MAC: bool = (OS == 'Darwin')

    ARCH: str = platform.machine()               # 'x86_64', 'aarch64', 'AMD64'
    PY_VERSION: tuple = tuple(map(int, platform.python_version_tuple()))

    @classmethod
    def summary(cls) -> str:
        return f"{cls.OS} {cls.ARCH} | Python {'.'.join(map(str, cls.PY_VERSION))}"


# ────────────────────────────────────────────────────────────
# Windows Timer Resolution
# ────────────────────────────────────────────────────────────
class _TimerResolution:
    """
    Manages Windows timer interrupt resolution via ntdll.dll.

    Technical mechanism:
      NtSetTimerResolution(DesiredResolution, SetResolution, CurrentResolution)
        - DesiredResolution: in 100ns units (10000 = 1.0ms)
        - SetResolution: True to set, False to release
        - CurrentResolution: output — actual resolution achieved

    This is superior to timeBeginPeriod(1) because:
      1. We can request sub-millisecond resolution (e.g., 5000 = 0.5ms)
      2. We get back the actual achieved resolution
      3. It's the underlying API that timeBeginPeriod calls anyway

    Power impact: ~1-3% battery on laptops. We provide restore() to undo.
    """

    _boosted: bool = False
    _ntdll: Optional[ctypes.WinDLL] = None  # type: ignore[assignment]
    _previous_resolution: int = 0

    @classmethod
    def boost(cls) -> bool:
        """
        Request 1ms timer resolution. Returns True if successful.
        Safe to call multiple times — idempotent.
        """
        if cls._boosted or not PlatformInfo.IS_WINDOWS:
            return cls._boosted

        try:
            ntdll = ctypes.WinDLL('ntdll.dll')
            current = ctypes.c_ulong()

            # Request 1ms (10000 × 100ns = 1,000,000ns = 1ms)
            status = ntdll.NtSetTimerResolution(
                ctypes.c_ulong(10000),   # desired: 1.0ms
                ctypes.c_long(1),        # set = True
                ctypes.byref(current)    # output: actual
            )

            if status == 0:  # STATUS_SUCCESS
                cls._ntdll = ntdll
                cls._previous_resolution = current.value
                cls._boosted = True
                actual_ms = current.value / 10000.0
                return True
            else:
                warnings.warn(
                    f"NtSetTimerResolution failed (status=0x{status:08X}). "
                    f"Frame timing may be inconsistent on Windows.",
                    RuntimeWarning, stacklevel=2
                )
                return False

        except (OSError, AttributeError) as e:
            warnings.warn(
                f"Cannot access ntdll.dll: {e}. "
                f"Frame timing may be inconsistent on Windows.",
                RuntimeWarning, stacklevel=2
            )
            return False

    @classmethod
    def restore(cls) -> None:
        """Restore original timer resolution. Call on shutdown."""
        if not cls._boosted or cls._ntdll is None:
            return
        try:
            current = ctypes.c_ulong()
            cls._ntdll.NtSetTimerResolution(
                ctypes.c_ulong(cls._previous_resolution),
                ctypes.c_long(0),  # set = False (release)
                ctypes.byref(current)
            )
        except Exception:
            pass
        finally:
            cls._boosted = False

    @classmethod
    @property
    def is_boosted(cls) -> bool:
        return cls._boosted


# ────────────────────────────────────────────────────────────
# HiDPI Awareness (Windows)
# ────────────────────────────────────────────────────────────
def enable_hidpi_awareness() -> bool:
    """
    [Windows Only] Declare DPI awareness to prevent blurry scaling.

    Without this, Windows 10/11 may auto-scale the OpenCV window,
    causing blurry text and misaligned pixels. By declaring
    Per-Monitor DPI awareness, we get:
      - Pixel-perfect rendering at native resolution
      - Correct mouse coordinates
      - Sharp text in cv2.putText

    Must be called BEFORE any cv2.imshow() or cv2.namedWindow().

    Returns True if successfully set.
    """
    if not PlatformInfo.IS_WINDOWS:
        return False

    try:
        # Windows 10 1703+ Per-Monitor V2 (best)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return True
    except (AttributeError, OSError):
        pass

    try:
        # Fallback: System DPI awareness
        ctypes.windll.user32.SetProcessDPIAware()
        return True
    except (AttributeError, OSError):
        return False


# ────────────────────────────────────────────────────────────
# Cross-Platform Key Code Normalization
# ────────────────────────────────────────────────────────────
def normalize_key(raw_key: int) -> int:
    """
    Normalize cv2.waitKey() return value across platforms.

    Problem:
      - Windows: waitKey returns clean 8-bit key code
      - Linux (GTK/Qt backend): waitKey may include modifier bits
        e.g., NumLock sets bit 20 (0x100000), so 'q' becomes 0x100071

    Solution: Mask to lowest 8 bits, which is the actual key code.

    Usage:
        key = normalize_key(cv2.waitKey(1))
        if key == ord('q'):
            break
    """
    if raw_key < 0:
        return -1
    return raw_key & 0xFF


# ────────────────────────────────────────────────────────────
# Convenience: apply all platform fixes at once
# ────────────────────────────────────────────────────────────
def apply_platform_fixes() -> dict:
    """
    Apply all platform-specific optimizations. Call once at startup.

    Returns dict with results:
        {
            'os': 'Windows',
            'timer_boosted': True,
            'hidpi_set': True,
        }
    """
    result = {
        'os': PlatformInfo.OS,
        'timer_boosted': False,
        'hidpi_set': False,
    }

    if PlatformInfo.IS_WINDOWS:
        result['timer_boosted'] = _TimerResolution.boost()
        result['hidpi_set'] = enable_hidpi_awareness()

    return result


def cleanup_platform() -> None:
    """Restore platform state. Call on exit."""
    _TimerResolution.restore()
