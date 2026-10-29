"""Intro animada del logo de Skull With Gas Mask Co."""

from .intro import (
    FULL_DURATION, QUICK_DURATION, QUICK_THRESHOLD, SkullIntro, Timeline, intro_for_launch,
    is_first_launch,
)

__all__ = [
    "SkullIntro", "Timeline", "intro_for_launch", "is_first_launch",
    "FULL_DURATION", "QUICK_DURATION", "QUICK_THRESHOLD",
]
