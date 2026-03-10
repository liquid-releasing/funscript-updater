# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Work items panel — review and track phrase editing tasks.

Each work item corresponds to a time window (phrase) from the assessment.
Status cycles through To Do → In Progress → Done.
The Edit button zooms the Phrase Editor to that time range.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from ui.common.project import Project


from dataclasses import dataclass as _dataclass


@_dataclass(frozen=True)
class _StatusInfo:
    label: str
    color: str


# Single source of truth — order defines the selectbox order.
_STATUSES: dict = {
    "todo":        _StatusInfo("To Do",       "#3a3a3a"),
    "in_progress": _StatusInfo("In Progress", "#1d4e89"),
    "done":        _StatusInfo("Done",        "#2d6a4f"),
}

_STATUS_OPTIONS = [s.label for s in _STATUSES.values()]
_STATUS_KEYS    = list(_STATUSES.keys())


def render(project: "Project") -> None:
    if not project.is_loaded:
        st.info("Load a funscript to see work items.")
        return

    if not project.work_items:
        st.warning(
            "No work items — save phrases from the Assessment tab "
            "using the Save button on any phrase row."
        )
        return

    n_total = len(project.work_items)
    n_done  = sum(1 for w in project.work_items if w.status == "done")
    st.subheader(f"Work items  ({n_done}/{n_total} done)")

    if n_done == n_total:
        st.success("All work items completed.")
    elif n_done > 0:
        st.progress(n_done / n_total, text=f"{n_done} of {n_total} done")

    st.divider()

    for item in project.work_items:
        _render_item_row(project, item)


def _render_item_row(project: "Project", item) -> None:
    color   = _STATUSES[item.status].color
    opacity = "0.55" if item.status == "done" else "1.0"

    with st.container():
        st.markdown(
            f'<div style="border-left:3px solid {color};padding-left:8px;'
            f'margin-bottom:4px;opacity:{opacity}">',
            unsafe_allow_html=True,
        )

        col_time, col_bpm, col_status, col_edit = st.columns([3.5, 1.5, 2.5, 1.0])

        # Time range + label
        col_time.caption(f"{item.start_ts}  →  {item.end_ts}")
        if item.label:
            col_time.markdown(f"*{item.label[:50]}*")

        # BPM
        if item.bpm > 0:
            col_bpm.metric("BPM", f"{item.bpm:.1f}")
        else:
            col_bpm.write("—")

        # Status dropdown
        current_label = _STATUSES.get(item.status, _StatusInfo("To Do", "#3a3a3a")).label
        new_label = col_status.selectbox(
            "Status",
            options=_STATUS_OPTIONS,
            index=_STATUS_OPTIONS.index(current_label),
            key=f"status_{item.id}",
        )
        new_status = _STATUS_KEYS[_STATUS_OPTIONS.index(new_label)]
        if new_status != item.status:
            project.set_item_status(item.id, new_status)
            st.rerun()

        # Edit button → select phrase in Phrase Editor and navigate there
        if col_edit.button("✏", key=f"edit_{item.id}", width="stretch", help="Edit in Phrase Editor"):
            st.session_state.view_state.set_selection(item.start_ms, item.end_ms)
            # Auto-advance status to In Progress if still To Do
            if item.status == "todo":
                project.set_item_status(item.id, "in_progress")
            st.session_state.goto_tab = 0
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
