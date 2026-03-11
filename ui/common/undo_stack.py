# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Undo/redo stack for FunscriptForge session state.

Framework-agnostic: holds snapshots of project + pattern-editor state.
The Streamlit layer is responsible for reading/writing session state.

Usage::

    from ui.common.undo_stack import UndoStack, Snapshot

    stack = UndoStack(max_size=50)

    # Push before a mutating operation
    stack.push(Snapshot(label="Add split at 1:23", project=proj, pe_state={...}))

    # Undo
    if stack.can_undo:
        snap = stack.undo()   # returns the state to restore
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.common.project import Project


@dataclass
class Snapshot:
    """A point-in-time capture of mutable session state."""

    label: str
    project: "Project | None"
    # Deep copy of all pe_splits_*, pe_transform_*, pe_split_transform_* keys.
    pe_state: dict = field(default_factory=dict)


class UndoStack:
    """Fixed-capacity undo/redo stack (LIFO with redo branch).

    The stack stores *Snapshot* objects.  Position *_pos* points to the
    snapshot that represents the **current** state.  Undoing moves *_pos*
    backwards; redoing moves it forwards.  Pushing a new snapshot after an
    undo discards the redo branch (standard behaviour).
    """

    def __init__(self, max_size: int = 50) -> None:
        self._snapshots: list[Snapshot] = []
        self._pos: int = -1
        self._max_size = max_size

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def push(self, snapshot: Snapshot) -> None:
        """Push *snapshot* as the new current state, discarding any redo branch."""
        # Drop everything after the current position (redo branch).
        self._snapshots = self._snapshots[: self._pos + 1]
        self._snapshots.append(snapshot)

        if len(self._snapshots) > self._max_size:
            # Trim oldest entry; position stays the same (we removed from front).
            self._snapshots.pop(0)
        else:
            self._pos += 1

    # ------------------------------------------------------------------
    # Navigation — return the Snapshot to restore, or None
    # ------------------------------------------------------------------

    def undo(self) -> Snapshot | None:
        """Step back one position and return the *previous* snapshot to restore."""
        if not self.can_undo:
            return None
        self._pos -= 1
        return self._snapshots[self._pos]

    def redo(self) -> Snapshot | None:
        """Step forward one position and return the *next* snapshot to restore."""
        if not self.can_redo:
            return None
        self._pos += 1
        return self._snapshots[self._pos]

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        return self._pos > 0

    @property
    def can_redo(self) -> bool:
        return self._pos < len(self._snapshots) - 1

    @property
    def undo_label(self) -> str | None:
        """Label of the operation that would be undone (current snapshot)."""
        if self.can_undo:
            return self._snapshots[self._pos].label
        return None

    @property
    def redo_label(self) -> str | None:
        """Label of the operation that would be redone (next snapshot)."""
        if self.can_redo:
            return self._snapshots[self._pos + 1].label
        return None

    @property
    def size(self) -> int:
        return len(self._snapshots)
