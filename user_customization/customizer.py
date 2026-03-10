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
from utils import LoggingMixin, low_pass_filter, parse_timestamp
from .config import CustomizerConfig

_WindowTriple = Tuple[int, int, str]    # raw windows: (start, end, label)
_ConfigWindow = Tuple[int, int, dict]   # perf/break windows: (start, end, config_overrides)


class WindowCustomizer(LoggingMixin):
    """Applies user-defined performance, break, and raw windows to a funscript."""

    def __init__(self, config: Optional[CustomizerConfig] = None):
        super().__init__()
        self.config = config or CustomizerConfig()
        self._data: dict = {}
        self._actions: list = []
        self._original_actions: list = []

        self._perf_windows: List[_ConfigWindow] = []
        self._break_windows: List[_ConfigWindow] = []
        self._raw_windows: List[_WindowTriple] = []

        self._cycles: list = []   # [{"start": ms, "end": ms}, ...]
        self._beats: list = []    # [{"time": ms}, ...]

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_funscript(self, path: str) -> None:
        """Load the funscript to be customized (output from FunscriptTransformer).

        Raises:
            FileNotFoundError: if the file does not exist.
            ValueError: if the file is not valid JSON or missing the 'actions' list.
        """
        try:
            with open(path) as f:
                self._data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Funscript not found: {path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in funscript '{path}': {e}")
        if "actions" not in self._data or not isinstance(self._data["actions"], list):
            raise ValueError(
                f"Funscript '{path}' is missing a required 'actions' list."
            )
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
            self._perf_windows = [(s, e, cfg) for s, e, _, cfg in windows]
        if break_path:
            windows = self._load_ts_file(break_path, "Break")
            self._break_windows = [(s, e, cfg) for s, e, _, cfg in windows]
        if raw_path:
            windows = self._load_ts_file(raw_path, "Raw")
            self._raw_windows = [(s, e, lbl) for s, e, lbl, _ in windows]

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
        raw_ms = [(s, e) for s, e, _ in self._raw_windows]

        cycle_ranges = [(c["start"], c["end"]) for c in self._cycles]
        cycle_midpoints = [(c["start"] + c["end"]) / 2 for c in self._cycles]
        beat_times = sorted(b["time"] for b in self._beats)

        # Loop starts at 2 so actions[i-1] and actions[i-2] are always valid.
        for i in range(2, len(actions)):
            t = actions[i]["at"]

            if self._in(t, raw_ms):
                self._restore_original(i, actions)
                continue

            self._apply_perf_or_break(i, actions, cfg)
            self._apply_cycle_dynamics(i, actions, cfg, cycle_ranges, cycle_midpoints)
            self._apply_beat_accent(i, actions, cfg, beat_times)

        self._apply_smoothing(actions, cfg, raw_ms)

        self._log(
            f"Customization complete: {len(self._perf_windows)} perf windows, "
            f"{len(self._break_windows)} break windows, "
            f"{len(self._raw_windows)} raw windows."
        )
        return actions

    # ------------------------------------------------------------------
    # Customization sub-steps
    # ------------------------------------------------------------------

    def _restore_original(self, i: int, actions: list) -> None:
        """Overwrite action i with the original (raw-preserve window)."""
        actions[i]["at"]  = self._original_actions[i]["at"]
        actions[i]["pos"] = self._original_actions[i]["pos"]

    def _apply_perf_or_break(self, i: int, actions: list, cfg) -> None:
        """Apply performance or break window processing to action i."""
        t = actions[i]["at"]

        perf_overrides = self._find_window(t, self._perf_windows)
        if perf_overrides is not None:
            eff = self._effective_config(cfg, perf_overrides)

            dt = actions[i]["at"] - actions[i - 1]["at"]
            if abs(dt) < eff.timing_jitter_ms:
                actions[i]["at"] = actions[i - 1]["at"] + eff.timing_jitter_ms

            p0  = actions[i - 1]["pos"]
            p1  = actions[i]["pos"]
            dt  = max(1, actions[i]["at"] - actions[i - 1]["at"])
            vel = (p1 - p0) / dt
            if abs(vel) > eff.max_velocity:
                p1 = p0 + math.copysign(eff.max_velocity * dt, vel)
                actions[i]["pos"] = int(p1)

            dir1 = actions[i - 1]["pos"] - actions[i - 2]["pos"]
            dir2 = actions[i]["pos"]     - actions[i - 1]["pos"]
            if dir1 * dir2 < 0:
                softened = actions[i - 1]["pos"] + dir2 * (1 - eff.reversal_soften)
                blended  = softened * (1 - eff.height_blend) + actions[i]["pos"] * eff.height_blend
                blended  = max(eff.compress_bottom, min(eff.compress_top, blended))
                actions[i]["pos"] = int(blended)
            return

        break_overrides = self._find_window(t, self._break_windows)
        if break_overrides is not None:
            eff = self._effective_config(cfg, break_overrides)
            p = actions[i]["pos"]
            actions[i]["pos"] = int(p + (50 - p) * eff.break_amplitude_reduce)

    def _apply_cycle_dynamics(
        self, i: int, actions: list, cfg,
        cycle_ranges: list, cycle_midpoints: list,
    ) -> None:
        """Apply cycle-aware amplitude dynamics to action i."""
        t      = actions[i]["at"]
        factor = self._cycle_factor(t, cycle_ranges, cycle_midpoints)
        if factor > 0:
            p     = actions[i]["pos"]
            delta = (p - cfg.cycle_dynamics_center) * cfg.cycle_dynamics_strength * factor
            actions[i]["pos"] = max(0, min(100, int(p + delta)))

    def _apply_beat_accent(
        self, i: int, actions: list, cfg, beat_times: list,
    ) -> None:
        """Apply beat-synchronised accent nudge to action i."""
        t = actions[i]["at"]
        if self._near_beat(t, beat_times, cfg.beat_accent_radius_ms):
            p     = actions[i]["pos"]
            nudge = cfg.beat_accent_amount if p >= 50 else -cfg.beat_accent_amount
            actions[i]["pos"] = max(0, min(100, p + nudge))

    def _apply_smoothing(self, actions: list, cfg, raw_ms: list) -> None:
        """Run the final LPF smoothing pass over the full action list."""
        positions = [a["pos"] for a in actions]
        strengths = []
        for a in actions:
            t  = a["at"]
            if self._in(t, raw_ms):
                strengths.append(0.0)
            else:
                po = self._find_window(t, self._perf_windows)
                bo = self._find_window(t, self._break_windows)
                if po is not None:
                    strengths.append(self._effective_config(cfg, po).lpf_performance)
                elif bo is not None:
                    strengths.append(self._effective_config(cfg, bo).lpf_break)
                else:
                    strengths.append(0.0)

        smoothed = low_pass_filter(positions, strengths)
        for i, p in enumerate(smoothed):
            actions[i]["pos"] = int(p)

    def save(self, path: str) -> None:
        """Write the customized funscript to disk."""
        self._data["actions"] = self._actions
        with open(path, "w") as f:
            json.dump(self._data, f, indent=2)
        self._log(f"Saved output: {path}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_ts_file(self, path: str, label: str) -> List[Tuple[int, int, str, dict]]:
        """Load a window JSON file.

        Each entry may carry an optional ``"label"`` and/or ``"config"`` key:

            [{"start": "00:01:10.000", "end": "00:01:25.000",
              "label": "chorus", "config": {"max_velocity": 0.28}}]

        Returns a list of ``(start_ms, end_ms, label, config_overrides)`` tuples.
        Old files without ``"config"`` return an empty dict for that field.
        """
        if not os.path.exists(path):
            self._log(f"{label}: file not found, treating as empty.")
            return []
        with open(path) as f:
            data = json.load(f)
        out = [
            (
                parse_timestamp(w["start"]),
                parse_timestamp(w["end"]),
                w.get("label", ""),
                w.get("config", {}),
            )
            for w in data
        ]
        self._log(f"{label}: loaded {len(out)} windows.")
        return out

    @staticmethod
    def _in(t: int, windows) -> bool:
        """Return True if *t* falls within any (start, end) pair in *windows*."""
        return any(s <= t <= e for s, e in windows)

    @staticmethod
    def _find_window(t: int, windows: List[_ConfigWindow]) -> Optional[dict]:
        """Return the config-overrides dict for the first window containing *t*.

        Returns ``None`` if *t* is not inside any window (distinct from an
        empty override dict ``{}`` which means "in a window, no overrides").
        """
        for s, e, overrides in windows:
            if s <= t <= e:
                return overrides
        return None

    @staticmethod
    def _effective_config(base: "CustomizerConfig", overrides: dict) -> "CustomizerConfig":
        """Return a CustomizerConfig with *overrides* merged on top of *base*."""
        if not overrides:
            return base
        merged = base.to_dict()
        merged.update(overrides)
        return CustomizerConfig.from_dict(merged)

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
