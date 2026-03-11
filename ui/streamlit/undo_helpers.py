# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Streamlit-aware undo/redo helpers.

Provides :func:`push_undo` (call before any mutating operation) and
:func:`apply_snapshot` (call after undo/redo to restore session state).

The pattern-editor keys that are snapshotted are those beginning with
``pe_splits_``, ``pe_transform_``, or ``pe_split_transform_``.
"""

from __future__ import annotations

from copy import deepcopy

import streamlit as st

from ui.common.undo_stack import Snapshot, UndoStack

_PE_PREFIXES = ("pe_splits_", "pe_transform_", "pe_split_transform_")


def push_undo(label: str) -> None:
    """Snapshot the current project + pattern-editor state onto the undo stack.

    Safe to call even before the stack is initialised (silently skips).
    Always call this *before* the mutating operation so the stack captures
    the state the user wants to return to.
    """
    undo_stack: UndoStack | None = st.session_state.get("undo_stack")
    if undo_stack is None:
        return

    pe_state = {
        k: deepcopy(v)
        for k, v in st.session_state.items()
        if any(k.startswith(pfx) for pfx in _PE_PREFIXES)
    }

    undo_stack.push(
        Snapshot(
            label=label,
            project=st.session_state.get("project"),
            pe_state=pe_state,
        )
    )
    # Mark the project as having unsaved changes (UX7).
    st.session_state["project_dirty"] = True


def apply_snapshot(snapshot: Snapshot) -> None:
    """Restore session state from *snapshot*.

    Replaces the project reference and rebuilds all pattern-editor keys.
    The caller must call ``st.rerun()`` after this.
    """
    st.session_state.project = snapshot.project

    # Remove existing pe_* keys then restore from snapshot.
    for k in list(st.session_state.keys()):
        if any(k.startswith(pfx) for pfx in _PE_PREFIXES):
            del st.session_state[k]

    for k, v in snapshot.pe_state.items():
        st.session_state[k] = deepcopy(v)
