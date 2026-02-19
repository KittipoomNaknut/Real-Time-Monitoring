"""
Interactions — Mouse tracking, keyboard shortcuts, screenshot & video recording.

Keyboard Shortcuts (cross-platform):
=====================================
  Q / ESC  — Quit
  P / SPACE — Pause/Resume data collection
  S        — Save screenshot (PNG)
  R        — Reset (clear all data)
  V        — Start/stop video recording (MP4)
  T        — Cycle theme (dark → light → midnight → ...)
  +/-      — Increase/decrease target FPS by 10
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field

import cv2
import numpy as np

from .platform_utils import PlatformInfo


# ────────────────────────────────────────────────────────────
# Mouse State
# ────────────────────────────────────────────────────────────
class MouseTracker:
    """
    Tracks mouse position inside an OpenCV window.

    OpenCV mouse callbacks run on the HighGUI thread, same as the
    thread that called cv2.imshow(). No cross-thread concerns if
    you read mouse_pos from the same thread.
    """

    def __init__(self):
        self._pos: Optional[tuple[int, int]] = None
        self._inside = False
        self._attached_window: Optional[str] = None

    def attach(self, window_name: str) -> None:
        """Register mouse callback for a named window."""
        self._attached_window = window_name
        cv2.setMouseCallback(window_name, self._callback)

    def _callback(self, event: int, x: int, y: int,
                  flags: int, param) -> None:
        if event == cv2.EVENT_MOUSEMOVE:
            self._pos = (x, y)
            self._inside = True
        elif event == cv2.EVENT_MOUSELEAVE:
            self._inside = False
            self._pos = None

    @property
    def position(self) -> Optional[tuple[int, int]]:
        """Current mouse (x, y) or None if outside window."""
        return self._pos if self._inside else None


# ────────────────────────────────────────────────────────────
# Screenshot
# ────────────────────────────────────────────────────────────
def save_screenshot(canvas: np.ndarray, directory: str = ".") -> str:
    """
    Save current canvas as PNG with timestamp filename.

    Returns the full path of the saved file.
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = path / f"liveplot_{timestamp}.png"
    cv2.imwrite(str(filename), canvas)
    return str(filename)


# ────────────────────────────────────────────────────────────
# Video Recording
# ────────────────────────────────────────────────────────────
class VideoRecorder:
    """
    Record the plot to an MP4 file using OpenCV VideoWriter.

    Cross-platform codec selection:
      - Windows: 'mp4v' (MPEG-4) or 'H264' (if available)
      - Linux: 'mp4v' (MPEG-4) — most universally available
      - Fallback: 'XVID' (widely supported)
    """

    def __init__(self, width: int, height: int, fps: float = 30.0,
                 directory: str = "."):
        self._width = width
        self._height = height
        self._fps = fps
        self._directory = directory
        self._writer: Optional[cv2.VideoWriter] = None
        self._filepath: Optional[str] = None
        self._recording = False

    def start(self) -> str:
        """Start recording. Returns filepath."""
        path = Path(self._directory)
        path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._filepath = str(path / f"liveplot_{timestamp}.mp4")

        # Try codecs in order of preference
        codecs = ['mp4v', 'avc1', 'XVID']
        for codec in codecs:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            self._writer = cv2.VideoWriter(
                self._filepath, fourcc, self._fps,
                (self._width, self._height)
            )
            if self._writer.isOpened():
                self._recording = True
                return self._filepath
            self._writer.release()

        raise RuntimeError(
            f"No suitable video codec found. Tried: {codecs}. "
            f"Install ffmpeg: sudo apt install ffmpeg (Linux) / choco install ffmpeg (Windows)"
        )

    def write_frame(self, frame: np.ndarray) -> None:
        """Write a frame. No-op if not recording."""
        if self._recording and self._writer is not None:
            self._writer.write(frame)

    def stop(self) -> Optional[str]:
        """Stop recording. Returns filepath or None."""
        if self._writer is not None:
            self._writer.release()
            self._writer = None
        self._recording = False
        return self._filepath

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def filepath(self) -> Optional[str]:
        return self._filepath


# ────────────────────────────────────────────────────────────
# Keyboard Action Dispatcher
# ────────────────────────────────────────────────────────────
@dataclass
class KeyAction:
    """Result of processing a key press."""
    quit: bool = False
    toggle_pause: bool = False
    screenshot: bool = False
    reset: bool = False
    toggle_recording: bool = False
    cycle_theme: bool = False
    fps_delta: int = 0
    status_message: str = ""


def process_key(key: int) -> KeyAction:
    """
    Map a normalized key code to an action.

    Uses normalized 8-bit key codes (already masked by normalize_key).
    """
    if key < 0:
        return KeyAction()

    action = KeyAction()

    if key == ord('q') or key == 27:       # Q or ESC
        action.quit = True
    elif key == ord('p') or key == 32:     # P or Space
        action.toggle_pause = True
    elif key == ord('s'):
        action.screenshot = True
    elif key == ord('r'):
        action.reset = True
    elif key == ord('v'):
        action.toggle_recording = True
    elif key == ord('t'):
        action.cycle_theme = True
    elif key == ord('+') or key == ord('='):
        action.fps_delta = 10
    elif key == ord('-') or key == ord('_'):
        action.fps_delta = -10

    return action
