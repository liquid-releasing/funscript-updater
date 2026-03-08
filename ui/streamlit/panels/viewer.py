"""viewer.py — Three-panel synchronised funscript viewer.

Shows three versions of the same funscript side-by-side (or stacked):
  Original   — the source file, never modified
  Proposed   — working scratch space; patterns are applied here
  Committed  — becomes the new canonical version after each commit

All panels share the same ViewState (zoom window, selection range,
colour mode, annotation toggles).

Committing
----------
When the user presses "Commit", the proposed actions replace the
current actions in the Project, the assessment is re-run, and the
UI rebuilds.
"""

from __future__ import annotations

import copy
from typing import List, Optional

from utils import ms_to_timestamp, parse_timestamp


def render(project, view_state, proposed_actions: Optional[List[dict]] = None) -> Optional[List[dict]]:
    """Render the three-panel viewer.

    Parameters
    ----------
    project:
        Loaded :class:`~ui.common.project.Project`.
    view_state:
        Shared :class:`~ui.common.view_state.ViewState`.
    proposed_actions:
        If None, proposed panel shows the original (no changes yet).

    Returns
    -------
    Optional[List[dict]]
        If the user pressed "Commit", returns the committed action list
        so the caller can update the project.  Otherwise returns None.
    """
    import streamlit as st

    if not project or not project.is_loaded:
        st.info("Load a funscript to use the viewer.")
        return None

    from visualizations.chart_data import compute_chart_data, compute_annotation_bands
    from visualizations.funscript_chart import FunscriptChart, HAS_PLOTLY

    if not HAS_PLOTLY:
        st.error("plotly is required for the viewer. Run: pip install plotly")
        return None

    assessment_dict = project.assessment.to_dict()
    original_actions = project.assessment  # we read from the source file separately
    # Get the actual original actions from the project's funscript data
    import json
    with open(project.funscript_path) as f:
        _raw = json.load(f)
    original_actions = _raw["actions"]

    if proposed_actions is None:
        proposed_actions = copy.deepcopy(original_actions)

    # Committed = original until the user has committed at least once
    committed_actions = original_actions

    bands = compute_annotation_bands(assessment_dict)
    duration_ms = project.assessment.duration_ms

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------
    _render_toolbar(view_state, duration_ms)

    # ------------------------------------------------------------------
    # Zoom / selection controls
    # ------------------------------------------------------------------
    committed = _render_zoom_controls(view_state, duration_ms)

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------
    orig_series  = compute_chart_data(original_actions)
    prop_series  = compute_chart_data(proposed_actions)
    comm_series  = compute_chart_data(committed_actions)

    chart_height = 220

    orig_chart = FunscriptChart(orig_series, bands, "Original",  duration_ms)
    prop_chart = FunscriptChart(prop_series, bands, "Proposed",  duration_ms)
    comm_chart = FunscriptChart(comm_series, bands, "Committed", duration_ms)

    # Stack panels vertically so patterns are easy to compare across the same time axis
    ev = orig_chart.render_streamlit(view_state, key="chart_orig", height=chart_height)
    _handle_chart_selection(ev, view_state)
    prop_chart.render_streamlit(view_state, key="chart_prop", height=chart_height)
    comm_chart.render_streamlit(view_state, key="chart_comm", height=chart_height)

    # ------------------------------------------------------------------
    # Commit bar
    # ------------------------------------------------------------------
    return _render_commit_bar(proposed_actions, original_actions, view_state)


# ------------------------------------------------------------------
# Sub-renderers
# ------------------------------------------------------------------

def _render_toolbar(view_state, duration_ms: int) -> None:
    import streamlit as st

    with st.expander("Display options", expanded=True):
        col1, col2 = st.columns([2, 3])
        with col1:
            view_state.color_mode = st.radio(
                "Colour mode",
                ["velocity", "amplitude"],
                index=0 if view_state.color_mode == "velocity" else 1,
                horizontal=True,
                key="viewer_color_mode",
            )
        with col2:
            st.markdown("**Annotations**")
            ann_col1, ann_col2, ann_col3 = st.columns(3)
            with ann_col1:
                view_state.show_phrases     = st.checkbox("Phrases",     view_state.show_phrases,     key="ann_phrases")
            with ann_col2:
                view_state.show_transitions = st.checkbox("Transitions", view_state.show_transitions, key="ann_trans")
            with ann_col3:
                view_state.show_patterns = st.checkbox("Patterns", view_state.show_patterns, key="ann_patterns")


def _render_zoom_controls(view_state, duration_ms: int) -> None:
    import streamlit as st

    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        z_start = st.text_input(
            "Zoom start",
            value=ms_to_timestamp(view_state.zoom_start_ms or 0),
            key="zoom_start_input",
            placeholder="HH:MM:SS.mmm",
        )
    with col2:
        z_end = st.text_input(
            "Zoom end",
            value=ms_to_timestamp(view_state.zoom_end_ms or duration_ms),
            key="zoom_end_input",
            placeholder="HH:MM:SS.mmm",
        )
    with col3:
        if st.button("Apply zoom", key="apply_zoom"):
            try:
                s = parse_timestamp(z_start)
                e = parse_timestamp(z_end)
                view_state.set_zoom(s, e)
                st.rerun()
            except Exception:
                st.error("Invalid timestamp format.")
    with col4:
        if st.button("Reset zoom", key="reset_zoom"):
            view_state.reset_zoom()
            view_state.clear_selection()
            st.rerun()


def _handle_chart_selection(event, view_state) -> None:
    """Translate a Plotly box-select event into a ViewState selection."""
    import streamlit as st

    if not event:
        return
    sel = getattr(event, "selection", None)
    if not sel:
        return
    box = getattr(sel, "box", None) or []
    if not box:
        return
    try:
        x_range = box[0].get("x", [])
        if len(x_range) == 2:
            s, e = int(x_range[0]), int(x_range[1])
            view_state.set_selection(s, e)
            st.rerun()
    except Exception:
        pass


def _render_commit_bar(
    proposed_actions: List[dict],
    original_actions: List[dict],
    view_state,
) -> Optional[List[dict]]:
    import streamlit as st

    st.divider()
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        if view_state.has_selection():
            s = ms_to_timestamp(view_state.selection_start_ms)
            e = ms_to_timestamp(view_state.selection_end_ms)
            st.caption(f"Selection: {s} — {e}")
        else:
            st.caption("No selection active.")
    with col2:
        if st.button("Discard proposed", key="discard_proposed"):
            view_state.clear_selection()
            st.rerun()
    with col3:
        if st.button("Commit", type="primary", key="commit_proposed"):
            return proposed_actions
    return None
