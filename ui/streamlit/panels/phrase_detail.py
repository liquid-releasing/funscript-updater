"""phrase_detail.py — Detailed view for a selected phrase.

Layout (when a phrase is selected)
------------------------------------
  ┌─────────────────────────────────┬──────────────┐
  │  P{N} — Phrase Detail           │              │
  │  Original chart (fixed x-axis)  │  Transform   │
  ├─────────────────────────────────│  controls    │
  │  Preview — {Transform Name}     │              │
  │  Preview chart (fixed x-axis)   │  ⏮ Prev  Next ⏭ │
  │                                 │  💾 Save  ✕ Cancel │
  └─────────────────────────────────┴──────────────┘

Both charts share the same fixed-width x-axis viewport (centered on the
selected phrase, sized to show the longest phrase in the funscript so that
BPM and velocity are visually comparable across all phrase views).

Areas outside the selected phrase are dimmed with a semi-transparent overlay
so context is visible but focus stays on the phrase being edited.

Navigation and Save/Cancel buttons live at the bottom-right.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def render(
    phrases: list,
    original_actions: list,
    view_state,
    duration_ms: int,
    bpm_threshold: float = 120.0,
) -> None:
    import streamlit as st

    if not view_state.has_selection():
        return

    sel_start  = view_state.selection_start_ms
    sel_end    = view_state.selection_end_ms
    phrase_idx = next(
        (i for i, ph in enumerate(phrases)
         if ph["start_ms"] == sel_start and ph["end_ms"] == sel_end),
        None,
    )
    if phrase_idx is None:
        return

    phrase = phrases[phrase_idx]

    st.divider()

    # ------------------------------------------------------------------
    # Fixed viewport: sized to the longest phrase + padding so all phrase
    # detail views share the same time-scale (velocity is comparable).
    # ------------------------------------------------------------------
    win_start, win_end = _fixed_viewport(phrases, phrase, duration_ms)

    # ------------------------------------------------------------------
    # Resolve current transform selection (from session state or default)
    # ------------------------------------------------------------------
    from suggested_updates.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

    transform_state = st.session_state.get(f"phrase_transform_{phrase_idx}", {})
    transform_key   = transform_state.get("transform_key", suggest_transform(phrase, bpm_threshold))
    param_values    = transform_state.get("param_values", {})
    spec = TRANSFORM_CATALOG.get(transform_key, TRANSFORM_CATALOG["passthrough"])

    preview_actions = _apply_transform_to_window(original_actions, phrase, spec, param_values)

    # ------------------------------------------------------------------
    # Two-column layout: charts (left 3) | controls + nav (right 1)
    # ------------------------------------------------------------------
    col_charts, col_right = st.columns([3, 1])

    with col_charts:
        # --- Original chart ---
        st.subheader(f"P{phrase_idx + 1} — Phrase Detail")
        _render_chart(
            actions=original_actions,
            phrases=phrases,
            phrase_idx=phrase_idx,
            win_start=win_start,
            win_end=win_end,
            view_state=view_state,
            chart_key=f"detail_orig_{phrase_idx}_{win_start}",
        )

        # --- Preview chart ---
        st.subheader(f"Preview — {spec.name}")
        _render_chart(
            actions=preview_actions,
            phrases=phrases,
            phrase_idx=phrase_idx,
            win_start=win_start,
            win_end=win_end,
            view_state=view_state,
            chart_key=f"detail_prev_{phrase_idx}_{win_start}_{transform_key}",
        )
        st.caption("*(not saved)*")

    with col_right:
        # --- Transform controls (top) ---
        _render_transform_controls(phrase, bpm_threshold, phrase_idx)

        # --- Prev / Next navigation ---
        st.write("")
        st.write("")
        _render_nav_buttons(phrases, phrase_idx, view_state, duration_ms)

        # --- Save / Cancel ---
        st.write("")
        _render_save_cancel(phrases, original_actions, view_state)


# ------------------------------------------------------------------
# Fixed viewport calculation
# ------------------------------------------------------------------

def _fixed_viewport(phrases: list, phrase: dict, duration_ms: int):
    """Return (win_start, win_end) that is the same width for all phrases.

    Width = longest phrase duration + padding on each side, so that BPM
    and stroke velocity are visually comparable across phrase detail views.
    """
    max_phrase_dur = max(
        (ph["end_ms"] - ph["start_ms"]) for ph in phrases
    ) if phrases else 60_000

    # Padding: at least 10 s each side, or one-third of the longest phrase
    side_pad = max(max_phrase_dur // 3, 10_000)
    half_win = max_phrase_dur // 2 + side_pad

    phrase_center = (phrase["start_ms"] + phrase["end_ms"]) // 2
    win_start = max(0, phrase_center - half_win)
    win_end   = min(duration_ms, phrase_center + half_win)

    # If we hit an edge, keep the window the same total width
    total_width = 2 * half_win
    if win_start == 0 and win_end < total_width:
        win_end = min(duration_ms, total_width)
    if win_end == duration_ms and (win_end - win_start) < total_width:
        win_start = max(0, duration_ms - total_width)

    return win_start, win_end


# ------------------------------------------------------------------
# Chart renderer (fixed viewport, no modebar, dimmed outside phrase)
# ------------------------------------------------------------------

def _render_chart(
    actions: list,
    phrases: list,
    phrase_idx: int,
    win_start: int,
    win_end: int,
    view_state,
    chart_key: str,
) -> None:
    import streamlit as st
    from visualizations.chart_data import (
        compute_chart_data, compute_annotation_bands,
        slice_series, slice_bands,
    )
    from visualizations.funscript_chart import FunscriptChart

    sel_phrase = phrases[phrase_idx]
    s = slice_series(compute_chart_data(actions), win_start, win_end)

    assessment_stub = {
        "phrases": phrases, "phases": [], "cycles": [],
        "patterns": [], "bpm_transitions": [],
    }
    visible_bands = slice_bands(compute_annotation_bands(assessment_stub), win_start, win_end)

    chart = FunscriptChart(
        s, visible_bands, "",
        win_end - win_start,
        large_funscript_threshold=10_000_000,
    )

    class _LocalVS:
        zoom_start_ms      = win_start
        zoom_end_ms        = win_end
        color_mode         = view_state.color_mode
        show_phrases       = True
        selection_start_ms = sel_phrase["start_ms"]
        selection_end_ms   = sel_phrase["end_ms"]
        def has_zoom(self):      return True
        def has_selection(self): return True

    fig = chart._build_figure(_LocalVS(), height=260)

    # Dim areas outside the selected phrase so context is visible but muted
    try:
        import plotly.graph_objects as go
        _DIM = "rgba(15,15,20,0.65)"
        if win_start < sel_phrase["start_ms"]:
            fig.add_vrect(
                x0=win_start, x1=sel_phrase["start_ms"],
                fillcolor=_DIM, layer="above", line_width=0,
            )
        if sel_phrase["end_ms"] < win_end:
            fig.add_vrect(
                x0=sel_phrase["end_ms"], x1=win_end,
                fillcolor=_DIM, layer="above", line_width=0,
            )
    except Exception:
        pass

    # Render without modebar so the timescale is locked
    st.plotly_chart(fig, key=chart_key, config={"displayModeBar": False})


# ------------------------------------------------------------------
# Transform application
# ------------------------------------------------------------------

def _apply_transform_to_window(
    original_actions: list,
    phrase: dict,
    spec,
    param_values: dict,
) -> list:
    """Deep-copy original_actions, apply spec only to the phrase slice."""
    phrase_start = phrase["start_ms"]
    phrase_end   = phrase["end_ms"]

    result       = copy.deepcopy(original_actions)
    phrase_slice = [a for a in result if phrase_start <= a["at"] <= phrase_end]
    transformed  = spec.apply(phrase_slice, param_values)

    t_to_pos = {a["at"]: a["pos"] for a in transformed}
    for a in result:
        if a["at"] in t_to_pos:
            a["pos"] = t_to_pos[a["at"]]

    return result


# ------------------------------------------------------------------
# Transform controls
# ------------------------------------------------------------------

def _render_transform_controls(phrase: dict, bpm_threshold: float, phrase_idx: int) -> None:
    import streamlit as st
    from suggested_updates.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

    suggested_key = suggest_transform(phrase, bpm_threshold)
    keys   = list(TRANSFORM_CATALOG.keys())
    labels = [TRANSFORM_CATALOG[k].name for k in keys]
    suggested_idx = keys.index(suggested_key) if suggested_key in keys else 0

    st.markdown("**Transform**")
    st.caption(f"Suggested: **{TRANSFORM_CATALOG[suggested_key].name}**")

    chosen_label = st.selectbox(
        "Select transform",
        options=labels,
        index=suggested_idx,
        key=f"transform_sel_{phrase_idx}",
        label_visibility="collapsed",
    )
    chosen_key = keys[labels.index(chosen_label)]
    spec = TRANSFORM_CATALOG[chosen_key]

    st.caption(spec.description)

    param_values = {}
    for param_key, param in spec.params.items():
        if param.type == "float":
            param_values[param_key] = st.slider(
                param.label,
                min_value=float(param.min_val or 0.0),
                max_value=float(param.max_val or 1.0),
                value=float(param.default),
                step=float(param.step or 0.05),
                help=param.help,
                key=f"param_{phrase_idx}_{param_key}",
            )
        elif param.type == "int":
            param_values[param_key] = st.slider(
                param.label,
                min_value=int(param.min_val or 0),
                max_value=int(param.max_val or 100),
                value=int(param.default),
                step=int(param.step or 1),
                help=param.help,
                key=f"param_{phrase_idx}_{param_key}",
            )

    st.session_state[f"phrase_transform_{phrase_idx}"] = {
        "transform_key": chosen_key,
        "param_values":  param_values,
    }


# ------------------------------------------------------------------
# Phrase navigation buttons (bottom-right)
# ------------------------------------------------------------------

def _render_nav_buttons(phrases: list, phrase_idx: int, view_state, duration_ms: int) -> None:
    import streamlit as st

    n = len(phrases)
    st.caption(f"P{phrase_idx + 1} of {n}")

    col_p, col_n = st.columns(2)
    with col_p:
        if st.button("⏮ Prev", key="pd_phrase_prev",
                     disabled=(phrase_idx == 0),
                     use_container_width=True):
            target = phrases[phrase_idx - 1]
            _select_and_zoom(target, view_state, duration_ms)
            st.rerun()

    with col_n:
        if st.button("Next ⏭", key="pd_phrase_next",
                     disabled=(phrase_idx >= n - 1),
                     use_container_width=True):
            target = phrases[phrase_idx + 1]
            _select_and_zoom(target, view_state, duration_ms)
            st.rerun()


# ------------------------------------------------------------------
# Save / Cancel buttons
# ------------------------------------------------------------------

def _render_save_cancel(phrases: list, original_actions: list, view_state) -> None:
    """Save applies all stored transforms and downloads the result.
    Cancel discards all stored transforms and returns to phrase selector.
    """
    import streamlit as st

    st.divider()

    # Build edited actions from all stored phrase transforms
    edited_actions = _build_edited_actions(phrases, original_actions)

    # Load the original funscript JSON to preserve metadata (version, range, etc.)
    funscript_path = st.session_state.project.funscript_path
    try:
        with open(funscript_path) as f:
            raw = json.load(f)
    except Exception:
        raw = {}
    raw["actions"] = sorted(edited_actions, key=lambda a: a["at"])
    edited_bytes = json.dumps(raw, indent=2).encode()

    # Derive download filename: strip .original suffix if present
    stem = os.path.splitext(os.path.basename(funscript_path))[0]
    if stem.endswith(".original"):
        stem = stem[:-9]
    download_name = f"{stem}.edited.funscript"

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.download_button(
            "💾 Save",
            data=edited_bytes,
            file_name=download_name,
            mime="application/json",
            key="pd_save",
            use_container_width=True,
            help=f"Download as {download_name} and return to phrase selector",
        ):
            _clear_transform_state()
            view_state.clear_selection()
            st.rerun()

    with col_cancel:
        if st.button(
            "✕ Cancel",
            key="pd_cancel",
            use_container_width=True,
            help="Discard all unsaved transforms and return to phrase selector",
        ):
            _clear_transform_state()
            view_state.clear_selection()
            st.rerun()


def _build_edited_actions(phrases: list, original_actions: list) -> list:
    """Apply all stored phrase transforms to original_actions and return result."""
    import streamlit as st
    from suggested_updates.phrase_transforms import TRANSFORM_CATALOG

    result = copy.deepcopy(original_actions)
    for idx, phrase in enumerate(phrases):
        transform_state = st.session_state.get(f"phrase_transform_{idx}", {})
        transform_key   = transform_state.get("transform_key")
        if not transform_key or transform_key == "passthrough":
            continue
        param_values = transform_state.get("param_values", {})
        spec = TRANSFORM_CATALOG.get(transform_key)
        if not spec:
            continue
        phrase_start = phrase["start_ms"]
        phrase_end   = phrase["end_ms"]
        phrase_slice = [a for a in result if phrase_start <= a["at"] <= phrase_end]
        transformed  = spec.apply(phrase_slice, param_values)
        t_to_pos     = {a["at"]: a["pos"] for a in transformed}
        for a in result:
            if a["at"] in t_to_pos:
                a["pos"] = t_to_pos[a["at"]]

    return result


def _clear_transform_state() -> None:
    """Remove all phrase_transform_* keys from session state."""
    import streamlit as st
    keys_to_del = [k for k in st.session_state if k.startswith("phrase_transform_")]
    for k in keys_to_del:
        del st.session_state[k]


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

def _select_and_zoom(phrase: dict, view_state, duration_ms: int) -> None:
    view_state.set_selection(phrase["start_ms"], phrase["end_ms"])
    start = phrase["start_ms"]
    end   = phrase["end_ms"]
    pad   = max((end - start) // 5, 2_000)
    view_state.set_zoom(max(0, start - pad), min(duration_ms, end + pad))
