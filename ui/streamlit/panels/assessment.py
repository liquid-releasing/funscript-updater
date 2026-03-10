"""Assessment panel — displays the full pipeline output for a loaded project.

Sections
--------
1. Summary    — 8-metric row
2. Phrases    — Plotly timeline strip + table + action buttons
3. BPM Transitions — Plotly step chart + table + button
4. Patterns   — Plotly horizontal bar + table + button
5. Phases     — collapsed expander with direction breakdown + table
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

if TYPE_CHECKING:
    from ui.common.project import Project

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------

_BG = "rgba(14,14,18,1)"
_GRID = "rgba(80,80,80,0.25)"
_BPM_LOW_COLOR = "#4a90d9"
_BPM_HIGH_COLOR = "#e84855"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render(project: "Project") -> None:
    """Render the assessment panel for *project*.

    Parameters
    ----------
    project:
        A loaded Project instance (``project.is_loaded`` must be True).
    """
    if not project.is_loaded:
        st.info("Load a funscript to see assessment details.")
        return

    ad = project.assessment.to_dict()
    phrases = ad.get("phrases", [])
    transitions = ad.get("bpm_transitions", [])
    patterns = ad.get("patterns", [])
    phases = ad.get("phases", [])

    _render_summary(project.summary())
    st.divider()
    _render_phrases_section(phrases, project)
    st.divider()
    _render_bpm_transitions_section(transitions, phrases)
    st.divider()
    _render_patterns_section(patterns, phrases)
    _render_phases_expander(phases)


# ---------------------------------------------------------------------------
# 1. Summary
# ---------------------------------------------------------------------------


def _render_summary(summary: Dict[str, Any]) -> None:
    st.subheader("Summary")
    row1 = st.columns(4)
    row2 = st.columns(4)
    metrics = [
        ("Duration",        summary.get("duration", "—")),
        ("Avg BPM",         f"{summary.get('bpm', 0):.1f}"),
        ("Actions",         f"{summary.get('actions', 0):,}"),
        ("Phases",          f"{summary.get('phases', 0):,}"),
        ("Cycles",          f"{summary.get('cycles', 0):,}"),
        ("Patterns",        f"{summary.get('patterns', 0):,}"),
        ("Phrases",         f"{summary.get('phrases', 0):,}"),
        ("BPM transitions", f"{summary.get('bpm_transitions', 0):,}"),
    ]
    for col, (label, value) in zip(row1 + row2, metrics):
        col.metric(label, value)


# ---------------------------------------------------------------------------
# 2. Phrases
# ---------------------------------------------------------------------------


def _render_phrases_section(phrases: List[Dict], project: "Project") -> None:
    from assessment.classifier import TAGS
    from utils import ms_to_timestamp

    st.subheader(f"Phrases  ({len(phrases)})")

    if not phrases:
        st.write("No phrases detected.")
        return

    # -- Timeline diagram --
    _render_phrases_timeline(phrases)

    # -- Per-row table with Focus button --
    # Columns: #(narrow/nowrap) | Time | BPM | Dur | Description | Tags | Focus
    col_widths = [0.5, 3.0, 1.0, 1.3, 3.0, 2.5, 1.8]
    hcols = st.columns(col_widths)
    for h, lbl in zip(hcols, ["#", "Time", "BPM", "Dur", "Description", "Tags", ""]):
        h.caption(lbl)

    for i, ph in enumerate(phrases):
        bpm = ph.get("bpm", 0.0)
        dur_ms = ph["end_ms"] - ph["start_ms"]
        raw_tags = ph.get("tags", []) or []
        tag_labels = ", ".join(TAGS[t].label if t in TAGS else t for t in raw_tags)

        start_ts = ph.get("start_ts", ms_to_timestamp(ph["start_ms"]))
        end_ts   = ph.get("end_ts",   ms_to_timestamp(ph["end_ms"]))
        time_str = f"{start_ts} → {end_ts}"

        if raw_tags and raw_tags[0] in TAGS:
            desc = TAGS[raw_tags[0]].description
        else:
            desc = (ph.get("pattern_label", "") or "").replace("->", "→")

        rc = st.columns(col_widths)
        rc[0].markdown(
            f'<span style="white-space:nowrap">{i + 1}</span>',
            unsafe_allow_html=True,
        )
        rc[1].write(time_str)
        rc[2].write(f"{bpm:.1f}")
        rc[3].write(ms_to_timestamp(max(0, dur_ms)))
        rc[4].write(desc)
        rc[5].write(tag_labels)
        if rc[6].button("👁", key=f"ph_focus_{i}", help="Focus in Phrase Editor"):
            st.session_state.view_state.set_selection(ph["start_ms"], ph["end_ms"])
            st.session_state.goto_tab = 1
            st.rerun()


def _render_phrases_timeline(phrases: List[Dict]) -> None:
    """Plotly horizontal bar timeline strip, coloured by BPM."""
    if not phrases:
        return

    all_bpms = [p.get("bpm", 0.0) for p in phrases]
    min_bpm = min(all_bpms) if all_bpms else 0.0
    max_bpm = max(all_bpms) if all_bpms else 1.0
    bpm_range = max(max_bpm - min_bpm, 1.0)

    def _lerp_color(t: float) -> str:
        r0, g0, b0 = 0x4a, 0x90, 0xd9
        r1, g1, b1 = 0xe8, 0x48, 0x55
        r = int(r0 + (r1 - r0) * t)
        g = int(g0 + (g1 - g0) * t)
        b = int(b0 + (b1 - b0) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    bar_colors = []
    bar_bases = []
    bar_widths = []
    hover_texts = []

    for ph in phrases:
        bpm = ph.get("bpm", min_bpm)
        t = (bpm - min_bpm) / bpm_range
        bar_colors.append(_lerp_color(t))
        bar_bases.append(ph["start_ms"])
        dur = ph["end_ms"] - ph["start_ms"]
        bar_widths.append(max(dur, 1))
        hover_texts.append(
            f"{ph.get('start_ts', '')} – {ph.get('end_ts', '')} | {bpm:.1f} BPM"
        )

    fig = go.Figure(go.Bar(
        base=bar_bases,
        x=bar_widths,
        y=["phrases"] * len(phrases),
        orientation="h",
        marker_color=bar_colors,
        hovertext=hover_texts,
        hoverinfo="text",
        showlegend=False,
    ))
    fig.update_layout(
        height=90,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        bargap=0,
        bargroupgap=0,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("Colour: blue = lower BPM → red = higher BPM. Hover a segment for exact values.")


# ---------------------------------------------------------------------------
# 3. BPM Transitions
# ---------------------------------------------------------------------------


def _render_bpm_transitions_section(
    transitions: List[Dict], phrases: List[Dict]
) -> None:
    st.subheader(f"BPM Transitions  ({len(transitions)})")

    if not phrases:
        st.write("No phrase data available.")
        return

    # -- Plotly step chart --
    _render_bpm_step_chart(phrases, transitions)

    # -- Per-row table with Focus button --
    if transitions:
        _bt_cols = [2.5, 1.8, 1.8, 2.0, 1.2, 1.8]
        hcols = st.columns(_bt_cols)
        for h, lbl in zip(hcols, ["At", "From BPM", "To BPM", "Change", "Dir", ""]):
            h.caption(lbl)

        for i, t in enumerate(transitions):
            direction = "▲" if t.get("change_pct", 0) > 0 else "▼"
            rc = st.columns(_bt_cols)
            rc[0].write(t.get("at_ts", ""))
            rc[1].write(f"{t.get('from_bpm', 0):.1f}")
            rc[2].write(f"{t.get('to_bpm', 0):.1f}")
            rc[3].write(f"{abs(t.get('change_pct', 0)):.1f}%")
            rc[4].write(direction)
            if rc[5].button("👁", key=f"bt_focus_{i}", help="Focus in Phrase Editor"):
                at_ms = t.get("at_ms", 0)
                surrounding = None
                for ph in phrases:
                    if ph["start_ms"] <= at_ms <= ph["end_ms"]:
                        surrounding = ph
                        break
                if surrounding is None and phrases:
                    surrounding = min(phrases, key=lambda p: abs(p["start_ms"] - at_ms))
                if surrounding:
                    st.session_state.view_state.set_selection(
                        surrounding["start_ms"], surrounding["end_ms"]
                    )
                st.session_state.goto_tab = 1
                st.rerun()
    else:
        st.info("No significant BPM transitions detected — tempo is uniform throughout.")


def _render_bpm_step_chart(phrases: List[Dict], transitions: List[Dict]) -> None:
    """Plotly scatter/line showing BPM at each phrase midpoint."""
    if not phrases:
        return

    xs = []
    ys = []
    for ph in phrases:
        mid = (ph["start_ms"] + ph["end_ms"]) / 2
        xs.append(mid)
        ys.append(round(ph.get("bpm", 0.0), 1))

    duration_ms = phrases[-1]["end_ms"]
    long_chart = duration_ms > 900_000  # > 15 minutes

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs,
        y=ys,
        mode="lines",
        line=dict(color="#4a90d9", width=2, shape="hv"),
        name="BPM",
        hovertemplate="%{y:.1f} BPM<extra></extra>",
    ))

    # Vertical dashed lines at each transition
    shapes = []
    for t in transitions:
        at_ms = t.get("at_ms", 0)
        shapes.append(dict(
            type="line",
            x0=at_ms, x1=at_ms,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="#e84855", width=1, dash="dash"),
        ))

    xaxis_cfg: dict = dict(
        gridcolor=_GRID,
        zeroline=False,
        title=None,
    )
    if long_chart:
        from math import ceil as _ceil
        # Compute human-readable ticks spaced to avoid overlap
        span = duration_ms
        _candidates = [60_000, 120_000, 300_000, 600_000, 900_000, 1_800_000]
        _step = _candidates[-1]
        for _c in _candidates:
            if span / _c <= 20:
                _step = _c
                break
        _first = _ceil(0 / _step) * _step or _step
        _vals = list(range(_first, duration_ms + 1, _step))
        from utils import ms_to_timestamp as _mts
        xaxis_cfg["tickvals"] = _vals
        xaxis_cfg["ticktext"] = [_mts(v) for v in _vals]
        xaxis_cfg["tickangle"] = -45

    fig.update_layout(
        height=160,
        margin=dict(l=40, r=10, t=10, b=60 if long_chart else 30),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        shapes=shapes,
        xaxis=xaxis_cfg,
        yaxis=dict(
            gridcolor=_GRID,
            zeroline=False,
            title="BPM",
            title_font=dict(size=11),
        ),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# 4. Patterns
# ---------------------------------------------------------------------------


def _render_patterns_section(patterns: List[Dict], phrases: List[Dict]) -> None:
    from assessment.classifier import TAGS

    st.subheader("Behavioral Patterns")

    # Group phrases by behavioral tag
    tag_phrases: Dict[str, List[dict]] = {}
    for ph in phrases:
        for tag in (ph.get("tags") or []):
            tag_phrases.setdefault(tag, []).append(ph)

    if not tag_phrases:
        st.info("No behavioral patterns detected in this funscript.")
        return

    sorted_tags = sorted(tag_phrases.keys(), key=lambda t: -len(tag_phrases[t]))

    # -- Chart: phrase count per behavioral tag --
    labels = [TAGS[t].label if t in TAGS else t.title() for t in sorted_tags]
    counts = [len(tag_phrases[t]) for t in sorted_tags]
    colors = [TAGS[t].color if t in TAGS else "rgba(180,180,180,0.6)" for t in sorted_tags]
    chart_height = max(100, len(sorted_tags) * 36 + 40)

    fig = go.Figure(go.Bar(
        x=counts,
        y=labels,
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="%{y}: %{x} phrases<extra></extra>",
    ))
    fig.update_layout(
        height=chart_height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        xaxis=dict(gridcolor=_GRID, zeroline=False, title="Phrases"),
        yaxis=dict(gridcolor=_GRID, zeroline=False, autorange="reversed"),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # -- Per-row: label, description, phrase count, BPM range, Focus --
    _bhv_cols = [2.0, 3.5, 1.0, 2.0, 1.8]
    hcols = st.columns(_bhv_cols)
    for h, lbl in zip(hcols, ["Tag", "Description", "Phrases", "BPM range", ""]):
        h.caption(lbl)

    for i, tag in enumerate(sorted_tags):
        meta = TAGS.get(tag)
        phs  = tag_phrases[tag]
        bpms = [p.get("bpm", 0) for p in phs if p.get("bpm", 0) > 0]
        bpm_rng = (
            f"{min(bpms):.0f} – {max(bpms):.0f}" if bpms else "—"
        )

        rc = st.columns(_bhv_cols)
        rc[0].write(meta.label if meta else tag.title())
        rc[1].write(meta.description if meta else "")
        rc[2].write(len(phs))
        rc[3].write(bpm_rng)
        if rc[4].button("👁", key=f"bhv_focus_{i}", help="Focus in Pattern Editor"):
            st.session_state.pe_selected_label = tag
            st.session_state.pe_selected_instance = 0
            st.toast("Switch to the Pattern Editor tab", icon="ℹ️")


# ---------------------------------------------------------------------------
# 5. Phases (expander)
# ---------------------------------------------------------------------------


def _render_phases_expander(phases: List[Dict]) -> None:
    from utils import ms_to_timestamp

    with st.expander(f"Phases ({len(phases)})", expanded=False):
        if not phases:
            st.write("No phases detected.")
            return

        # Direction breakdown bar chart
        labels_list = [p.get("label", "") for p in phases]
        up_count = sum(1 for l in labels_list if "upward" in l)
        down_count = sum(1 for l in labels_list if "downward" in l)
        plateau_count = sum(1 for l in labels_list if "plateau" in l)

        fig = go.Figure(go.Bar(
            x=["Up", "Down", "Plateau"],
            y=[up_count, down_count, plateau_count],
            marker_color=["#4a90d9", "#e84855", "#888888"],
        ))
        fig.update_layout(
            height=120,
            margin=dict(l=10, r=10, t=10, b=30),
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            xaxis=dict(gridcolor=_GRID, zeroline=False),
            yaxis=dict(gridcolor=_GRID, zeroline=False),
            showlegend=False,
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        # First 50 phases table
        st.caption("First 50 phases")
        rows = [
            {
                "start": p.get("start_ts", ms_to_timestamp(p["start_ms"])),
                "end": p.get("end_ts", ms_to_timestamp(p["end_ms"])),
                "label": p.get("label", ""),
            }
            for p in phases[:50]
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
