"""catalog_view.py — Pattern Catalog tab.

Two sections
------------
1. This funscript
   - Behavioral timeline: multi-row Gantt showing where each tag appears
   - Tag summary table with metrics + sample chart on selection
2. Your library
   - Aggregate stats across all indexed funscripts
   - Tag frequency bar chart
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

import streamlit as st

from assessment.classifier import TAGS
from utils import ms_to_timestamp


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render(project) -> None:
    catalog = st.session_state.get("pattern_catalog")

    has_project = project is not None and project.is_loaded

    if has_project:
        assessment_dict = project.assessment.to_dict()
        phrases: List[dict] = assessment_dict.get("phrases", [])
        _render_funscript_section(project, phrases, catalog)
        st.divider()

    _render_library_section(catalog)


# ---------------------------------------------------------------------------
# Section 1 — this funscript
# ---------------------------------------------------------------------------

def _render_funscript_section(project, phrases: List[dict], catalog) -> None:
    import plotly.graph_objects as go

    fname       = project.funscript_path.split("\\")[-1].split("/")[-1]
    duration_ms = project.assessment.duration_ms

    st.subheader(f"This funscript — {fname}")

    tagged = [ph for ph in phrases if ph.get("tags")]
    if not tagged:
        st.info("No behavioral patterns detected in this funscript.")
        return

    # --- Behavioral timeline (Gantt) ---
    # Collect (tag, start_ms, end_ms) tuples; a phrase with multiple tags
    # appears in multiple rows.
    rows: List[dict] = []
    for ph in phrases:
        for tag in ph.get("tags", []):
            rows.append({
                "tag":      tag,
                "label":    TAGS[tag].label if tag in TAGS else tag.title(),
                "color":    TAGS[tag].color if tag in TAGS else "rgba(180,180,180,0.6)",
                "start_ms": ph["start_ms"],
                "end_ms":   ph["end_ms"],
                "bpm":      ph.get("bpm", 0),
                "span":     ph.get("metrics", {}).get("span", 0),
            })

    if rows:
        _render_behavioral_timeline(rows, duration_ms)

    st.caption(
        "Each row is a behavioral tag. Bars show when that pattern appears. "
        "Width = phrase duration."
    )

    # --- Tag summary table + sample chart ---
    st.markdown("#### Tag details")

    # Group phrases by tag
    tag_groups: Dict[str, List[dict]] = {}
    for ph in phrases:
        for tag in ph.get("tags", []):
            tag_groups.setdefault(tag, []).append(ph)

    # Build summary rows
    import pandas as pd
    summary_rows = []
    for tag, phs in sorted(tag_groups.items(), key=lambda x: -len(x[1])):
        meta    = TAGS.get(tag)
        bpms    = [p.get("bpm", 0) for p in phs if p.get("bpm", 0) > 0]
        spans   = [p.get("metrics", {}).get("span", 0) for p in phs]
        m_poses = [p.get("metrics", {}).get("mean_pos", 50) for p in phs]
        vels    = [p.get("metrics", {}).get("mean_velocity", 0) for p in phs]

        def rng(lst):
            if not lst: return "—"
            lo, hi = round(min(lst), 1), round(max(lst), 1)
            return f"{lo}–{hi}" if lo != hi else str(lo)

        summary_rows.append({
            "Tag":        meta.label if meta else tag.title(),
            "Phrases":    len(phs),
            "BPM range":  rng(bpms),
            "Span range": rng(spans),
            "Centre":     rng(m_poses),
            "Velocity":   rng(vels),
            "Fix":        meta.suggested_transform if meta else "—",
        })

    df = pd.DataFrame(summary_rows)
    sel = st.dataframe(
        df,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="cv_tag_table",
    )

    # Sample chart for the selected row
    sel_rows = sel.selection.get("rows", []) if sel and hasattr(sel, "selection") else []
    if sel_rows:
        sel_tag_label = summary_rows[sel_rows[0]]["Tag"]
        sel_tag       = next((t for t, m in TAGS.items() if m.label == sel_tag_label), None)
        if sel_tag and sel_tag in tag_groups:
            sample_phrase = tag_groups[sel_tag][0]
            _render_sample_chart(project, sample_phrase, sel_tag)


def _render_behavioral_timeline(rows: List[dict], duration_ms: int) -> None:
    """Gantt-style timeline: one y-row per tag, bars = phrase windows."""
    import plotly.graph_objects as go

    # Assign a y-position per unique tag label (sorted by tag key)
    unique_labels = list(dict.fromkeys(r["label"] for r in rows))  # preserve insertion order
    y_map = {lbl: i for i, lbl in enumerate(unique_labels)}

    fig = go.Figure()

    # One trace per tag so the legend / color is consistent
    from itertools import groupby
    rows_sorted = sorted(rows, key=lambda r: r["tag"])
    for tag_key, group in groupby(rows_sorted, key=lambda r: r["tag"]):
        group = list(group)
        lbl   = group[0]["label"]
        color = group[0]["color"]
        y_pos = y_map[lbl]

        for r in group:
            dur = max(1, r["end_ms"] - r["start_ms"])
            fig.add_trace(go.Bar(
                x=[dur],
                y=[lbl],
                base=[r["start_ms"]],
                orientation="h",
                marker=dict(color=color, line=dict(width=0)),
                showlegend=False,
                hovertemplate=(
                    f"<b>{lbl}</b><br>"
                    f"{ms_to_timestamp(r['start_ms'])} → {ms_to_timestamp(r['end_ms'])}<br>"
                    f"BPM: {r['bpm']:.0f}  span: {r['span']:.0f}"
                    "<extra></extra>"
                ),
                name=lbl,
            ))

    n_rows = len(unique_labels)
    _BG    = "rgba(14,14,18,1)"
    fig.update_layout(
        barmode="overlay",
        height=max(80, n_rows * 36 + 40),
        margin=dict(l=0, r=0, t=4, b=20),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        xaxis=dict(
            range=[0, duration_ms],
            showgrid=False, zeroline=False,
            tickfont=dict(color="rgba(180,180,180,0.7)", size=9),
        ),
        yaxis=dict(
            categoryorder="array",
            categoryarray=list(reversed(unique_labels)),
            tickfont=dict(color="rgba(220,220,220,0.9)", size=10),
            showgrid=False,
        ),
    )

    st.plotly_chart(fig, config={"displayModeBar": False}, key="cv_timeline")


def _render_sample_chart(project, phrase: dict, tag: str) -> None:
    """Show a small chart of the selected phrase's actions."""
    from visualizations.chart_data import compute_chart_data
    from visualizations.funscript_chart import FunscriptChart

    meta = TAGS.get(tag)
    st.markdown(
        f"**Sample — {meta.label if meta else tag}** "
        f"({ms_to_timestamp(phrase['start_ms'])} → {ms_to_timestamp(phrase['end_ms'])})"
    )

    try:
        with open(project.funscript_path) as f:
            all_actions = json.load(f)["actions"]
    except Exception:
        st.warning("Could not load funscript actions.")
        return

    start_ms = phrase["start_ms"]
    end_ms   = phrase["end_ms"]
    window   = [a for a in all_actions if start_ms <= a["at"] <= end_ms]
    if not window:
        st.caption("No actions in this window.")
        return

    s = compute_chart_data(window)

    class _VS:
        zoom_start_ms      = start_ms
        zoom_end_ms        = end_ms
        color_mode         = "amplitude"
        show_phrases       = False
        selection_start_ms = None
        selection_end_ms   = None
        def has_zoom(self):      return True
        def has_selection(self): return False

    chart = FunscriptChart(s, [], "", end_ms - start_ms)
    fig   = chart._build_figure(_VS(), height=180)
    fig.update_xaxes(range=[start_ms, end_ms], autorange=False)
    st.plotly_chart(fig, config={"displayModeBar": False}, key=f"cv_sample_{tag}")

    # Metrics row
    m = phrase.get("metrics", {})
    if m:
        cols = st.columns(5)
        cols[0].metric("BPM",      f"{phrase.get('bpm', 0):.0f}")
        cols[1].metric("Span",     f"{m.get('span', 0):.0f}")
        cols[2].metric("Centre",   f"{m.get('mean_pos', 50):.0f}")
        cols[3].metric("Vel mean", f"{m.get('mean_velocity', 0):.3f}")
        cols[4].metric("Duration", ms_to_timestamp(m.get("duration_ms", 0)))


# ---------------------------------------------------------------------------
# Section 2 — library catalog
# ---------------------------------------------------------------------------

def _render_library_section(catalog) -> None:
    st.subheader("Your library")

    if catalog is None:
        st.info("Catalog not available.")
        return

    summary = catalog.summary()
    n_files  = summary["funscripts_indexed"]
    n_tagged = summary["total_tagged_phrases"]

    if n_files == 0:
        st.info("No funscripts indexed yet — load and assess a funscript to begin building the catalog.")
        return

    col_a, col_b = st.columns(2)
    col_a.metric("Funscripts indexed", n_files)
    col_b.metric("Tagged phrases stored", n_tagged)

    stats = catalog.get_tag_stats()
    if not stats:
        st.caption("No tagged phrases in the catalog yet.")
        return

    # --- Frequency bar chart ---
    import plotly.graph_objects as go
    tags_sorted = sorted(stats.keys(), key=lambda t: -stats[t]["count"])
    labels  = [TAGS[t].label if t in TAGS else t.title() for t in tags_sorted]
    counts  = [stats[t]["count"] for t in tags_sorted]
    colors  = [TAGS[t].color if t in TAGS else "rgba(180,180,180,0.6)" for t in tags_sorted]

    fig = go.Figure(go.Bar(
        x=labels, y=counts,
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="%{x}: %{y} phrases<extra></extra>",
    ))
    _BG = "rgba(14,14,18,1)"
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=8, b=4),
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        xaxis=dict(showgrid=False, tickfont=dict(color="rgba(220,220,220,0.9)", size=10)),
        yaxis=dict(showgrid=True,  gridcolor="rgba(80,80,80,0.3)",
                   tickfont=dict(color="rgba(180,180,180,0.7)", size=9),
                   title=dict(text="phrases", font=dict(size=9, color="rgba(180,180,180,0.6)"))),
    )
    st.plotly_chart(fig, config={"displayModeBar": False}, key="cv_lib_bar")

    # --- Aggregate stats table ---
    import pandas as pd
    table_rows = []
    for tag in tags_sorted:
        s   = stats[tag]
        meta = TAGS.get(tag)
        table_rows.append({
            "Tag":          meta.label if meta else tag.title(),
            "Phrases":      s["count"],
            "Files":        s["funscripts"],
            "BPM range":    f"{s['bpm_min']}–{s['bpm_max']}",
            "Span range":   f"{s['span_min']}–{s['span_max']}",
            "Avg velocity": s["mean_vel_mean"],
            "Avg duration": ms_to_timestamp(s["duration_mean_ms"]),
        })

    st.dataframe(
        pd.DataFrame(table_rows),
        hide_index=True,
        key="cv_lib_table",
    )

    # --- Per-file breakdown ---
    with st.expander("Per-file breakdown", expanded=False):
        file_rows = []
        for entry in catalog.entries:
            tag_counts = {}
            for ph in entry.get("phrases", []):
                for t in ph.get("tags", []):
                    tag_counts[t] = tag_counts.get(t, 0) + 1
            row = {"File": entry["funscript"], "Assessed": entry.get("assessed_at", "")[:10]}
            for tag in tags_sorted:
                meta = TAGS.get(tag)
                lbl  = meta.label if meta else tag.title()
                row[lbl] = tag_counts.get(tag, 0)
            row["Total tagged"] = sum(tag_counts.values())
            file_rows.append(row)

        st.dataframe(
            pd.DataFrame(file_rows),
            hide_index=True,
            key="cv_file_table",
        )
