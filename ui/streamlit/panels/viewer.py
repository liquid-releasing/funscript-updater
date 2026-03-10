# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""viewer.py — Phrase Selector panel.

Shows the full funscript as a fixed chart with phrase bounding boxes.

Interaction
-----------
* Click a point    — selects the enclosing phrase; shows phrase info below.
* Phrase buttons   — P1, P2, … below the chart jump directly to a phrase.
* Color toggle     — switch between velocity and amplitude colour mode.

Selected phrase info (start, end, duration, BPM, pattern, cycle count) is
displayed below.  A phrase editor will appear here in the next version.
"""

from __future__ import annotations

import json
from typing import List, Optional

import streamlit as st

from utils import ms_to_timestamp, parse_timestamp


# ------------------------------------------------------------------
# Selector fragment — the chart + controls as a Streamlit fragment so
# that scroll/zoom interactions rerun only this section of the page,
# not the entire app.  Phrase selection triggers a full app rerun via
# st.rerun(scope="app") to switch into phrase detail mode.
# ------------------------------------------------------------------

@st.fragment
def _selector_fragment(
    funscript_path: str,
    assessment_dict: dict,
    duration_ms: int,
    large_funscript_threshold: int,
) -> None:
    import json
    import time as _time
    from visualizations.chart_data import compute_chart_data, compute_annotation_bands
    from visualizations.funscript_chart import FunscriptChart

    view_state = st.session_state.view_state

    with open(funscript_path) as f:
        original_actions = json.load(f)["actions"]

    phrases = assessment_dict.get("phrases", [])
    bands   = compute_annotation_bands(assessment_dict)

    # Show edited version if any phrase transforms have been accepted
    from ui.streamlit.panels.phrase_detail import build_edited_actions
    has_edits = any(
        k.startswith("phrase_transform_")
        and st.session_state[k].get("transform_key", "passthrough") != "passthrough"
        for k in st.session_state
    )
    if has_edits:
        display_actions = build_edited_actions(phrases, original_actions)
        st.info(
            "These edits have not been saved — ready for export.",
            icon="💾",
        )
    else:
        display_actions = original_actions

    _render_controls(view_state, duration_ms, phrases)

    n_actions   = len(display_actions)
    spinner_msg = (
        f"Building chart ({n_actions} actions — using fast rendering)…"
        if n_actions > large_funscript_threshold
        else f"Building chart ({n_actions} actions)…"
    )
    _t0 = _time.time()
    with st.spinner(spinner_msg):
        series  = compute_chart_data(display_actions)
        chart   = FunscriptChart(
            series, bands, "", duration_ms,
            large_funscript_threshold=large_funscript_threshold,
        )
        _chart_v = st.session_state.get("phrase_sel_chart_instance", 0)
        ev = chart.render_streamlit(
            view_state, key=f"chart_phrase_sel_{_chart_v}", height=380
        )
    st.caption(f"Chart built in {_time.time() - _t0:.1f}s")
    _handle_chart_event(ev, view_state, phrases)

    _render_phrase_bar(phrases, view_state)


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def render(
    project,
    view_state,
    proposed_actions: Optional[List[dict]] = None,
    large_funscript_threshold: int = 10_000,
) -> None:
    """Render the Phrase Selector.

    Parameters
    ----------
    project:
        Loaded :class:`~ui.common.project.Project`.
    view_state:
        Shared :class:`~ui.common.view_state.ViewState`.
    proposed_actions:
        Reserved for future editing workflow.
    """
    if not project or not project.is_loaded:
        st.info("Load a funscript to use the Phrase Selector.")
        return

    from visualizations.funscript_chart import HAS_PLOTLY
    if not HAS_PLOTLY:
        st.error("plotly is required.  Run: pip install plotly")
        return

    assessment_dict = project.assessment.to_dict()
    phrases         = assessment_dict.get("phrases", [])
    duration_ms     = project.assessment.duration_ms

    # Ensure phrases are always shown even if view_state has them toggled off.
    view_state.show_phrases = True

    from ui.streamlit.panels import phrase_detail

    if view_state.has_selection():
        # ------------------------------------------------------------------
        # Detail mode: hide phrase selector, show only phrase detail panel
        # ------------------------------------------------------------------
        _render_phrase_info(view_state, phrases)
        from ui.streamlit.panels.media_player import render_player
        _sel_start = view_state.selection_start_ms or 0
        _sel_end   = view_state.selection_end_ms   or duration_ms
        with open(project.funscript_path, encoding="utf-8") as _fp:
            _all_acts = json.load(_fp).get("actions", [])
        _sel_acts = [a for a in _all_acts if _sel_start <= a["at"] <= _sel_end]
        render_player(
            start_ms=_sel_start,
            end_ms=_sel_end,
            actions=_sel_acts,
            key_suffix=f"viewer_{_sel_start}",
        )
        phrase_detail.render(
            phrases=phrases,
            view_state=view_state,
            duration_ms=duration_ms,
            bpm_threshold=st.session_state.get("bpm_threshold", 120.0),
        )
    else:
        # ------------------------------------------------------------------
        # Selector mode: chart + controls in a fragment so scroll/zoom
        # interactions don't flash the whole page.
        # ------------------------------------------------------------------
        _selector_fragment(
            funscript_path=project.funscript_path,
            assessment_dict=assessment_dict,
            duration_ms=duration_ms,
            large_funscript_threshold=large_funscript_threshold,
        )


# ------------------------------------------------------------------
# Controls bar
# ------------------------------------------------------------------

def _render_controls(view_state, duration_ms: int, phrases: list) -> None:
    """Colour mode + time range display + scroll/zoom controls."""
    zoom_start = view_state.zoom_start_ms or 0
    zoom_end   = view_state.zoom_end_ms   or duration_ms
    span       = zoom_end - zoom_start
    scroll_step = max(span // 3, 1_000)

    col_mode, col_t0, col_t1, col_left, col_right, col_all, col_zin, col_zout = st.columns(
        [2, 2, 2, 1, 1, 1, 1, 1]
    )

    with col_mode:
        view_state.color_mode = st.radio(
            "Color mode",
            ["velocity", "amplitude"],
            index=0 if view_state.color_mode == "velocity" else 1,
            horizontal=True,
            key="viewer_color_mode",
        )

    # Keys include the current zoom values so the widgets re-initialize
    # (with the correct default) whenever a scroll/zoom button changes the viewport.
    with col_t0:
        t0_val = st.text_input(
            "From", value=ms_to_timestamp(zoom_start),
            key=f"ctrl_t0_{zoom_start}",
            placeholder="M:SS",
        )

    with col_t1:
        t1_val = st.text_input(
            "To", value=ms_to_timestamp(zoom_end),
            key=f"ctrl_t1_{zoom_end}",
            placeholder="M:SS",
        )

    # Apply typed timestamps only if both parse cleanly and differ from current viewport.
    try:
        t0_ms = parse_timestamp(t0_val)
        t1_ms = parse_timestamp(t1_val)
        if t0_ms != zoom_start or t1_ms != zoom_end:
            view_state.set_zoom(t0_ms, t1_ms)
            st.rerun()   # fragment rerun — just updates the chart
    except Exception:
        pass

    with col_left:
        if st.button("◀", key="scroll_left", help="Scroll left", width="stretch"):
            new_start = max(0, zoom_start - scroll_step)
            view_state.set_zoom(new_start, new_start + span)
            st.rerun()   # fragment rerun

    with col_right:
        if st.button("▶", key="scroll_right", help="Scroll right", width="stretch"):
            new_end = min(duration_ms, zoom_end + scroll_step)
            view_state.set_zoom(new_end - span, new_end)
            st.rerun()   # fragment rerun

    with col_all:
        if st.button("All", key="reset_zoom", help="Show full funscript", width="stretch"):
            view_state.reset_zoom()
            st.rerun()   # fragment rerun

    with col_zin:
        if st.button("＋", key="zoom_in", help="Zoom in (halve window)", width="stretch"):
            mid  = (zoom_start + zoom_end) // 2
            half = max(span // 4, 5_000)
            view_state.set_zoom(max(0, mid - half), min(duration_ms, mid + half))
            st.rerun()   # fragment rerun

    with col_zout:
        if st.button("－", key="zoom_out", help="Zoom out (double window)", width="stretch"):
            mid  = (zoom_start + zoom_end) // 2
            half = min(span, duration_ms)
            view_state.set_zoom(max(0, mid - half), min(duration_ms, mid + half))
            st.rerun()   # fragment rerun


# ------------------------------------------------------------------
# Chart event handling
# ------------------------------------------------------------------

def _handle_chart_event(event, view_state, phrases: list) -> None:
    """Map a Plotly point-click or box-select event to a ViewState update."""
    if not event:
        return
    sel = getattr(event, "selection", None)
    if not sel:
        return

    # Single-point click → select enclosing phrase
    points = getattr(sel, "points", [])
    if points:
        x = points[0].get("x")
        if x is not None:
            phrase = _find_phrase_at(int(x), phrases)
            if phrase:
                _select_phrase(phrase, view_state)
                st.rerun(scope="app")   # full rerun → switches to detail mode
        return

    # Box drag → manual time range selection
    box = getattr(sel, "box", None) or []
    if box:
        try:
            x_range = box[0].get("x", [])
            if len(x_range) == 2:
                view_state.set_selection(int(x_range[0]), int(x_range[1]))
                st.rerun(scope="app")   # full rerun
        except Exception:
            pass


# ------------------------------------------------------------------
# Phrase table
# ------------------------------------------------------------------

def _render_phrase_bar(phrases: list, view_state) -> None:
    """Per-row table of all phrases with an Edit button on each row."""
    if not phrases:
        return

    from assessment.classifier import TAGS

    st.caption(
        f"{len(phrases)} phrase{'s' if len(phrases) != 1 else ''} — "
        "click a phrase on the chart above or use the Edit buttons below"
    )

    _col_w = [0.5, 3.0, 1.2, 1.0, 3.0, 1.2, 1.5]
    hcols = st.columns(_col_w)
    for h, lbl in zip(hcols, ["#", "Time", "Dur", "BPM", "Behavior", "Cycles", ""]):
        h.caption(lbl)

    for i, ph in enumerate(phrases):
        start   = ph["start_ms"]
        end     = ph["end_ms"]
        dur_ms  = end - start
        bpm     = ph.get("bpm", 0.0)
        cycles  = ph.get("cycle_count", "—")
        raw_tags = ph.get("tags", []) or []

        # Behavior: prefer human tag labels, fall back to pattern_label
        if raw_tags:
            behavior = ", ".join(TAGS[t].label if t in TAGS else t for t in raw_tags)
        else:
            behavior = (ph.get("pattern_label", "") or "—").replace("->", "→")

        time_str = f"{ms_to_timestamp(start)} → {ms_to_timestamp(end)}"
        dur_str  = ms_to_timestamp(max(0, dur_ms))

        is_sel = (
            view_state.has_selection()
            and view_state.selection_start_ms == start
            and view_state.selection_end_ms   == end
        )

        rc = st.columns(_col_w)
        rc[0].markdown(
            f'<span style="white-space:nowrap">{"◆ " if is_sel else ""}{i + 1}</span>',
            unsafe_allow_html=True,
        )
        rc[1].write(time_str)
        rc[2].write(dur_str)
        rc[3].write(f"{bpm:.1f}")
        rc[4].write(behavior)
        rc[5].write(str(cycles))
        if rc[6].button("✏", key=f"phrase_btn_{i}", type="primary" if is_sel else "secondary", help="Edit phrase"):
            _select_phrase(ph, view_state)
            st.rerun(scope="app")


# ------------------------------------------------------------------
# Selected phrase info panel
# ------------------------------------------------------------------

def _render_phrase_info(view_state, phrases: list) -> None:
    """Show a compact table row for the selected phrase."""
    start = view_state.selection_start_ms
    end   = view_state.selection_end_ms

    phrase_idx = next(
        (i for i, ph in enumerate(phrases)
         if ph["start_ms"] == start and ph["end_ms"] == end),
        None,
    )
    if phrase_idx is None:
        return
    phrase = phrases[phrase_idx]

    duration_ms = end - start
    col_label, col_a, col_b = st.columns([1, 10, 1])
    with col_label:
        st.markdown(f"### P{phrase_idx + 1}")
    with col_a:
        import pandas as pd
        from assessment.classifier import TAGS
        raw_tags = phrase.get("tags") or []
        if raw_tags:
            behavior = ", ".join(TAGS[t].label if t in TAGS else t for t in raw_tags)
        else:
            behavior = (phrase.get("pattern_label") or "—").replace("->", "→")
        row = {
            "Start":    ms_to_timestamp(start),
            "End":      ms_to_timestamp(end),
            "Duration": f"{duration_ms / 1000:.1f} s",
            "BPM":      f"{phrase.get('bpm', 0):.1f}",
            "Behavior": behavior,
            "Cycles":   phrase.get("cycle_count", "—"),
        }
        st.dataframe(pd.DataFrame([row]), hide_index=True, width="stretch")
    with col_b:
        if st.button("✕", key="clear_sel", help="Clear selection"):
            view_state.clear_selection()
            st.rerun()


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def _find_phrase_at(time_ms: int, phrases: list):
    for ph in phrases:
        if ph["start_ms"] <= time_ms <= ph["end_ms"]:
            return ph
    return None


def _select_phrase(phrase: dict, view_state) -> None:
    view_state.set_selection(phrase["start_ms"], phrase["end_ms"])


def _zoom_to_phrase(phrase: dict, view_state, duration_ms: int) -> None:
    """Scroll the viewport to show the phrase with a small padding on each side."""
    start = phrase["start_ms"]
    end   = phrase["end_ms"]
    pad   = max((end - start) // 5, 2_000)
    view_state.set_zoom(max(0, start - pad), min(duration_ms, end + pad))
