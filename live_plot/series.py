"""
Series — Circular buffer data container with O(1) push and built-in statistics.

Circular Buffer Mechanism:
==========================
Fixed-size numpy array with a write head that wraps around.
When buffer is full, oldest data is silently overwritten.

    Buffer: [ d  e  f  g  a  b  c ]
                              ↑ head=4
    Logical order: a b c d e f g
    get_data() uses np.roll(-head) to unwrap.

Performance vs list:
    list.append + list.pop(0)  →  O(n) per pop (shift all elements)
    circular buffer push       →  O(1) always (write at head, increment)
    For buffer_size=1000: circular is ~100x faster per push.

Memory:
    Uses __slots__ to eliminate per-instance __dict__ overhead.
    Each Series: buffer_size × 8 bytes (float64) + ~64 bytes overhead.
    1000-point series = ~8 KB.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from .config import SeriesConfig


class Series:
    """A single data series backed by a circular buffer."""

    __slots__ = ('config', '_buffer', '_size', '_head', '_count',
                 '_running_sum', '_running_sq_sum')

    def __init__(self, config: SeriesConfig, buffer_size: int):
        self.config = config
        self._size = buffer_size
        self._buffer = np.full(buffer_size, np.nan, dtype=np.float64)
        self._head = 0
        self._count = 0

        # Running statistics (for O(1) mean/std if needed)
        self._running_sum = 0.0
        self._running_sq_sum = 0.0

    def push(self, value: float) -> None:
        """Add a value. Handles None, NaN, inf gracefully."""
        if value is None:
            clean = np.nan
        elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            clean = np.nan
        else:
            try:
                clean = float(value)
                # Also catch numpy inf/nan for non-float inputs
                if math.isnan(clean) or math.isinf(clean):
                    clean = np.nan
            except (ValueError, TypeError):
                clean = np.nan

        # Update running stats: subtract old value if overwriting
        if self._count >= self._size:
            old = self._buffer[self._head]
            if not math.isnan(old):
                self._running_sum -= old
                self._running_sq_sum -= old * old

        if not math.isnan(clean):
            self._running_sum += clean
            self._running_sq_sum += clean * clean

        self._buffer[self._head] = clean
        self._head = (self._head + 1) % self._size
        self._count = min(self._count + 1, self._size)

    def get_data(self) -> np.ndarray:
        """Return data in chronological order (oldest → newest)."""
        if self._count < self._size:
            return self._buffer[:self._count].copy()
        return np.roll(self._buffer, -self._head).copy()

    @property
    def latest(self) -> float:
        """Most recently pushed value."""
        if self._count == 0:
            return np.nan
        idx = (self._head - 1) % self._size
        return self._buffer[idx]

    @property
    def count(self) -> int:
        """Number of data points stored (up to buffer_size)."""
        return self._count

    @property
    def valid_count(self) -> int:
        """Number of non-NaN data points."""
        if self._count < self._size:
            return int(np.count_nonzero(~np.isnan(self._buffer[:self._count])))
        return int(np.count_nonzero(~np.isnan(self._buffer)))

    def get_min_max(self) -> tuple[float, float]:
        """Return (min, max) of valid data. Returns (nan, nan) if no data."""
        data = self._buffer[:self._count] if self._count < self._size else self._buffer
        valid = data[~np.isnan(data)]
        if len(valid) == 0:
            return (np.nan, np.nan)
        return (float(valid.min()), float(valid.max()))

    def clear(self) -> None:
        """Reset all data."""
        self._buffer[:] = np.nan
        self._head = 0
        self._count = 0
        self._running_sum = 0.0
        self._running_sq_sum = 0.0
