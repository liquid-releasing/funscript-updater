"""FunscriptAnalyzer: structural analysis of a funscript.

Replaces the four procedural assessment scripts (1-4) with a single class
that can be driven from a CLI or a UI.

Pipeline:
  load() → analyze() → AssessmentResult

The AssessmentResult can be saved as a single JSON file containing:
  phases, cycles, patterns, phrases, beat_windows, auto_mode_windows
  — all with both millisecond and human-readable timestamp fields.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from models import Phase, Cycle, Pattern, Phrase, Window, AssessmentResult
from utils import ms_to_timestamp


@dataclass
class AnalyzerConfig:
    """Tunable parameters for the analysis pipeline."""
    min_velocity: float = 0.02
    min_phase_duration_ms: int = 80
    duration_tolerance: float = 0.20
    velocity_tolerance: float = 0.25
    # Phrases with >= this many cycles → performance window
    performance_cycle_threshold: int = 5
    # Phrases with <= this many cycles → break window
    break_cycle_threshold: int = 2


class FunscriptAnalyzer:
    """Analyzes a funscript and produces a structured AssessmentResult.

    Usage::

        analyzer = FunscriptAnalyzer()
        analyzer.load("path/to/file.funscript")
        result = analyzer.analyze()
        result.save("path/to/assessment.json")
    """

    def __init__(self, config: Optional[AnalyzerConfig] = None):
        self.config = config or AnalyzerConfig()
        self._actions: list = []
        self._source_file: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, path: str) -> None:
        """Load a funscript file."""
        with open(path) as f:
            data = json.load(f)
        self._actions = data["actions"]
        self._source_file = path

    def analyze(self) -> AssessmentResult:
        """Run the full analysis pipeline and return an AssessmentResult."""
        if not self._actions:
            raise RuntimeError("No actions loaded. Call load() first.")

        phases = self._detect_phases()
        cycles = self._detect_cycles(phases)
        patterns = self._detect_patterns(cycles)
        phrases = self._detect_phrases(patterns)
        beat_windows = self._generate_beat_windows(cycles, phrases)
        auto_mode_windows = self._generate_auto_mode_windows(phrases)

        return AssessmentResult(
            source_file=self._source_file,
            analyzed_at=datetime.now().isoformat(),
            duration_ms=self._actions[-1]["at"],
            action_count=len(self._actions),
            phases=phases,
            cycles=cycles,
            patterns=patterns,
            phrases=phrases,
            beat_windows=beat_windows,
            auto_mode_windows=auto_mode_windows,
        )

    # ------------------------------------------------------------------
    # Phase detection
    # ------------------------------------------------------------------

    def _detect_phases(self) -> List[Phase]:
        actions = self._actions
        cfg = self.config
        phases: List[Phase] = []
        phase_start_idx = 0
        phase_velocities: List[float] = []

        for i in range(1, len(actions)):
            t0 = actions[i - 1]["at"]
            t1 = actions[i]["at"]
            p0 = actions[i - 1]["pos"]
            p1 = actions[i]["pos"]

            v = self._velocity(p0, p1, t0, t1)
            phase_velocities.append(v)

            current_dir = self._dir(v, cfg.min_velocity)
            prev_dir = (
                self._dir(phase_velocities[-2], cfg.min_velocity)
                if len(phase_velocities) > 1
                else current_dir
            )

            if current_dir != prev_dir:
                start_t = actions[phase_start_idx]["at"]
                end_t = actions[i - 1]["at"]
                if end_t - start_t >= cfg.min_phase_duration_ms:
                    avg_vel = sum(phase_velocities[:-1]) / max(1, len(phase_velocities[:-1]))
                    phases.append(Phase(start_t, end_t, self._describe_phase(avg_vel)))
                phase_start_idx = i - 1
                phase_velocities = [v]

        if phase_velocities:
            start_t = actions[phase_start_idx]["at"]
            end_t = actions[-1]["at"]
            if end_t - start_t >= cfg.min_phase_duration_ms:
                avg_vel = sum(phase_velocities) / max(1, len(phase_velocities))
                phases.append(Phase(start_t, end_t, self._describe_phase(avg_vel)))

        return phases

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------

    def _detect_cycles(self, phases: List[Phase]) -> List[Cycle]:
        cycles: List[Cycle] = []
        current: List[Phase] = []
        current_dir: Optional[str] = None

        for ph in phases:
            ph_dir = self._phase_direction(ph.label)
            if not current:
                current.append(ph)
                current_dir = ph_dir
                continue

            if ph_dir != current_dir:
                current.append(ph)
                current_dir = ph_dir
            else:
                label = " → ".join(self._phase_direction(p.label) for p in current)
                cycles.append(Cycle(
                    current[0].start_ms, current[-1].end_ms, label,
                    self._oscillation_count(current),
                ))
                current = [ph]
                current_dir = ph_dir

        if current:
            label = " → ".join(self._phase_direction(p.label) for p in current)
            cycles.append(Cycle(
                current[0].start_ms, current[-1].end_ms, label,
                self._oscillation_count(current),
            ))

        return cycles

    # ------------------------------------------------------------------
    # Pattern detection
    # ------------------------------------------------------------------

    def _detect_patterns(self, cycles: List[Cycle]) -> List[Pattern]:
        patterns: List[Pattern] = []
        assigned = [False] * len(cycles)

        for i, base in enumerate(cycles):
            if assigned[i]:
                continue
            group = [base]
            assigned[i] = True
            for j in range(i + 1, len(cycles)):
                if not assigned[j] and self._cycles_similar(base, cycles[j]):
                    group.append(cycles[j])
                    assigned[j] = True
            avg_dur = sum(c.end_ms - c.start_ms for c in group) / len(group)
            patterns.append(Pattern(base.label, avg_dur, len(group), group))

        return patterns

    # ------------------------------------------------------------------
    # Phrase boundary detection
    # ------------------------------------------------------------------

    def _detect_phrases(self, patterns: List[Pattern]) -> List[Phrase]:
        all_cycles = sorted(
            [
                (c.start_ms, c.end_ms, p.pattern_label, c.oscillation_count)
                for p in patterns for c in p.cycles
            ],
            key=lambda x: x[0],
        )

        phrases: List[Phrase] = []
        current: List[tuple] = []
        current_label: Optional[str] = None
        current_oscillations: int = 0

        for start, end, label, osc in all_cycles:
            if not current:
                current.append((start, end))
                current_label = label
                current_oscillations = osc
                continue
            if label == current_label:
                current.append((start, end))
                current_oscillations += osc
            else:
                phrases.append(self._make_phrase(current, current_label, current_oscillations))
                current = [(start, end)]
                current_label = label
                current_oscillations = osc

        if current:
            phrases.append(self._make_phrase(current, current_label, current_oscillations))

        return phrases

    # ------------------------------------------------------------------
    # Beat windows (cycle + phrase boundaries)
    # ------------------------------------------------------------------

    def _generate_beat_windows(
        self, cycles: List[Cycle], phrases: List[Phrase]
    ) -> List[Window]:
        windows: List[Window] = []
        for cy in cycles:
            windows.append(Window(cy.start_ms, cy.end_ms, f"cycle beat ({cy.label})"))
        for ph in phrases:
            windows.append(Window(ph.start_ms, ph.end_ms, f"phrase ({ph.pattern_label})"))
        return windows

    # ------------------------------------------------------------------
    # Auto mode window classification
    # ------------------------------------------------------------------

    def _generate_auto_mode_windows(
        self, phrases: List[Phrase]
    ) -> dict:
        cfg = self.config
        result: dict = {"performance": [], "break": [], "default": []}
        for ph in phrases:
            if ph.cycle_count >= cfg.performance_cycle_threshold:
                result["performance"].append(Window(ph.start_ms, ph.end_ms, ph.description))
            elif ph.cycle_count <= cfg.break_cycle_threshold:
                result["break"].append(Window(ph.start_ms, ph.end_ms, ph.description))
            else:
                result["default"].append(Window(ph.start_ms, ph.end_ms, ph.description))
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _velocity(p0: float, p1: float, t0: int, t1: int) -> float:
        return (p1 - p0) / max(1, t1 - t0)

    @staticmethod
    def _dir(v: float, threshold: float) -> int:
        if v > threshold:
            return 1
        if v < -threshold:
            return -1
        return 0

    @staticmethod
    def _describe_phase(avg_vel: float, threshold: float = 0.02) -> str:
        if avg_vel > threshold:
            return "steady upward motion"
        if avg_vel < -threshold:
            return "steady downward motion"
        return "low-motion plateau"

    @staticmethod
    def _phase_direction(label: str) -> str:
        label = label.lower()
        if "upward" in label:
            return "up"
        if "downward" in label:
            return "down"
        return "flat"

    def _cycles_similar(self, a: Cycle, b: Cycle) -> bool:
        cfg = self.config
        dur_a = a.end_ms - a.start_ms
        dur_b = b.end_ms - b.start_ms
        if abs(dur_a - dur_b) > cfg.duration_tolerance * max(dur_a, dur_b):
            return False
        if a.label != b.label:
            return False
        vel_a = 1.0 / max(1, dur_a)
        vel_b = 1.0 / max(1, dur_b)
        if abs(vel_a - vel_b) > cfg.velocity_tolerance * max(vel_a, vel_b):
            return False
        return True

    @staticmethod
    def _make_phrase(current: list, label: str, oscillation_count: int = 0) -> Phrase:
        n = len(current)
        return Phrase(
            current[0][0], current[-1][1],
            label, n,
            f"{n} cycles of pattern '{label}'",
            oscillation_count,
        )

    def _oscillation_count(self, phases: List[Phase]) -> int:
        """Count up-down pairs (oscillations) in a list of phases."""
        active = sum(1 for p in phases if self._phase_direction(p.label) != "flat")
        return active // 2
