"""
Color Palette & Theme System — All colors in BGR format (OpenCV convention).

Design principles:
  - Vibrant series colors with high mutual perceptual distance
  - Dark theme optimized for low eye strain during monitoring
  - Light theme available for screenshots/presentations
  - All colors stored as BGR tuples for direct use with OpenCV
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class Theme:
    """Complete color theme for the plot."""

    name: str

    # Background & structural elements
    bg: tuple[int, int, int]
    grid_major: tuple[int, int, int]
    grid_minor: tuple[int, int, int]
    grid_center: tuple[int, int, int]
    border: tuple[int, int, int]

    # Text
    axis_label: tuple[int, int, int]
    title: tuple[int, int, int]
    value_text: tuple[int, int, int]
    fps_text: tuple[int, int, int]

    # Legend overlay
    legend_bg: tuple[int, int, int]
    legend_alpha: float = 0.7  # blend weight for semi-transparent box

    # Data series palette (up to 8 distinguishable colors)
    series_colors: tuple[tuple[int, int, int], ...] = ()


# ────────────────────────────────────────────────────────────
# Built-in Themes
# ────────────────────────────────────────────────────────────

DARK_THEME = Theme(
    name="dark",
    bg=(18, 18, 24),
    grid_major=(45, 45, 55),
    grid_minor=(32, 32, 40),
    grid_center=(60, 60, 75),
    border=(50, 50, 65),
    axis_label=(140, 140, 160),
    title=(200, 200, 220),
    value_text=(180, 180, 200),
    fps_text=(80, 80, 100),
    legend_bg=(30, 30, 40),
    legend_alpha=0.7,
    series_colors=(
        (255, 100, 255),   # Magenta
        (100, 255, 100),   # Green
        (100, 200, 255),   # Cyan-blue
        (80, 180, 255),    # Orange (BGR)
        (100, 100, 255),   # Red
        (255, 255, 100),   # Light cyan
        (150, 100, 255),   # Coral
        (255, 200, 50),    # Sky blue
    ),
)

LIGHT_THEME = Theme(
    name="light",
    bg=(245, 245, 248),
    grid_major=(210, 210, 218),
    grid_minor=(228, 228, 234),
    grid_center=(180, 180, 195),
    border=(190, 190, 200),
    axis_label=(80, 80, 100),
    title=(30, 30, 50),
    value_text=(50, 50, 70),
    fps_text=(160, 160, 175),
    legend_bg=(235, 235, 240),
    legend_alpha=0.85,
    series_colors=(
        (180, 50, 180),    # Dark magenta
        (50, 180, 50),     # Dark green
        (200, 120, 30),    # Teal (BGR)
        (30, 130, 220),    # Orange (BGR)
        (60, 60, 200),     # Red
        (180, 180, 30),    # Dark cyan
        (100, 50, 200),    # Crimson
        (200, 150, 20),    # Blue
    ),
)

MIDNIGHT_THEME = Theme(
    name="midnight",
    bg=(12, 8, 4),
    grid_major=(35, 30, 25),
    grid_minor=(24, 20, 16),
    grid_center=(55, 45, 35),
    border=(45, 38, 30),
    axis_label=(120, 130, 140),
    title=(180, 195, 210),
    value_text=(160, 170, 185),
    fps_text=(70, 75, 85),
    legend_bg=(22, 18, 12),
    legend_alpha=0.75,
    series_colors=(
        (255, 180, 80),    # Warm cyan
        (100, 255, 180),   # Mint
        (180, 120, 255),   # Lavender
        (80, 200, 255),    # Amber
        (120, 100, 255),   # Salmon
        (255, 220, 100),   # Ice blue
        (100, 255, 255),   # Yellow
        (255, 150, 150),   # Light blue
    ),
)

# Registry of all themes
THEMES: dict[str, Theme] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "midnight": MIDNIGHT_THEME,
}


def get_theme(name: str) -> Theme:
    """Get a theme by name. Raises KeyError if not found."""
    if name not in THEMES:
        available = ', '.join(THEMES.keys())
        raise KeyError(f"Theme '{name}' not found. Available: {available}")
    return THEMES[name]


def register_theme(theme: Theme) -> None:
    """Register a custom theme."""
    THEMES[theme.name] = theme
