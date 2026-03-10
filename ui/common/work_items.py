"""Work item models for the Funscript Forge UI.

A WorkItem represents a tagged time window in a funscript that the user has
reviewed and assigned a type (performance, break, raw, or neutral).  Each
type maps directly to one of the customizer's window inputs.

This module has no UI-framework dependency and can be imported by any
deployment target (Streamlit, Flask/web, desktop, etc.).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from utils import ms_to_timestamp


class ItemType(str, Enum):
    """Classification for a work item / time window."""

    PERFORMANCE = "performance"
    BREAK = "break"
    RAW = "raw"
    NEUTRAL = "neutral"


# Default per-type configuration values mirroring CustomizerConfig defaults.
_PERF_DEFAULTS: Dict[str, Any] = {
    "max_velocity": 0.32,
    "reversal_soften": 0.62,
    "height_blend": 0.75,
    "compress_bottom": 15,
    "compress_top": 92,
    "lpf_performance": 0.16,
    "timing_jitter_ms": 3,
}

_BREAK_DEFAULTS: Dict[str, Any] = {
    "break_amplitude_reduce": 0.40,
    "lpf_break": 0.30,
}


def _default_config(item_type: ItemType) -> Dict[str, Any]:
    if item_type == ItemType.PERFORMANCE:
        return dict(_PERF_DEFAULTS)
    if item_type == ItemType.BREAK:
        return dict(_BREAK_DEFAULTS)
    return {}


@dataclass
class WorkItem:
    """A user-reviewed, typed time window within a funscript.

    Attributes
    ----------
    id:
        Unique identifier (UUID4 string).
    start_ms:
        Window start in milliseconds.
    end_ms:
        Window end in milliseconds.
    item_type:
        Classification — controls which customizer task applies.
    label:
        Optional human-readable label shown in the UI.
    bpm:
        Representative BPM of this section (informational).
    source:
        How the item was created: ``"phrase"``, ``"bpm_transition"``,
        or ``"manual"``.
    config:
        Type-specific configuration overrides.  Keys match the
        corresponding CustomizerConfig fields for the item type.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_ms: int = 0
    end_ms: int = 0
    item_type: ItemType = ItemType.NEUTRAL
    label: str = ""
    bpm: float = 0.0
    source: str = "manual"
    config: Dict[str, Any] = field(default_factory=dict)
    # Status lifecycle: "todo" → "in_progress" → "done"
    status: str = "todo"

    def __post_init__(self) -> None:
        # Populate config with type defaults if empty.
        if not self.config:
            self.config = _default_config(self.item_type)

    @property
    def completed(self) -> bool:
        return self.status == "done"

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def start_ts(self) -> str:
        return ms_to_timestamp(self.start_ms)

    @property
    def end_ts(self) -> str:
        return ms_to_timestamp(self.end_ms)

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    @property
    def duration_ts(self) -> str:
        return ms_to_timestamp(self.duration_ms)

    # ------------------------------------------------------------------
    # Type helpers
    # ------------------------------------------------------------------

    def set_type(self, item_type: ItemType) -> None:
        """Change the item type and reset config to the new type's defaults."""
        self.item_type = item_type
        self.config = _default_config(item_type)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_window_dict(self) -> Dict[str, Any]:
        """Return a window dict compatible with the customizer's JSON input."""
        d: Dict[str, Any] = {
            "start": self.start_ts,
            "end": self.end_ts,
        }
        if self.label:
            d["label"] = self.label
        if self.config:
            d["config"] = self.config
        return d

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "item_type": self.item_type.value,
            "label": self.label,
            "bpm": self.bpm,
            "source": self.source,
            "config": self.config,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkItem":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            start_ms=d["start_ms"],
            end_ms=d["end_ms"],
            item_type=ItemType(d.get("item_type", "neutral")),
            label=d.get("label", ""),
            bpm=d.get("bpm", 0.0),
            source=d.get("source", "manual"),
            config=d.get("config", {}),
            # migrate old bool "completed" field
            status=d.get("status", "done" if d.get("completed", False) else "todo"),
        )


# ------------------------------------------------------------------
# Factory helpers
# ------------------------------------------------------------------


def items_from_phrases(phrases: List[Dict[str, Any]]) -> List[WorkItem]:
    """Create one neutral WorkItem per phrase from assessment output.

    Parameters
    ----------
    phrases:
        List of phrase dicts from ``AssessmentResult.to_dict()["phrases"]``.
    """
    items: List[WorkItem] = []
    for ph in phrases:
        items.append(WorkItem(
            start_ms=ph["start_ms"],
            end_ms=ph["end_ms"],
            bpm=ph.get("bpm", 0.0),
            label=ph.get("pattern_label", ""),
            source="phrase",
        ))
    return items


def items_from_bpm_transitions(
    transitions: List[Dict[str, Any]],
    phrases: List[Dict[str, Any]],
) -> List[WorkItem]:
    """Create WorkItems aligned to BPM transition boundaries.

    Each transition marks the *start* of a new phrase-like region.  We
    emit one WorkItem per region, bounded by adjacent transition points.

    Parameters
    ----------
    transitions:
        List of bpm_transition dicts from assessment output.
    phrases:
        List of phrase dicts (used to determine first/last timestamp).
    """
    if not transitions or not phrases:
        return []

    # Collect boundary timestamps (ms) from transitions + overall extents.
    boundaries = sorted({t["at_ms"] for t in transitions})
    first_ms = phrases[0]["start_ms"]
    last_ms = phrases[-1]["end_ms"]

    # Build regions between consecutive boundaries.
    edges = [first_ms] + boundaries + [last_ms]
    items: List[WorkItem] = []
    for i in range(len(edges) - 1):
        start = edges[i]
        end = edges[i + 1]
        if end <= start:
            continue
        # Find a representative BPM from matching phrase.
        bpm = _bpm_for_region(start, end, phrases)
        items.append(WorkItem(
            start_ms=start,
            end_ms=end,
            bpm=bpm,
            source="bpm_transition",
        ))
    return items


def items_from_time_windows(
    duration_ms: int,
    window_ms: int,
    bpm: float = 0.0,
) -> List[WorkItem]:
    """Create neutral WorkItems by splitting *duration_ms* into equal windows.

    Used as a fallback for uniform-tempo content that produces only a single
    phrase with no BPM transitions.

    Parameters
    ----------
    duration_ms:
        Total funscript duration in milliseconds.
    window_ms:
        Size of each segment in milliseconds.
    bpm:
        Representative BPM to attach to every item (informational).
    """
    items: List[WorkItem] = []
    start = 0
    while start < duration_ms:
        end = min(start + window_ms, duration_ms)
        items.append(WorkItem(
            start_ms=start,
            end_ms=end,
            bpm=bpm,
            source="time_window",
        ))
        start = end
    return items


def _bpm_for_region(
    start_ms: int, end_ms: int, phrases: List[Dict[str, Any]]
) -> float:
    """Return the BPM of the first phrase that overlaps [start_ms, end_ms]."""
    for ph in phrases:
        if ph["start_ms"] < end_ms and ph["end_ms"] > start_ms:
            return ph.get("bpm", 0.0)
    return 0.0
