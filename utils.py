# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Shared utility functions and base classes used across the pipeline."""

import os
import sys
from typing import List


def writable_base_dir() -> str:
    """Return the directory where writable app data (e.g. output/) should live.

    When running as a PyInstaller frozen executable ``sys.frozen`` is True and
    ``sys._MEIPASS`` points to the *read-only* extracted bundle.  Writable data
    must instead live beside the executable (``sys.executable``).

    In development (non-frozen) mode this is the project root (parent of this
    file), matching the existing convention of ``output/`` at the repo root.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


class LoggingMixin:
    """Minimal list-based message log shared by pipeline stage classes.

    Subclasses call ``super().__init__()`` to initialise the log, then use
    ``self._log(msg)`` to append messages and ``self.get_log()`` to retrieve them.
    """

    def __init__(self) -> None:
        self._log_lines: List[str] = []

    def _log(self, msg: str) -> None:
        self._log_lines.append(msg)

    def get_log(self) -> List[str]:
        """Return all log messages accumulated in this session."""
        return list(self._log_lines)


def parse_timestamp(ts: str) -> int:
    """Convert HH:MM:SS.mmm (or MM:SS.mmm or SS.mmm) to milliseconds."""
    parts = ts.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = 0, parts[0], parts[1]
    else:
        h, m, s = 0, 0, parts[0]

    if "." in str(s):
        sec, ms_str = str(s).split(".")
        ms = int(ms_str.ljust(3, "0")[:3])
    else:
        sec, ms = s, 0

    return int(h) * 3_600_000 + int(m) * 60_000 + int(sec) * 1_000 + ms


def ms_to_timestamp(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS.mmm."""
    ms = max(0, int(ms))
    hours = ms // 3_600_000
    ms %= 3_600_000
    minutes = ms // 60_000
    ms %= 60_000
    seconds = ms // 1_000
    millis = ms % 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Return True if interval [a_start, a_end] overlaps [b_start, b_end]."""
    return not (a_end < b_start or a_start > b_end)


def find_phrase_at(phrases: list, t_ms: int):
    """Return the first phrase whose [start_ms, end_ms] contains t_ms, or None.

    Accepts either Phrase dataclass instances (attribute access) or plain dicts
    (key access), so it works throughout the pipeline without importing models.
    """
    for ph in phrases:
        if hasattr(ph, "start_ms"):
            start, end = ph.start_ms, ph.end_ms
        else:
            start, end = ph["start_ms"], ph["end_ms"]
        if start <= t_ms <= end:
            return ph
    return None


def low_pass_filter(values: list, strengths: list) -> list:
    """Apply a variable-strength low-pass filter.

    strength=0.0 → pass through unchanged
    strength=1.0 → lock to first value (full smoothing)
    """
    if not values:
        return []
    out = [values[0]]
    for i in range(1, len(values)):
        prev = out[-1]
        curr = values[i]
        out.append(prev + (curr - prev) * (1.0 - strengths[i]))
    return out
