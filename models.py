"""Shared data models for assessment and suggested_updates."""

import json
from dataclasses import dataclass, field
from typing import List, Dict

from utils import ms_to_timestamp


@dataclass
class Phase:
    start_ms: int
    end_ms: int
    label: str

    @property
    def start_ts(self) -> str:
        return ms_to_timestamp(self.start_ms)

    @property
    def end_ts(self) -> str:
        return ms_to_timestamp(self.end_ms)

    def to_dict(self) -> dict:
        return {
            "start_ms": self.start_ms,
            "start_ts": self.start_ts,
            "end_ms": self.end_ms,
            "end_ts": self.end_ts,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Phase":
        return cls(d["start_ms"], d["end_ms"], d["label"])


@dataclass
class Cycle:
    start_ms: int
    end_ms: int
    label: str
    oscillation_count: int = 0  # actual up-down pairs within this structural cycle

    @property
    def start_ts(self) -> str:
        return ms_to_timestamp(self.start_ms)

    @property
    def end_ts(self) -> str:
        return ms_to_timestamp(self.end_ms)

    @property
    def bpm(self) -> float:
        duration = self.end_ms - self.start_ms
        if duration <= 0 or self.oscillation_count == 0:
            return 0.0
        return round(self.oscillation_count * 60_000 / duration, 2)

    def to_dict(self) -> dict:
        return {
            "start_ms": self.start_ms,
            "start_ts": self.start_ts,
            "end_ms": self.end_ms,
            "end_ts": self.end_ts,
            "oscillation_count": self.oscillation_count,
            "bpm": self.bpm,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Cycle":
        return cls(d["start_ms"], d["end_ms"], d["label"], d.get("oscillation_count", 0))


@dataclass
class Pattern:
    pattern_label: str
    avg_duration_ms: float
    count: int
    cycles: List[Cycle]

    def to_dict(self) -> dict:
        return {
            "pattern_label": self.pattern_label,
            "avg_duration_ms": self.avg_duration_ms,
            "count": self.count,
            "cycles": [c.to_dict() for c in self.cycles],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Pattern":
        return cls(
            d["pattern_label"],
            d["avg_duration_ms"],
            d["count"],
            [Cycle.from_dict(c) for c in d["cycles"]],
        )


@dataclass
class Phrase:
    start_ms: int
    end_ms: int
    pattern_label: str
    cycle_count: int
    description: str
    oscillation_count: int = 0  # total up-down pairs across all cycles in this phrase

    @property
    def start_ts(self) -> str:
        return ms_to_timestamp(self.start_ms)

    @property
    def end_ts(self) -> str:
        return ms_to_timestamp(self.end_ms)

    @property
    def bpm(self) -> float:
        duration = self.end_ms - self.start_ms
        if duration <= 0 or self.oscillation_count == 0:
            return 0.0
        return round(self.oscillation_count * 60_000 / duration, 2)

    def to_dict(self) -> dict:
        return {
            "start_ms": self.start_ms,
            "start_ts": self.start_ts,
            "end_ms": self.end_ms,
            "end_ts": self.end_ts,
            "oscillation_count": self.oscillation_count,
            "bpm": self.bpm,
            "pattern_label": self.pattern_label,
            "cycle_count": self.cycle_count,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Phrase":
        return cls(
            d["start_ms"], d["end_ms"],
            d["pattern_label"], d["cycle_count"], d["description"],
            d.get("oscillation_count", 0),
        )


@dataclass
class Window:
    start_ms: int
    end_ms: int
    label: str = ""

    @property
    def start_ts(self) -> str:
        return ms_to_timestamp(self.start_ms)

    @property
    def end_ts(self) -> str:
        return ms_to_timestamp(self.end_ms)

    def to_dict(self) -> dict:
        return {
            "start_ms": self.start_ms,
            "start_ts": self.start_ts,
            "end_ms": self.end_ms,
            "end_ts": self.end_ts,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Window":
        return cls(d["start_ms"], d["end_ms"], d.get("label", ""))


@dataclass
class AssessmentResult:
    source_file: str
    analyzed_at: str
    duration_ms: int
    action_count: int
    phases: List[Phase]
    cycles: List[Cycle]
    patterns: List[Pattern]
    phrases: List[Phrase]
    beat_windows: List[Window]
    auto_mode_windows: Dict[str, List[Window]]

    @property
    def duration_ts(self) -> str:
        return ms_to_timestamp(self.duration_ms)

    @property
    def bpm(self) -> float:
        """Average oscillations per minute, derived from directional phase count.

        Each up-phase + down-phase pair counts as one oscillation (one beat).
        This is independent of structural cycle grouping, which can span many
        oscillations and would undercount BPM on pure alternating scripts.
        """
        active = sum(
            1 for p in self.phases
            if "upward" in p.label or "downward" in p.label
        )
        if active == 0 or self.duration_ms <= 0:
            return 0.0
        return round((active / 2) * 60_000 / self.duration_ms, 2)

    def to_dict(self) -> dict:
        return {
            "meta": {
                "source_file": self.source_file,
                "analyzed_at": self.analyzed_at,
                "duration_ms": self.duration_ms,
                "duration_ts": self.duration_ts,
                "action_count": self.action_count,
                "bpm": self.bpm,
            },
            "phases": [p.to_dict() for p in self.phases],
            "cycles": [c.to_dict() for c in self.cycles],
            "patterns": [p.to_dict() for p in self.patterns],
            "phrases": [p.to_dict() for p in self.phrases],
            "beat_windows": [w.to_dict() for w in self.beat_windows],
            "auto_mode_windows": {
                mode: [w.to_dict() for w in windows]
                for mode, windows in self.auto_mode_windows.items()
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AssessmentResult":
        meta = d["meta"]
        return cls(
            source_file=meta["source_file"],
            analyzed_at=meta["analyzed_at"],
            duration_ms=meta["duration_ms"],
            action_count=meta["action_count"],
            phases=[Phase.from_dict(p) for p in d["phases"]],
            cycles=[Cycle.from_dict(c) for c in d["cycles"]],
            patterns=[Pattern.from_dict(p) for p in d["patterns"]],
            phrases=[Phrase.from_dict(p) for p in d["phrases"]],
            beat_windows=[Window.from_dict(w) for w in d["beat_windows"]],
            auto_mode_windows={
                mode: [Window.from_dict(w) for w in windows]
                for mode, windows in d["auto_mode_windows"].items()
            },
        )

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "AssessmentResult":
        with open(path) as f:
            return cls.from_dict(json.load(f))
