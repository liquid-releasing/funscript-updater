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
    from ui.common.work_items import ItemType, WorkItem
    from assessment.classifier import TAGS
    from utils import ms_to_timestamp

    st.subheader(f"Phrases  ({len(phrases)})")

    if not phrases:
        st.write("No phrases detected.")
        return

    # -- Timeline diagram --
    _render_phrases_timeline(phrases)

    # -- Build dataframe --
    rows = []
    for i, ph in enumerate(phrases):
        bpm = ph.get("bpm", 0.0)
        dur_ms = ph["end_ms"] - ph["start_ms"]
        raw_tags = ph.get("tags", []) or []
        tag_labels = ", ".join(
            TAGS[t].label if t in TAGS else t for t in raw_tags
        )
        rows.append({
            "#": i + 1,
            "start": ph.get("start_ts", ms_to_timestamp(ph["start_ms"])),
            "end": ph.get("end_ts", ms_to_timestamp(ph["end_ms"])),
            "BPM": round(bpm, 1),
            "duration": ms_to_timestamp(max(0, dur_ms)),
            "pattern": (ph.get("pattern_label", "") or "")[:35],
            "tags": tag_labels,
            "cycles": ph.get("cycle_count", ""),
        })

    df = pd.DataFrame(rows)

    sel = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="phrases_table_sel",
    )
    selected_rows: List[int] = (
        sel.selection.rows if sel and hasattr(sel, "selection") else []
    )
    n_sel = len(selected_rows)

    col_pe, col_ve, col_add = st.columns(3)

    # ---- Edit in Pattern Editor ----
    if col_pe.button(
        "Edit in Pattern Editor",
        disabled=(n_sel != 1),
        key="phrases_btn_pe",
    ):
        ph = phrases[selected_rows[0]]
        raw_tags = ph.get("tags", []) or []
        if not raw_tags:
            st.warning("This phrase has no behavioral tag.")
        else:
            tag = raw_tags[0]
            # Find which instance among all phrases with this tag
            inst_idx = 0
            count = 0
            for p in phrases:
                if tag in (p.get("tags") or []):
                    if p is ph:
                        inst_idx = count
                        break
                    count += 1
            st.session_state.pe_selected_label = tag
            st.session_state.pe_selected_instance = inst_idx
            st.toast("Switch to the Pattern Editor tab", icon="ℹ️")

    # ---- View in Phrase Editor ----
    if col_ve.button(
        "View in Phrase Editor",
        disabled=(n_sel != 1),
        key="phrases_btn_ve",
    ):
        ph = phrases[selected_rows[0]]
        st.session_state.view_state.set_zoom(ph["start_ms"], ph["end_ms"])
        st.toast("Switch to the Phrase Editor tab", icon="ℹ️")

    # ---- Add to Work Items ----
    if col_add.button(
        "Add to Work Items",
        disabled=(n_sel == 0),
        key="phrases_btn_add",
    ):
        existing_starts = {w.start_ms for w in project.work_items}
        added = 0
        for row_idx in selected_rows:
            ph = phrases[row_idx]
            if ph["start_ms"] in existing_starts:
                continue
            project.add_item(WorkItem(
                start_ms=ph["start_ms"],
                end_ms=ph["end_ms"],
                item_type=ItemType.NEUTRAL,
                label=(ph.get("pattern_label", "") or "")[:40],
                bpm=ph.get("bpm", 0.0),
                source="phrase",
            ))
            existing_starts.add(ph["start_ms"])
            added += 1
        if added:
            st.success(f"Added {added} work item(s).")
        else:
            st.info("All selected phrases are already in the work items list.")


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
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
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

    # -- Table --
    if transitions:
        rows = []
        for t in transitions:
            direction = "▲" if t.get("change_pct", 0) > 0 else "▼"
            rows.append({
                "at": t.get("at_ts", ""),
                "from BPM": round(t.get("from_bpm", 0), 1),
                "to BPM": round(t.get("to_bpm", 0), 1),
                "change": f"{abs(t.get('change_pct', 0)):.1f}%",
                "direction": direction,
            })
        df = pd.DataFrame(rows)
        sel = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="bpm_trans_table_sel",
        )
        selected_rows: List[int] = (
            sel.selection.rows if sel and hasattr(sel, "selection") else []
        )
    else:
        st.info("No significant BPM transitions detected — tempo is uniform throughout.")
        selected_rows = []

    n_sel = len(selected_rows)

    if st.button(
        "View in Phrase Editor",
        disabled=(n_sel != 1),
        key="bpm_trans_btn_ve",
    ):
        t = transitions[selected_rows[0]]
        at_ms = t.get("at_ms", 0)
        # Find the surrounding phrase
        surrounding = None
        for ph in phrases:
            if ph["start_ms"] <= at_ms <= ph["end_ms"]:
                surrounding = ph
                break
        if surrounding is None and phrases:
            # Fall back to nearest phrase
            surrounding = min(phrases, key=lambda p: abs(p["start_ms"] - at_ms))
        if surrounding:
            st.session_state.view_state.set_zoom(
                surrounding["start_ms"], surrounding["end_ms"]
            )
        st.toast("Switch to the Phrase Editor tab", icon="ℹ️")


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

    fig.update_layout(
        height=160,
        margin=dict(l=40, r=10, t=10, b=30),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        shapes=shapes,
        xaxis=dict(
            gridcolor=_GRID,
            zeroline=False,
            title=None,
        ),
        yaxis=dict(
            gridcolor=_GRID,
            zeroline=False,
            title="BPM",
            title_font=dict(size=11),
        ),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ---------------------------------------------------------------------------
# 4. Patterns
# ---------------------------------------------------------------------------


def _render_patterns_section(patterns: List[Dict], phrases: List[Dict]) -> None:
    from utils import ms_to_timestamp

    st.subheader(f"Patterns  ({len(patterns)})")

    if not patterns:
        st.write("No patterns detected.")
        return

    sorted_pats = sorted(patterns, key=lambda p: p.get("count", 0), reverse=True)

    # -- Plotly horizontal bar chart --
    labels = [(p.get("pattern_label", "") or "")[:40] for p in sorted_pats]
    counts = [p.get("count", 0) for p in sorted_pats]
    chart_height = max(100, len(sorted_pats) * 28 + 40)

    fig = go.Figure(go.Bar(
        x=counts,
        y=labels,
        orientation="h",
        marker_color="#4a90d9",
        hovertemplate="%{y}: %{x} cycles<extra></extra>",
    ))
    fig.update_layout(
        height=chart_height,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        xaxis=dict(gridcolor=_GRID, zeroline=False, title="Cycles"),
        yaxis=dict(gridcolor=_GRID, zeroline=False, autorange="reversed"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # -- Table --
    rows = []
    for p in sorted_pats:
        avg_dur = p.get("avg_duration_ms", 1)
        avg_bpm = round(60_000 / max(1, avg_dur), 1)
        from utils import ms_to_timestamp as _mtt
        rows.append({
            "pattern": (p.get("pattern_label", "") or "")[:50],
            "cycles": p.get("count", 0),
            "avg BPM": avg_bpm,
            "avg duration": _mtt(int(avg_dur)),
        })
    df = pd.DataFrame(rows)
    sel = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="patterns_table_sel",
    )
    selected_rows: List[int] = (
        sel.selection.rows if sel and hasattr(sel, "selection") else []
    )
    n_sel = len(selected_rows)

    if st.button(
        "Edit in Pattern Editor",
        disabled=(n_sel != 1),
        key="patterns_btn_pe",
    ):
        pat = sorted_pats[selected_rows[0]]
        pat_label = pat.get("pattern_label", "") or ""
        # Find the most-common tag across phrases with this pattern_label
        tag_counts: Dict[str, int] = {}
        for ph in phrases:
            if (ph.get("pattern_label", "") or "") == pat_label:
                for tg in (ph.get("tags") or []):
                    tag_counts[tg] = tag_counts.get(tg, 0) + 1
        if not tag_counts:
            st.warning("No behavioral tag found for this pattern.")
        else:
            top_tag = max(tag_counts, key=lambda k: tag_counts[k])
            # Find which instance
            inst_idx = 0
            count = 0
            for ph in phrases:
                if top_tag in (ph.get("tags") or []) and (ph.get("pattern_label", "") or "") == pat_label:
                    inst_idx = count
                    break
                if top_tag in (ph.get("tags") or []):
                    count += 1
            st.session_state.pe_selected_label = top_tag
            st.session_state.pe_selected_instance = inst_idx
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
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
