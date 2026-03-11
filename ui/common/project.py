# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Project session state for the Funscript Forge UI.

A Project holds everything needed to drive one editing session:
  - which funscript is loaded
  - the assessment result for that funscript
  - the user's work items (tagged time windows)

It is framework-agnostic; Streamlit, Flask, and local-desktop code all
import from here.

Typical workflow
----------------
1. ``project = Project.from_funscript("path/to/file.funscript")``
2. User reviews ``project.work_items`` and calls ``set_item_type()``.
3. ``project.export_windows("output/")`` writes JSON files for the customizer.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# Allow imports from the project root regardless of CWD.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from assessment.analyzer import FunscriptAnalyzer, AnalyzerConfig
from models import AssessmentResult
from ui.common.work_items import (
    ItemType,
    WorkItem,
    items_from_bpm_transitions,
    items_from_phrases,
    items_from_time_windows,
)

# Fallback segmentation: if assessment produces ≤ this many work items for
# content longer than FALLBACK_MIN_DURATION_MS, split into fixed windows.
_FALLBACK_WINDOW_MS: int = 5 * 60 * 1000   # 5 minutes per segment
_FALLBACK_MIN_DURATION_MS: int = 10 * 60 * 1000  # only trigger for 10+ min


@dataclass
class Project:
    """All state for one funscript editing session.

    Attributes
    ----------
    funscript_path:
        Absolute or relative path to the source ``.funscript`` file.
    assessment:
        Parsed ``AssessmentResult`` (populated after ``run_assessment()``).
    work_items:
        The user's reviewed and typed time windows.
    selected_item_id:
        ID of the currently selected work item in the UI (optional).
    """

    funscript_path: str = ""
    assessment: Optional[AssessmentResult] = None
    work_items: List[WorkItem] = field(default_factory=list)
    selected_item_id: Optional[str] = None
    custom_name: str = ""        # User-defined project name (empty = use filename)
    description: str = ""       # User-defined description (empty = use auto_description)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_funscript(
        cls,
        path: str,
        analyzer_config: Optional[AnalyzerConfig] = None,
        existing_assessment_path: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> "Project":
        """Create a Project and run (or load) the assessment.

        Parameters
        ----------
        path:
            Path to the ``.funscript`` source file.
        analyzer_config:
            Optional custom analyzer settings.
        existing_assessment_path:
            If provided, load the assessment JSON instead of re-running it.
        progress_callback:
            Optional callable forwarded to :meth:`FunscriptAnalyzer.analyze`
            for stage-by-stage progress reporting.
        """
        project = cls(funscript_path=path)
        if existing_assessment_path and os.path.exists(existing_assessment_path):
            project.assessment = AssessmentResult.load(existing_assessment_path)
        else:
            project.run_assessment(analyzer_config, progress_callback=progress_callback)
        project._init_work_items()
        return project

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------

    def run_assessment(
        self,
        config: Optional[AnalyzerConfig] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> AssessmentResult:
        """Run the analyzer on the loaded funscript and cache the result."""
        analyzer = FunscriptAnalyzer(config=config or AnalyzerConfig())
        analyzer.load(self.funscript_path)
        self.assessment = analyzer.analyze(progress_callback=progress_callback)
        return self.assessment

    def save_assessment(self, output_path: str) -> None:
        """Persist the assessment JSON to disk."""
        if self.assessment is None:
            raise RuntimeError("No assessment — call run_assessment() first.")
        self.assessment.save(output_path)

    # ------------------------------------------------------------------
    # Work item management
    # ------------------------------------------------------------------

    def _init_work_items(self) -> None:
        """Populate work_items from the assessment (called once on load).

        Strategy (in priority order):
        1. BPM transitions present → segment at transition boundaries.
        2. Multiple phrases → one item per phrase.
        3. Fallback → fixed time-window segments (for uniform-tempo content
           where the whole piece is one long phrase with no BPM changes).
        """
        if self.assessment is None:
            return
        ad = self.assessment.to_dict()
        phrases = ad.get("phrases", [])
        transitions = ad.get("bpm_transitions", [])

        if transitions:
            self.work_items = items_from_bpm_transitions(transitions, phrases)
        elif len(phrases) > 1:
            self.work_items = items_from_phrases(phrases)
        elif (
            self.assessment.duration_ms >= _FALLBACK_MIN_DURATION_MS
            and len(phrases) <= 1
        ):
            # Uniform-tempo fallback: divide into fixed-size windows.
            self.work_items = items_from_time_windows(
                self.assessment.duration_ms, _FALLBACK_WINDOW_MS,
                bpm=phrases[0].get("bpm", 0.0) if phrases else 0.0,
            )
        else:
            self.work_items = items_from_phrases(phrases)

    def get_item(self, item_id: str) -> Optional[WorkItem]:
        """Return the work item with the given ID, or None."""
        for item in self.work_items:
            if item.id == item_id:
                return item
        return None

    def set_item_type(self, item_id: str, item_type: ItemType) -> None:
        """Update the type of a work item (resets its config to defaults)."""
        item = self.get_item(item_id)
        if item:
            item.set_type(item_type)

    def update_item_config(self, item_id: str, key: str, value) -> None:
        """Set a single config key on a work item."""
        item = self.get_item(item_id)
        if item:
            item.config[key] = value

    def update_item_times(
        self, item_id: str, start_ms: int, end_ms: int
    ) -> None:
        """Adjust the time window of a work item.

        Raises
        ------
        ValueError
            If ``end_ms <= start_ms``.
        """
        if end_ms <= start_ms:
            raise ValueError(
                f"end_ms ({end_ms}) must be greater than start_ms ({start_ms})"
            )
        item = self.get_item(item_id)
        if item:
            item.start_ms = start_ms
            item.end_ms = end_ms

    def set_item_status(self, item_id: str, status: str) -> None:
        """Set a work item's status: 'todo', 'in_progress', or 'done'."""
        item = self.get_item(item_id)
        if item:
            item.status = status

    def set_item_completed(self, item_id: str, completed: bool) -> None:
        """Mark a work item as done (True) or reopen it as todo (False)."""
        self.set_item_status(item_id, "done" if completed else "todo")

    def add_item(self, item: WorkItem) -> None:
        """Insert a new work item (e.g. manually drawn)."""
        self.work_items.append(item)
        self.work_items.sort(key=lambda w: w.start_ms)

    def remove_item(self, item_id: str) -> None:
        """Delete a work item by ID."""
        self.work_items = [w for w in self.work_items if w.id != item_id]
        if self.selected_item_id == item_id:
            self.selected_item_id = None

    # ------------------------------------------------------------------
    # Derived window lists (for the customizer)
    # ------------------------------------------------------------------

    def performance_windows(self) -> List[Dict]:
        return [w.to_window_dict() for w in self.work_items if w.item_type == ItemType.PERFORMANCE]

    def break_windows(self) -> List[Dict]:
        return [w.to_window_dict() for w in self.work_items if w.item_type == ItemType.BREAK]

    def raw_windows(self) -> List[Dict]:
        return [w.to_window_dict() for w in self.work_items if w.item_type == ItemType.RAW]

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_windows(self, output_dir: str) -> Dict[str, str]:
        """Write customizer-ready JSON window files to *output_dir*.

        Returns a dict mapping window type → file path for each non-empty
        category.
        """
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(self.funscript_path))[0]
        written: Dict[str, str] = {}

        for type_name, windows in [
            ("performance", self.performance_windows()),
            ("break", self.break_windows()),
            ("raw", self.raw_windows()),
        ]:
            if windows:
                path = os.path.join(output_dir, f"{base}.{type_name}.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(windows, f, indent=2)
                written[type_name] = path

        return written

    def export_project(self, path: str) -> None:
        """Save the full project state to a JSON file."""
        data = {
            "funscript_path": self.funscript_path,
            "custom_name":    self.custom_name,
            "description":    self.description,
            "work_items":     [w.to_dict() for w in self.work_items],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load_project(cls, path: str) -> "Project":
        """Restore a project from a previously saved JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        project = cls(funscript_path=data.get("funscript_path", ""))
        project.custom_name  = data.get("custom_name", "")
        project.description  = data.get("description", "")
        project.work_items   = [
            WorkItem.from_dict(d) for d in data.get("work_items", [])
        ]
        return project

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Friendly display name derived from the funscript filename."""
        return os.path.splitext(os.path.basename(self.funscript_path))[0]

    @property
    def display_name(self) -> str:
        """User-defined name if set, else the filename-derived name."""
        return self.custom_name.strip() or self.name

    def auto_description(self) -> str:
        """Generate a one-sentence description from the assessment data."""
        if not self.assessment:
            return ""
        s = self.summary()
        duration = s.get("duration", "")
        bpm      = s.get("bpm", 0.0)
        phrases  = s.get("phrases", 0)
        patterns = s.get("patterns", 0)
        bpm_str  = f"{bpm:.0f} BPM" if bpm else ""
        parts = []
        if duration:
            parts.append(duration)
        if bpm_str:
            parts.append(bpm_str)
        if phrases:
            parts.append(f"{phrases} phrase{'s' if phrases != 1 else ''}")
        if patterns:
            parts.append(f"{patterns} pattern{'s' if patterns != 1 else ''}")
        return ", ".join(parts) + "." if parts else ""

    def get_description(self) -> str:
        """User description if set, else auto-generated from assessment."""
        return self.description.strip() or self.auto_description()

    @property
    def is_loaded(self) -> bool:
        return bool(self.funscript_path) and self.assessment is not None

    def summary(self) -> Dict:
        """Return a plain-dict summary suitable for display."""
        if not self.assessment:
            return {}
        ad = self.assessment.to_dict()
        meta = ad.get("meta", {})
        return {
            "name": self.name,
            "duration": meta.get("duration_ts", ""),
            "bpm": meta.get("bpm", 0.0),
            "actions": meta.get("action_count", 0),
            "phases": len(ad.get("phases", [])),
            "cycles": len(ad.get("cycles", [])),
            "patterns": len(ad.get("patterns", [])),
            "phrases": len(ad.get("phrases", [])),
            "bpm_transitions": len(ad.get("bpm_transitions", [])),
        }
