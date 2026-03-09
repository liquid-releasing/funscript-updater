"""Work items panel — the main interactive workspace.

Shows all time-window work items in a scrollable list.  Each row lets the
user classify the section (performance / break / raw / neutral) and select
it for further editing in the detail panel.

State mutations (type changes, selection) are written back to
``st.session_state.project`` so all panels stay in sync.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from ui.common.work_items import ItemType

if TYPE_CHECKING:
    from ui.common.project import Project


# Display colours per item type (background for the row badge).
_TYPE_COLORS = {
    ItemType.PERFORMANCE: "#2d6a4f",   # green
    ItemType.BREAK: "#1d3557",         # navy blue
    ItemType.RAW: "#7b2d00",           # burnt orange
    ItemType.NEUTRAL: "#3a3a3a",       # dark grey
}

_TYPE_LABELS = {
    ItemType.PERFORMANCE: "Performance",
    ItemType.BREAK: "Break",
    ItemType.RAW: "Raw",
    ItemType.NEUTRAL: "Neutral",
}

_TYPE_ICONS = {
    ItemType.PERFORMANCE: "🔥",
    ItemType.BREAK: "🌊",
    ItemType.RAW: "🎯",
    ItemType.NEUTRAL: "⚪",
}


def render(project: "Project") -> None:
    """Render the work items panel for *project*.

    Writes ``st.session_state.project.selected_item_id`` when an item
    is clicked.
    """
    if not project.is_loaded:
        st.info("Load a funscript to see work items.")
        return

    if not project.work_items:
        st.warning("No work items — select phrases in the Assessment tab and click 'Add to Work Items'.")
        return

    n_total = len(project.work_items)
    n_done  = sum(1 for w in project.work_items if w.completed)
    st.subheader(f"Work items  ({n_done}/{n_total} done)")

    if n_done == n_total:
        st.success("All work items completed.")
    elif n_done > 0:
        st.progress(n_done / n_total, text=f"{n_done} of {n_total} completed")

    _render_legend()
    st.divider()

    for item in project.work_items:
        _render_item_row(project, item)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _render_legend() -> None:
    cols = st.columns(len(_TYPE_LABELS))
    for col, (itype, label) in zip(cols, _TYPE_LABELS.items()):
        color = _TYPE_COLORS[itype]
        icon = _TYPE_ICONS[itype]
        col.markdown(
            f'<span style="background:{color};padding:2px 8px;border-radius:4px;'
            f'font-size:12px;color:white">{icon} {label}</span>',
            unsafe_allow_html=True,
        )


def _render_item_row(project: "Project", item) -> None:
    color = _TYPE_COLORS[item.item_type]
    icon = _TYPE_ICONS[item.item_type]
    is_selected = project.selected_item_id == item.id

    # Dim completed rows slightly
    opacity = "0.55" if item.completed else "1.0"
    border  = "2px solid #f0c040" if is_selected else f"2px solid {color}"
    with st.container():
        st.markdown(
            f'<div style="border-left:{border};padding-left:8px;margin-bottom:2px;opacity:{opacity}">',
            unsafe_allow_html=True,
        )

        col_done, col_badge, col_time, col_bpm, col_type, col_edit = st.columns([0.5, 1, 3, 2, 3, 1])

        # Completion toggle
        done_label = "✓" if item.completed else "◻"
        done_help  = "Mark incomplete" if item.completed else "Mark as done"
        if col_done.button(
            done_label,
            key=f"done_{item.id}",
            help=done_help,
            use_container_width=True,
        ):
            project.set_item_completed(item.id, not item.completed)
            st.rerun()

        # Type badge.
        col_badge.markdown(
            f'<span style="background:{color};padding:2px 6px;border-radius:4px;'
            f'font-size:12px;color:white">{icon}</span>',
            unsafe_allow_html=True,
        )

        # Time range.
        col_time.caption(f"{item.start_ts}  →  {item.end_ts}")
        dur_s = item.duration_ms / 1000
        col_time.markdown(f"*{dur_s:.1f} s*")

        # BPM info.
        if item.bpm > 0:
            col_bpm.metric("BPM", f"{item.bpm:.1f}", label_visibility="collapsed")
        else:
            col_bpm.write("—")

        # Type selector (key must be unique per item).
        options = list(_TYPE_LABELS.values())
        current_idx = options.index(_TYPE_LABELS[item.item_type])
        new_label = col_type.selectbox(
            "Type",
            options=options,
            index=current_idx,
            key=f"type_{item.id}",
            label_visibility="collapsed",
        )
        new_type = _label_to_type(new_label)
        if new_type != item.item_type:
            project.set_item_type(item.id, new_type)
            st.rerun()

        # Edit button selects this item.
        if col_edit.button("Edit", key=f"edit_{item.id}", type="primary" if is_selected else "secondary"):
            project.selected_item_id = item.id
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def _label_to_type(label: str) -> ItemType:
    for itype, lbl in _TYPE_LABELS.items():
        if lbl == label:
            return itype
    return ItemType.NEUTRAL
