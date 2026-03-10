"""Shared utility functions used across assessment and pattern_catalog."""


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
