"""
FrameTimer — Cross-platform precise frame rate controller.

This module solves THE core cross-platform timing problem:
==========================================================

On Windows:
  cv2.waitKey(1) internally calls MsgWaitForMultipleObjects with timeout=1ms,
  BUT Windows default timer resolution is 15.625ms (64 Hz system tick).
  Result: waitKey(1) actually waits ~15-16ms → max ~60 FPS even if rendering
  takes <1ms. Moving the mouse sends WM_MOUSEMOVE events that wake the wait
  early, causing the "mouse makes graph faster" effect.

On Linux:
  Kernel HZ is typically 1000, so waitKey(1) actually waits ~1-2ms.
  Less problematic but still imprecise at high FPS targets.

Solution — Hybrid Timer Strategy:
===================================
1. Call platform_utils.boost_timer_resolution() on Windows (makes sleep ~1ms)
2. Use a computed waitKey delay based on how long rendering took
3. If precision matters more than CPU, add a busy-wait spin loop for
   the final sub-millisecond alignment

Three strategies:
  ADAPTIVE  — Compute waitKey delay to hit target FPS (recommended)
  HYBRID    — sleep for bulk + busy-wait for precision (most accurate)
  UNLIMITED — waitKey(1), no throttling (max FPS, useful for benchmarking)
"""

from __future__ import annotations

import time
from collections import deque
from enum import Enum, auto
from typing import Optional

import cv2

from .platform_utils import PlatformInfo, normalize_key


class TimingStrategy(Enum):
    """Frame timing strategy."""
    ADAPTIVE = auto()    # Compute waitKey delay dynamically
    HYBRID = auto()      # Sleep + busy-wait for precision
    UNLIMITED = auto()   # No throttling


class FrameTimer:
    """
    Manages frame pacing and input handling.

    Usage:
        timer = FrameTimer(target_fps=60)

        while True:
            # ... render frame ...
            cv2.imshow("Plot", img)

            key = timer.tick()           # pace frame + get key input
            if key == ord('q'):
                break

        timer.stop()

    The tick() method:
      1. Measures time since last tick
      2. Computes how long to wait to maintain target FPS
      3. Calls cv2.waitKey(computed_delay) for GUI event processing
      4. (HYBRID only) Busy-waits for final sub-ms alignment
      5. Returns normalized key code (-1 if no key)
    """

    def __init__(
        self,
        target_fps: int = 60,
        strategy: TimingStrategy = TimingStrategy.ADAPTIVE,
    ):
        self._target_fps = max(0, target_fps)
        self._strategy = strategy
        self._frame_duration = 1.0 / target_fps if target_fps > 0 else 0.0

        # Timing state
        self._last_tick = time.perf_counter()
        self._frame_times: deque[float] = deque(maxlen=120)
        self._fps = 0.0

        # Adaptive delay compensation
        # Tracks how much waitKey overshoots to auto-correct
        self._overshoot_avg = 0.0
        self._overshoot_alpha = 0.1  # EMA smoothing factor

    def tick(self) -> int:
        """
        Pace the frame and return key input.

        Returns:
            Normalized key code (8-bit), or -1 if no key pressed.
        """
        now = time.perf_counter()

        if self._target_fps <= 0 or self._strategy == TimingStrategy.UNLIMITED:
            # No throttling — just process GUI events
            raw_key = cv2.waitKey(1)
            self._record_frame(now)
            return normalize_key(raw_key)

        # Time spent rendering this frame
        elapsed = now - self._last_tick
        remaining = self._frame_duration - elapsed

        if self._strategy == TimingStrategy.ADAPTIVE:
            key = self._tick_adaptive(remaining)
        else:  # HYBRID
            key = self._tick_hybrid(remaining)

        self._record_frame(time.perf_counter())
        return key

    def _tick_adaptive(self, remaining: float) -> int:
        """
        Compute optimal waitKey delay accounting for OS overhead.

        The key insight: cv2.waitKey(n) on Windows overshoots by a
        predictable amount (~0-2ms with timer boost). We track this
        overshoot with an exponential moving average and subtract it
        from the requested delay.

        wait_ms = max(1, int((remaining - overshoot_avg) × 1000))
        """
        if remaining <= 0:
            raw_key = cv2.waitKey(1)
            self._last_tick = time.perf_counter()
            return normalize_key(raw_key)

        # Subtract measured overshoot to compensate OS jitter
        adjusted_ms = max(1, int((remaining - self._overshoot_avg) * 1000))

        t_before = time.perf_counter()
        raw_key = cv2.waitKey(adjusted_ms)
        t_after = time.perf_counter()

        # Update overshoot estimate (EMA)
        actual_wait = t_after - t_before
        requested_wait = adjusted_ms / 1000.0
        overshoot = actual_wait - requested_wait
        self._overshoot_avg = (
            self._overshoot_alpha * overshoot
            + (1 - self._overshoot_alpha) * self._overshoot_avg
        )

        self._last_tick = t_after
        return normalize_key(raw_key)

    def _tick_hybrid(self, remaining: float) -> int:
        """
        Sleep for bulk of the delay, then busy-wait for precision.

        Strategy:
          1. If remaining > 3ms: cv2.waitKey(remaining - 2ms)
          2. Busy-wait (spin loop) until exact target time
          3. This gives ±0.1ms accuracy at the cost of ~1-2% CPU on one core

        The 2ms safety margin accounts for:
          - OS scheduling jitter (~0.5-1ms)
          - waitKey overhead (~0.1ms)
          - Context switch latency (~0.1-0.5ms)
        """
        raw_key = -1
        target_time = self._last_tick + self._frame_duration

        if remaining > 0.003:
            # Sleep most of the time via waitKey (also processes GUI events)
            wait_ms = max(1, int((remaining - 0.002) * 1000))
            raw_key = cv2.waitKey(wait_ms)
        else:
            # Still need to call waitKey at least once for GUI events
            raw_key = cv2.waitKey(1)

        # Busy-wait for final alignment (sub-millisecond precision)
        while time.perf_counter() < target_time:
            pass  # spin

        self._last_tick = time.perf_counter()
        return normalize_key(raw_key)

    def _record_frame(self, now: float) -> None:
        """Update FPS measurement using sliding window."""
        self._frame_times.append(now)
        self._last_tick = now

        if len(self._frame_times) >= 2:
            oldest = self._frame_times[0]
            elapsed = now - oldest
            if elapsed > 0:
                self._fps = (len(self._frame_times) - 1) / elapsed

    @property
    def fps(self) -> float:
        """Current measured FPS (sliding window average)."""
        return self._fps

    @property
    def target_fps(self) -> int:
        return self._target_fps

    @target_fps.setter
    def target_fps(self, value: int) -> None:
        self._target_fps = max(0, value)
        self._frame_duration = 1.0 / value if value > 0 else 0.0

    def stop(self) -> None:
        """Cleanup. Call when done."""
        cv2.destroyAllWindows()