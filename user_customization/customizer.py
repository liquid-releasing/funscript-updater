"""WindowCustomizer: user-defined performance, break, and raw window customization (Part 3).

Layers on top of the FunscriptTransformer output. The user defines windows
using human-readable HH:MM:SS.mmm timestamps in JSON files, then calls
customize() to apply them.

Window priority (highest to lowest):
  1. Raw preserve  — original actions copied verbatim
  2. Performance   — velocity limiting, reversal softening, compression
  3. Break         — pull positions toward center, reduce amplitude
  (Cycle dynamics and beat accents apply everywhere outside raw windows.)

Typical usage::

    customizer = WindowCustomizer()
    customizer.load_funscript("transformed.funscript")
    customizer.load_assessment_from_file("assessment.json")
    customizer.load_manual_overrides(
        perf_path="manual_performance.json",
        break_path="manual_break.json",
        raw_path="raw_windows.json",
    )
    customizer.load_beats_from_file("beats.json")   # optional
    customizer.customize()
    customizer.save("customized.funscript")
"""

import bisect
import copy
import json
import math
import os
from typing import List, Optional, Tuple

from models import AssessmentResult
from utils import low_pass_filter, parse_timestamp
from .config import CustomizerConfig

_WindowPair = Tuple[int, int]
_WindowTriple = Tuple[int, int, str]


class WindowCustomizer:
    """Applies user-defined performance, break, and raw windows to a funscript."""

    def __init__(self, config: Optional[CustomizerConfig] = None):
        self.config = config or CustomizerConfig()
        self._data: dict = {}
        self._actions: list = []
        self._original_actions: list = []
        self._log_lines: List[str] = []

        self._perf_windows: List[_WindowPair] = []
        self._break_windows: List[_WindowPair] = []
        self._raw_windows: List[_WindowTriple] = []

        self._cycles: list = []   # [{"start": ms, "end": ms}, ...]
        self._beats: list = []    # [{"time": ms}, ...]

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_funscript(self, path: str) -> None:
        """Load the funscript to be customized (output from FunscriptTransformer)."""
        with open(path) as f:
            self._data = json.load(f)
        self._actions = self._data["actions"]
        self._original_actions = copy.deepcopy(self._actions)
        self._log(f"Loaded funscript: {path} ({len(self._actions)} actions)")

    def load_assessment(self, assessment: AssessmentResult) -> None:
        """Load cycle data from an AssessmentResult (used for Task 5 dynamics)."""
        self._cycles = [{"start": c.start_ms, "end": c.end_ms} for c in assessment.cycles]
        self._log(f"Loaded assessment: {len(self._cycles)} cycles")

    def load_assessment_from_file(self, path: str) -> None:
        """Load cycle data from a saved assessment JSON file."""
        assessment = AssessmentResult.load(path)
        self.load_assessment(assessment)

    def load_manual_overrides(
        self,
        perf_path: Optional[str] = None,
        break_path: Optional[str] = None,
        raw_path: Optional[str] = None,
    ) -> None:
        """Load user-defined windows from JSON files with HH:MM:SS.mmm timestamps.

        Each file is a JSON array of objects with "start", "end", and optional "label":

            [{"start": "00:01:10.000", "end": "00:01:25.000", "label": "chorus"}]
        """
        if perf_path:
            windows = self._load_ts_file(perf_path, "Performance")
            self._perf_windows = [(s, e) for s, e, _ in windows]
        if break_path:
            windows = self._load_ts_file(break_path, "Break")
            self._break_windows = [(s, e) for s, e, _ in windows]
        if raw_path:
            self._raw_windows = self._load_ts_file(raw_path, "Raw")

    def load_beats_from_file(self, path: str) -> None:
        """Load beat times from a JSON file (enables Task 6 beat accents).

        Format: [{"time": 1200}, {"time": 1500}, ...]
        """
        if not os.path.exists(path):
            self._log(f"Beats file not found: {path}. Beat accents inactive.")
            return
        with open(path) as f:
            self._beats = json.load(f)
        self._log(f"Loaded {len(self._beats)} beats from {path}")

    # ------------------------------------------------------------------
    # Customization
    # ------------------------------------------------------------------

    def customize(self) -> list:
        """Apply performance, break, raw, cycle dynamics, and beat accents.

        Returns the modified actions list.
        """
        cfg = self.config
        actions = self._actions
        raw_ms: List[_WindowPair] = [(s, e) for s, e, _ in self._raw_windows]

        cycle_ranges = [(c["start"], c["end"]) for c in self._cycles]
        cycle_midpoints = [(c["start"] + c["end"]) / 2 for c in self._cycles]
        beat_times = sorted(b["time"] for b in self._beats)

        for i in range(2, len(actions)):
            t = actions[i]["at"]

            # Task 4 — raw preserve (highest priority)
            if self._in(t, raw_ms):
                actions[i]["at"] = self._original_actions[i]["at"]
                actions[i]["pos"] = self._original_actions[i]["pos"]
                continue

            # Task 2 — performance window
            if self._in(t, self._perf_windows):
                dt = actions[i]["at"] - actions[i - 1]["at"]
                if abs(dt) < cfg.timing_jitter_ms:
                    actions[i]["at"] = actions[i - 1]["at"] + cfg.timing_jitter_ms

                p0 = actions[i - 1]["pos"]
                p1 = actions[i]["pos"]
                dt = max(1, actions[i]["at"] - actions[i - 1]["at"])
                vel = (p1 - p0) / dt

                if abs(vel) > cfg.max_velocity:
                    p1 = p0 + math.copysign(cfg.max_velocity * dt, vel)
                    actions[i]["pos"] = int(p1)

                dir1 = actions[i - 1]["pos"] - actions[i - 2]["pos"]
                dir2 = actions[i]["pos"] - actions[i - 1]["pos"]
                if dir1 * dir2 < 0:
                    softened = actions[i - 1]["pos"] + dir2 * (1 - cfg.reversal_soften)
                    blended = softened * (1 - cfg.height_blend) + actions[i]["pos"] * cfg.height_blend
                    blended = max(cfg.compress_bottom, min(cfg.compress_top, blended))
                    actions[i]["pos"] = int(blended)

            # Task 3 — break window
            elif self._in(t, self._break_windows):
                p = actions[i]["pos"]
                actions[i]["pos"] = int(p + (50 - p) * cfg.break_amplitude_reduce)

            # Task 5 — cycle-aware dynamics
            factor = self._cycle_factor(t, cycle_ranges, cycle_midpoints)
            if factor > 0:
                p = actions[i]["pos"]
                delta = (p - cfg.cycle_dynamics_center) * cfg.cycle_dynamics_strength * factor
                actions[i]["pos"] = max(0, min(100, int(p + delta)))

            # Task 6 — beat-synced accents
            if self._near_beat(t, beat_times, cfg.beat_accent_radius_ms):
                p = actions[i]["pos"]
                nudge = cfg.beat_accent_amount if p >= 50 else -cfg.beat_accent_amount
                actions[i]["pos"] = max(0, min(100, p + nudge))

        # --- Final smoothing pass ---
        positions = [a["pos"] for a in actions]
        strengths = []
        for a in actions:
            t = a["at"]
            if self._in(t, raw_ms):
                strengths.append(0.0)
            elif self._in(t, self._perf_windows):
                strengths.append(cfg.lpf_performance)
            elif self._in(t, self._break_windows):
                strengths.append(cfg.lpf_break)
            else:
                strengths.append(0.0)

        smoothed = low_pass_filter(positions, strengths)
        for i, p in enumerate(smoothed):
            actions[i]["pos"] = int(p)

        self._log(
            f"Customization complete: {len(self._perf_windows)} perf windows, "
            f"{len(self._break_windows)} break windows, "
            f"{len(self._raw_windows)} raw windows."
        )
        return actions

    def save(self, path: str) -> None:
        """Write the customized funscript to disk."""
        self._data["actions"] = self._actions
        with open(path, "w") as f:
            json.dump(self._data, f, indent=2)
        self._log(f"Saved output: {path}")

    def get_log(self) -> List[str]:
        """Return all log messages produced during this session."""
        return list(self._log_lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_ts_file(self, path: str, label: str) -> List[_WindowTriple]:
        if not os.path.exists(path):
            self._log(f"{label}: file not found, treating as empty.")
            return []
        with open(path) as f:
            data = json.load(f)
        out = [
            (parse_timestamp(w["start"]), parse_timestamp(w["end"]), w.get("label", ""))
            for w in data
        ]
        self._log(f"{label}: loaded {len(out)} windows.")
        return out

    def _log(self, msg: str) -> None:
        self._log_lines.append(msg)

    @staticmethod
    def _in(t: int, windows: List[_WindowPair]) -> bool:
        return any(s <= t <= e for s, e in windows)

    @staticmethod
    def _cycle_factor(t: int, ranges: list, midpoints: list) -> float:
        for (start, end), mid in zip(ranges, midpoints):
            if start <= t <= end:
                span = end - start
                if span <= 0:
                    return 0.0
                x = (t - start) / span
                return 0.5 * (1 - math.cos(2 * math.pi * x))
        return 0.0

    @staticmethod
    def _near_beat(t: int, beat_times: list, radius_ms: int) -> bool:
        if not beat_times:
            return False
        idx = bisect.bisect_left(beat_times, t)
        candidates = []
        if idx < len(beat_times):
            candidates.append(beat_times[idx])
        if idx > 0:
            candidates.append(beat_times[idx - 1])
        nearest = min(candidates, key=lambda bt: abs(bt - t))
        return abs(nearest - t) <= radius_ms
