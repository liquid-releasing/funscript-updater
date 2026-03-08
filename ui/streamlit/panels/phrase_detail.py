"""phrase_detail.py — Detailed view for a selected phrase.

Layout
------
When a phrase is selected in the Phrase Selector this panel renders below
the phrase info table:

  [ Full-colour zoomed chart of the phrase + neighbour context ]
  [ Transform selector  |  Parameter sliders  |  Apply button  ]

The chart shows the selected phrase highlighted in gold, the immediate
neighbours dimmed, and everything outside the window hidden.

The transform selector lists all entries in TRANSFORM_CATALOG with the
system-suggested option pre-selected.  Adjustable parameter sliders appear
inline.  Pressing **Preview** shows a second overlay chart of the transformed
actions.
"""

from __future__ import annotations

from typing import List, Optional

from utils import ms_to_timestamp


def render(
    phrases: list,
    original_actions: list,
    view_state,
    duration_ms: int,
    bpm_threshold: float = 120.0,
) -> None:
    """Render the phrase detail panel.

    Parameters
    ----------
    phrases:
        Full phrase list from the assessment dict.
    original_actions:
        Raw funscript actions (used for the chart and preview).
    view_state:
        Shared ViewState — used to find the currently selected phrase.
    duration_ms:
        Total funscript duration.
    bpm_threshold:
        BPM threshold used by the transformer (for suggestion logic).
    """
    import streamlit as st

    if not view_state.has_selection():
        return

    # Find the selected phrase and its index.
    sel_start = view_state.selection_start_ms
    sel_end   = view_state.selection_end_ms
    phrase_idx = next(
        (i for i, ph in enumerate(phrases)
         if ph["start_ms"] == sel_start and ph["end_ms"] == sel_end),
        None,
    )
    if phrase_idx is None:
        return

    phrase = phrases[phrase_idx]

    st.divider()
    st.subheader(f"P{phrase_idx + 1} — Phrase Detail")

    # ------------------------------------------------------------------
    # Build viewport: selected phrase + one neighbour on each side
    # ------------------------------------------------------------------
    prev_phrase = phrases[phrase_idx - 1] if phrase_idx > 0 else None
    next_phrase = phrases[phrase_idx + 1] if phrase_idx < len(phrases) - 1 else None

    win_start = prev_phrase["start_ms"] if prev_phrase else sel_start
    win_end   = next_phrase["end_ms"]   if next_phrase else sel_end
    # Add a small pad so the borders aren't flush with the chart edge
    pad = max((sel_end - sel_start) // 10, 1_000)
    win_start = max(0, win_start - pad)
    win_end   = min(duration_ms, win_end + pad)

    # ------------------------------------------------------------------
    # Chart (left) + transform controls (right)
    # ------------------------------------------------------------------
    col_chart, col_controls = st.columns([3, 1])

    with col_chart:
        _render_detail_chart(
            original_actions=original_actions,
            phrases=phrases,
            phrase_idx=phrase_idx,
            win_start=win_start,
            win_end=win_end,
            view_state=view_state,
        )

    with col_controls:
        _render_transform_controls(phrase, bpm_threshold, phrase_idx)


# ------------------------------------------------------------------
# Detail chart
# ------------------------------------------------------------------

def _render_detail_chart(
    original_actions: list,
    phrases: list,
    phrase_idx: int,
    win_start: int,
    win_end: int,
    view_state,
    preview_actions: Optional[list] = None,
) -> None:
    import streamlit as st
    from visualizations.chart_data import compute_chart_data, compute_annotation_bands, slice_series, slice_bands, AnnotationBand, ANNOTATION_COLORS
    from visualizations.funscript_chart import FunscriptChart

    try:
        import plotly.graph_objects as go
    except ImportError:
        st.error("plotly is required.")
        return

    sel_phrase = phrases[phrase_idx]

    # Slice data to the window
    full_series = compute_chart_data(original_actions)
    from visualizations.chart_data import slice_series
    s = slice_series(full_series, win_start, win_end)

    # Build phrase bands only for the window
    assessment_stub = {"phrases": phrases, "phases": [], "cycles": [], "patterns": [], "bpm_transitions": []}
    all_bands = compute_annotation_bands(assessment_stub)
    visible_bands = slice_bands(all_bands, win_start, win_end)

    # Force threshold = 0 so all segments use per-segment coloured lines
    chart = FunscriptChart(s, visible_bands, "", win_end - win_start, large_funscript_threshold=10_000_000)

    # Override view_state zoom to the window without mutating the real view_state
    class _LocalVS:
        zoom_start_ms  = win_start
        zoom_end_ms    = win_end
        color_mode     = view_state.color_mode
        show_phrases   = True
        selection_start_ms = sel_phrase["start_ms"]
        selection_end_ms   = sel_phrase["end_ms"]
        def has_zoom(self): return True
        def has_selection(self): return True

    chart.render_streamlit(_LocalVS(), key=f"detail_chart_{phrase_idx}_{win_start}", height=280)

    # Overlay preview if available
    if preview_actions:
        preview_series = compute_chart_data(preview_actions)
        ps = slice_series(preview_series, win_start, win_end)
        colors = ps.colors_velocity if view_state.color_mode == "velocity" else ps.colors_amplitude
        n = len(ps.times_ms)
        fig_prev = go.Figure()
        for i in range(n - 1):
            fig_prev.add_trace(go.Scatter(
                x=[ps.times_ms[i], ps.times_ms[i + 1]],
                y=[ps.positions[i], ps.positions[i + 1]],
                mode="lines",
                line=dict(color=colors[i], width=2, dash="dot"),
                showlegend=False, hoverinfo="skip",
            ))
        st.caption("↑ Preview of transformed actions (dotted)")
        st.plotly_chart(fig_prev, key=f"preview_{phrase_idx}", use_container_width=True)


# ------------------------------------------------------------------
# Transform controls
# ------------------------------------------------------------------

def _render_transform_controls(phrase: dict, bpm_threshold: float, phrase_idx: int) -> None:
    import streamlit as st
    from suggested_updates.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

    suggested_key = suggest_transform(phrase, bpm_threshold)

    # Build display labels
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

    # Parameter sliders
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

    # Store chosen transform + params in session state for later use
    import streamlit as st
    st.session_state[f"phrase_transform_{phrase_idx}"] = {
        "transform_key": chosen_key,
        "param_values": param_values,
    }
