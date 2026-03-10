# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""ViewState — shared zoom/selection state for the funscript viewer.

Framework-agnostic.  The Streamlit app stores one instance in
``st.session_state`` and passes it to every panel that needs it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


ColorMode = Literal["velocity", "amplitude"]


@dataclass
class ViewState:
    """Zoom window, selection range, and display options shared across panels.

    Attributes
    ----------
    zoom_start_ms:
        Left edge of the visible time window (ms).  ``None`` = show from start.
    zoom_end_ms:
        Right edge of the visible time window (ms).  ``None`` = show to end.
    selection_start_ms:
        Start of the user's active selection (ms).  ``None`` = no selection.
    selection_end_ms:
        End of the user's active selection (ms).
    color_mode:
        ``"velocity"`` — colour by rate of change (blue=slow, red=fast).
        ``"amplitude"`` — colour by absolute position value.
    show_phases:
        Overlay phase annotation bands on the chart.
    show_cycles:
        Overlay cycle annotation bands.
    show_patterns:
        Overlay pattern annotation bands.
    show_phrases:
        Overlay phrase annotation bands.
    show_transitions:
        Overlay BPM transition markers.
    """

    zoom_start_ms: Optional[int] = None
    zoom_end_ms: Optional[int] = None

    selection_start_ms: Optional[int] = None
    selection_end_ms: Optional[int] = None

    color_mode: ColorMode = "velocity"

    show_phases:      bool = False
    show_cycles:      bool = False
    show_patterns:    bool = False
    show_phrases:     bool = True
    show_transitions: bool = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def has_zoom(self) -> bool:
        return self.zoom_start_ms is not None and self.zoom_end_ms is not None

    def has_selection(self) -> bool:
        return (
            self.selection_start_ms is not None
            and self.selection_end_ms is not None
        )

    def set_zoom(self, start_ms: int, end_ms: int) -> None:
        """Set zoom window, clamping so start < end."""
        if start_ms >= end_ms:
            return
        self.zoom_start_ms = start_ms
        self.zoom_end_ms = end_ms

    def set_selection(self, start_ms: int, end_ms: int) -> None:
        """Set selection range.  Also narrows zoom to the selection."""
        if start_ms >= end_ms:
            return
        self.selection_start_ms = start_ms
        self.selection_end_ms = end_ms
        # Expand zoom if needed so the selection is visible
        if self.zoom_start_ms is None or self.zoom_start_ms > start_ms:
            self.zoom_start_ms = start_ms
        if self.zoom_end_ms is None or self.zoom_end_ms < end_ms:
            self.zoom_end_ms = end_ms

    def clear_selection(self) -> None:
        self.selection_start_ms = None
        self.selection_end_ms = None

    def reset_zoom(self) -> None:
        self.zoom_start_ms = None
        self.zoom_end_ms = None

    def enabled_kinds(self) -> list:
        """Return the annotation band kinds that are currently toggled on."""
        kinds = []
        if self.show_phases:      kinds.append("phase")
        if self.show_cycles:      kinds.append("cycle")
        if self.show_patterns:    kinds.append("pattern")
        if self.show_phrases:     kinds.append("phrase")
        if self.show_transitions: kinds.append("transition")
        return kinds

    def to_dict(self) -> dict:
        return {
            "zoom_start_ms":      self.zoom_start_ms,
            "zoom_end_ms":        self.zoom_end_ms,
            "selection_start_ms": self.selection_start_ms,
            "selection_end_ms":   self.selection_end_ms,
            "color_mode":         self.color_mode,
            "show_phases":        self.show_phases,
            "show_cycles":        self.show_cycles,
            "show_patterns":      self.show_patterns,
            "show_phrases":       self.show_phrases,
            "show_transitions":   self.show_transitions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ViewState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
