"""
Cleanvid - Automated Movie Profanity Filter

A tool for automatically filtering profanity from movies by analyzing subtitles
and muting audio at detected timestamps.
"""

__version__ = "1.0.0"
__author__ = "Aaron"
__license__ = "MIT"

from cleanvid.models.config import Settings
from cleanvid.models.subtitle import SubtitleEntry, SubtitleFile
from cleanvid.models.segment import MuteSegment
from cleanvid.models.processing import ProcessingResult, ProcessingStats

__all__ = [
    "Settings",
    "SubtitleEntry",
    "SubtitleFile",
    "MuteSegment",
    "ProcessingResult",
    "ProcessingStats",
]
