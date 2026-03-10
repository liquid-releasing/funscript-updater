"""catalog_view.py — Pattern Catalog tab.

Two sections
------------
1. This funscript
   - Behavioral timeline: multi-row Gantt showing where each tag appears
   - Tag summary table with metrics
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

    if catalog is not None:
        st.divider()
        _render_saved_patterns_section(catalog)


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

    # --- Tag details table ---
    st.markdown("#### Tag details")

    # Group phrases by tag
    tag_groups: Dict[str, List[dict]] = {}
    for ph in phrases:
        for tag in ph.get("tags", []):
            tag_groups.setdefault(tag, []).append(ph)

    def _rng(lst):
        if not lst: return "—"
        lo, hi = round(min(lst), 1), round(max(lst), 1)
        return f"{lo}–{hi}" if lo != hi else str(lo)

    for tag, phs in sorted(tag_groups.items(), key=lambda x: -len(x[1])):
        meta    = TAGS.get(tag)
        bpms    = [p.get("bpm", 0) for p in phs if p.get("bpm", 0) > 0]
        spans   = [p.get("metrics", {}).get("span", 0) for p in phs]
        label   = meta.label if meta else tag.title()
        hint    = meta.fix_hint if meta else "—"

        bpm_str  = _rng(bpms)
        span_str = _rng(spans)
        header   = f"**{label}** — {len(phs)} phrase{'s' if len(phs) != 1 else ''} · BPM {bpm_str} · span {span_str}"

        with st.expander(header, expanded=False):
            st.caption(f"Fix: {hint}")
            st.markdown("")

            ph_hcols = st.columns([2.5, 1.2, 1.2, 1.0])
            for h, lbl in zip(ph_hcols, ["Time range", "BPM", "Span", ""]):
                h.caption(lbl)

            for j, ph in enumerate(sorted(phs, key=lambda p: p["start_ms"])):
                time_str = f"{ms_to_timestamp(ph['start_ms'])} → {ms_to_timestamp(ph['end_ms'])}"
                bpm_val  = ph.get("bpm", 0)
                span_val = ph.get("metrics", {}).get("span", 0)

                pr = st.columns([2.5, 1.2, 1.2, 1.0])
                pr[0].write(time_str)
                pr[1].write(f"{bpm_val:.1f}")
                pr[2].write(f"{span_val:.0f}")
                if pr[3].button("✏", key=f"cv_edit_{tag}_{j}", help="Edit in Phrase Editor"):
                    st.session_state.view_state.set_selection(ph["start_ms"], ph["end_ms"])
                    st.session_state.goto_tab = 1
                    st.rerun()


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


# ---------------------------------------------------------------------------
# Section 3 — saved raw patterns
# ---------------------------------------------------------------------------

def _render_saved_patterns_section(catalog) -> None:
    st.subheader("Saved patterns")

    patterns = catalog.get_saved_patterns()

    if not patterns:
        st.info(
            "No patterns saved yet. Open the **Pattern Editor**, select a phrase instance, "
            "and use **Save to catalog** in the controls panel."
        )
        return

    st.caption(f"{len(patterns)} pattern{'s' if len(patterns) != 1 else ''} saved")

    for pat in patterns:
        tag_labels = [TAGS[t].label if t in TAGS else t.title() for t in pat.get("tags", [])]
        tags_str   = ", ".join(tag_labels) if tag_labels else "untagged"
        header     = f"**{pat['name']}** — {tags_str} · {ms_to_timestamp(pat['duration_ms'])} · {pat['bpm']:.0f} BPM"

        with st.expander(header, expanded=False):
            col_info, col_del = st.columns([5, 1])

            with col_info:
                st.caption(
                    f"Source: {pat['source_funscript']}  "
                    f"({ms_to_timestamp(pat['source_start_ms'])} → {ms_to_timestamp(pat['source_end_ms'])})"
                )
                m = pat.get("metrics", {})
                if m:
                    mc = st.columns(4)
                    mc[0].metric("Span",     f"{m.get('span', 0):.0f}")
                    mc[1].metric("Centre",   f"{m.get('mean_pos', 50):.0f}")
                    mc[2].metric("Vel mean", f"{m.get('mean_velocity', 0):.3f}")
                    mc[3].metric("Actions",  len(pat.get("actions", [])))

            with col_del:
                if st.button(
                    "Delete",
                    key=f"cv_del_{pat['id']}",
                    type="secondary",
                    width="stretch",
                ):
                    catalog.delete_saved_pattern(pat["id"])
                    catalog.save()
                    st.rerun()

            # Preview chart (time-normalised actions)
            actions = pat.get("actions", [])
            if len(actions) >= 2:
                _render_pattern_preview(actions, pat["id"])


def _render_pattern_preview(actions: List[dict], pattern_id: str) -> None:
    """Compact line chart of time-normalised actions."""
    import plotly.graph_objects as go

    xs = [a["at"] for a in actions]
    ys = [a["pos"] for a in actions]

    fig = go.Figure(go.Scatter(
        x=xs, y=ys,
        mode="lines",
        line=dict(color="rgba(255,165,0,0.85)", width=1.5),
        showlegend=False,
        hovertemplate="t=%{x} ms  pos=%{y}<extra></extra>",
    ))
    _BG = "rgba(14,14,18,1)"
    fig.update_layout(
        height=140,
        margin=dict(l=0, r=0, t=4, b=4),
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        xaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(color="rgba(180,180,180,0.6)", size=8)),
        yaxis=dict(range=[0, 100], showgrid=True,
                   gridcolor="rgba(80,80,80,0.25)",
                   tickfont=dict(color="rgba(180,180,180,0.6)", size=8)),
    )
    st.plotly_chart(fig, config={"displayModeBar": False}, key=f"cv_pat_{pattern_id}")


