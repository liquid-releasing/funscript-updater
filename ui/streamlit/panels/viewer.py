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

from typing import List, Optional

from utils import ms_to_timestamp, parse_timestamp


def render(project, view_state, proposed_actions: Optional[List[dict]] = None, large_funscript_threshold: int = 10_000) -> None:
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
    import streamlit as st

    if not project or not project.is_loaded:
        st.info("Load a funscript to use the Phrase Selector.")
        return

    from visualizations.chart_data import compute_chart_data, compute_annotation_bands
    from visualizations.funscript_chart import FunscriptChart, HAS_PLOTLY

    if not HAS_PLOTLY:
        st.error("plotly is required.  Run: pip install plotly")
        return

    import json
    with open(project.funscript_path) as f:
        _raw = json.load(f)
    original_actions = _raw["actions"]

    assessment_dict = project.assessment.to_dict()
    phrases         = assessment_dict.get("phrases", [])
    bands           = compute_annotation_bands(assessment_dict)
    duration_ms     = project.assessment.duration_ms

    # Ensure phrases are always shown even if view_state has them toggled off.
    view_state.show_phrases = True

    # ------------------------------------------------------------------
    # Controls: colour mode + scroll/zoom
    # ------------------------------------------------------------------
    _render_controls(view_state, duration_ms, phrases)

    # ------------------------------------------------------------------
    # Phrase Selector chart — full width, pan mode
    # ------------------------------------------------------------------
    import time as _time
    n_actions = len(original_actions)
    spinner_msg = (
        f"Building chart ({n_actions} actions — using fast rendering)…"
        if n_actions > large_funscript_threshold
        else f"Building chart ({n_actions} actions)…"
    )
    _t0 = _time.time()
    with st.spinner(spinner_msg):
        series = compute_chart_data(original_actions)
        chart  = FunscriptChart(series, bands, "", duration_ms, large_funscript_threshold=large_funscript_threshold)
        ev     = chart.render_streamlit(view_state, key="chart_phrase_sel", height=380)
    st.caption(f"Chart built in {_time.time() - _t0:.1f}s")
    _handle_chart_event(ev, view_state, phrases)

    # ------------------------------------------------------------------
    # Phrase quick-jump buttons
    # ------------------------------------------------------------------
    _render_phrase_bar(phrases, view_state)

    # ------------------------------------------------------------------
    # Selected phrase info + detail panel
    # ------------------------------------------------------------------
    if view_state.has_selection():
        _render_phrase_info(view_state, phrases)
        from ui.streamlit.panels import phrase_detail
        phrase_detail.render(
            phrases=phrases,
            original_actions=original_actions,
            view_state=view_state,
            duration_ms=duration_ms,
            bpm_threshold=st.session_state.get("bpm_threshold", 120.0),
        )


# ------------------------------------------------------------------
# Controls bar
# ------------------------------------------------------------------

def _render_controls(view_state, duration_ms: int, phrases: list) -> None:
    """Colour mode + time range display + scroll/zoom controls."""
    import streamlit as st

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
            label_visibility="collapsed",
        )

    # Keys include the current zoom values so the widgets re-initialize
    # (with the correct default) whenever a scroll/zoom button changes the viewport.
    with col_t0:
        t0_val = st.text_input(
            "From", value=ms_to_timestamp(zoom_start),
            key=f"ctrl_t0_{zoom_start}",
            label_visibility="collapsed",
            placeholder="M:SS",
        )

    with col_t1:
        t1_val = st.text_input(
            "To", value=ms_to_timestamp(zoom_end),
            key=f"ctrl_t1_{zoom_end}",
            label_visibility="collapsed",
            placeholder="M:SS",
        )

    # Apply typed timestamps only if both parse cleanly and differ from current viewport.
    try:
        t0_ms = parse_timestamp(t0_val)
        t1_ms = parse_timestamp(t1_val)
        if t0_ms != zoom_start or t1_ms != zoom_end:
            view_state.set_zoom(t0_ms, t1_ms)
            st.rerun()
    except Exception:
        pass

    with col_left:
        if st.button("◀", key="scroll_left", help="Scroll left", use_container_width=True):
            new_start = max(0, zoom_start - scroll_step)
            view_state.set_zoom(new_start, new_start + span)
            st.rerun()

    with col_right:
        if st.button("▶", key="scroll_right", help="Scroll right", use_container_width=True):
            new_end = min(duration_ms, zoom_end + scroll_step)
            view_state.set_zoom(new_end - span, new_end)
            st.rerun()

    with col_all:
        if st.button("All", key="reset_zoom", help="Show full funscript", use_container_width=True):
            view_state.reset_zoom()
            st.rerun()

    with col_zin:
        if st.button("＋", key="zoom_in", help="Zoom in (halve window)", use_container_width=True):
            mid  = (zoom_start + zoom_end) // 2
            half = max(span // 4, 5_000)
            view_state.set_zoom(max(0, mid - half), min(duration_ms, mid + half))
            st.rerun()

    with col_zout:
        if st.button("－", key="zoom_out", help="Zoom out (double window)", use_container_width=True):
            mid  = (zoom_start + zoom_end) // 2
            half = min(span, duration_ms)
            view_state.set_zoom(max(0, mid - half), min(duration_ms, mid + half))
            st.rerun()


# ------------------------------------------------------------------
# Chart event handling
# ------------------------------------------------------------------

def _handle_chart_event(event, view_state, phrases: list) -> None:
    """Map a Plotly point-click or box-select event to a ViewState update."""
    import streamlit as st

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
                st.rerun()
        return

    # Box drag → manual time range selection
    box = getattr(sel, "box", None) or []
    if box:
        try:
            x_range = box[0].get("x", [])
            if len(x_range) == 2:
                view_state.set_selection(int(x_range[0]), int(x_range[1]))
                st.rerun()
        except Exception:
            pass


# ------------------------------------------------------------------
# Phrase quick-jump bar
# ------------------------------------------------------------------

def _render_phrase_bar(phrases: list, view_state) -> None:
    """A numbered button for each phrase; clicking selects it."""
    import streamlit as st

    if not phrases:
        return

    st.caption(
        f"{len(phrases)} phrase{'s' if len(phrases) != 1 else ''} — "
        "click a phrase on the chart or use the buttons below"
    )

    chunk_size = 10
    chunks = [phrases[i:i + chunk_size] for i in range(0, len(phrases), chunk_size)]
    for row_idx, chunk in enumerate(chunks):
        cols = st.columns(len(chunk))
        for col_idx, ph in enumerate(chunk):
            idx   = row_idx * chunk_size + col_idx
            start = ph["start_ms"]
            end   = ph["end_ms"]
            is_sel = (
                view_state.has_selection()
                and view_state.selection_start_ms == start
                and view_state.selection_end_ms   == end
            )
            label = f"◆ P{idx + 1}" if is_sel else f"P{idx + 1}"
            tip   = (
                f"{ms_to_timestamp(start)} — {ms_to_timestamp(end)}\n"
                f"{ph.get('bpm', 0):.0f} BPM  ·  {ph.get('pattern_label', '')}"
            )
            with cols[col_idx]:
                if st.button(label, key=f"phrase_btn_{idx}", help=tip):
                    _select_phrase(ph, view_state)
                    st.rerun()


# ------------------------------------------------------------------
# Selected phrase info panel
# ------------------------------------------------------------------

def _render_phrase_info(view_state, phrases: list) -> None:
    """Show a compact table row for the selected phrase."""
    import streamlit as st

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
        row = {
            "Start":    ms_to_timestamp(start),
            "End":      ms_to_timestamp(end),
            "Duration": f"{duration_ms / 1000:.1f} s",
            "BPM":      f"{phrase.get('bpm', 0):.1f}",
            "Pattern":  phrase.get("pattern_label", "—"),
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
