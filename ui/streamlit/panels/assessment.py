"""Assessment panel — displays the full pipeline output for a loaded project.

Renders four sub-sections corresponding to the analysis pipeline stages:
  1. Summary stats (meta)
  2. Phases
  3. Cycles → Patterns
  4. Phrases + BPM transitions (timeline)

All rendering is pure Streamlit; no state is mutated here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from ui.common.project import Project


# Colour map for phrase BPM intensity (low → high)
_BPM_LOW_COLOR = "#4a90d9"
_BPM_HIGH_COLOR = "#e84855"


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
    _render_summary(project.summary())
    st.divider()
    _render_phases(ad.get("phases", []))
    st.divider()
    _render_patterns(ad.get("patterns", []))
    st.divider()
    _render_phrases_timeline(ad.get("phrases", []), ad.get("bpm_transitions", []))


# ------------------------------------------------------------------
# Sub-sections
# ------------------------------------------------------------------


def _render_summary(summary: Dict[str, Any]) -> None:
    st.subheader("Summary")
    cols = st.columns(8)
    metrics = [
        ("Duration", summary.get("duration", "—")),
        ("Avg BPM", f"{summary.get('bpm', 0):.1f}"),
        ("Actions", summary.get("actions", 0)),
        ("Phases", summary.get("phases", 0)),
        ("Cycles", summary.get("cycles", 0)),
        ("Patterns", summary.get("patterns", 0)),
        ("Phrases", summary.get("phrases", 0)),
        ("BPM transitions", summary.get("bpm_transitions", 0)),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)


def _render_phases(phases: List[Dict]) -> None:
    with st.expander(f"Phases  ({len(phases)})", expanded=False):
        if not phases:
            st.write("No phases detected.")
            return

        # Direction breakdown bar chart.
        labels = [p["label"] for p in phases]
        counts = {
            "steady upward motion": labels.count("steady upward motion"),
            "steady downward motion": labels.count("steady downward motion"),
            "low-motion plateau": labels.count("low-motion plateau"),
        }
        df_counts = pd.DataFrame.from_dict(
            {"Direction": list(counts.keys()), "Count": list(counts.values())}
        )
        st.bar_chart(df_counts.set_index("Direction"))

        # First / last few phases table.
        st.caption("First 20 phases")
        rows = [
            {"start": p["start_ts"], "end": p["end_ts"], "label": p["label"]}
            for p in phases[:20]
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_patterns(patterns: List[Dict]) -> None:
    with st.expander(f"Cycles → Patterns  ({len(patterns)} patterns)", expanded=False):
        if not patterns:
            st.write("No patterns detected.")
            return

        rows = [
            {
                "pattern": p["pattern_label"][:60] + ("…" if len(p["pattern_label"]) > 60 else ""),
                "cycles": p["count"],
                "avg duration (ms)": int(p["avg_duration_ms"]),
                "avg BPM": round(60_000 / max(1, p["avg_duration_ms"]), 1),
            }
            for p in sorted(patterns, key=lambda x: x["count"], reverse=True)
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_phrases_timeline(phrases: List[Dict], transitions: List[Dict]) -> None:
    st.subheader(f"Phrases  ({len(phrases)})  &  BPM transitions  ({len(transitions)})")

    if not phrases:
        st.write("No phrases detected.")
        return

    total_ms = max(p["end_ms"] for p in phrases)
    if total_ms <= 0:
        return

    # Build a visual timeline using a horizontal bar per phrase.
    _render_horizontal_timeline(phrases, total_ms)

    # BPM transitions list.
    if transitions:
        st.markdown("**BPM transitions detected**")
        rows = []
        for t in transitions:
            arrow = "⬆" if t["change_pct"] > 0 else "⬇"
            rows.append({
                "at": t["at_ts"],
                "from BPM": round(t["from_bpm"], 1),
                "to BPM": round(t["to_bpm"], 1),
                "change %": f"{arrow} {abs(t['change_pct']):.1f}%",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No significant BPM transitions detected — tempo is uniform throughout.")

    # Phrase detail table.
    with st.expander("Phrase details"):
        rows = [
            {
                "start": p["start_ts"],
                "end": p["end_ts"],
                "BPM": round(p.get("bpm", 0), 1),
                "cycles": p.get("cycle_count", ""),
                "pattern": p.get("pattern_label", "")[:50],
            }
            for p in phrases
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_horizontal_timeline(phrases: List[Dict], total_ms: int) -> None:
    """Draw a colour-coded SVG timeline bar showing phrases by BPM."""
    all_bpms = [p.get("bpm", 0) for p in phrases]
    min_bpm = min(all_bpms) if all_bpms else 0
    max_bpm = max(all_bpms) if all_bpms else 1
    bpm_range = max(max_bpm - min_bpm, 1)

    bar_height = 40
    label_height = 18
    total_height = bar_height + label_height + 4
    width = 900

    def lerp_color(t: float) -> str:
        # Interpolate between low-BPM blue and high-BPM red.
        r0, g0, b0 = 0x4a, 0x90, 0xd9
        r1, g1, b1 = 0xe8, 0x48, 0x55
        r = int(r0 + (r1 - r0) * t)
        g = int(g0 + (g1 - g0) * t)
        b = int(b0 + (b1 - b0) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    rects: list[str] = []
    for ph in phrases:
        x = ph["start_ms"] / total_ms * width
        w = max((ph["end_ms"] - ph["start_ms"]) / total_ms * width, 1)
        bpm = ph.get("bpm", min_bpm)
        t = (bpm - min_bpm) / bpm_range
        color = lerp_color(t)
        label = f"{bpm:.0f}"
        rects.append(
            f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="{bar_height}" '
            f'fill="{color}" stroke="#111" stroke-width="0.5">'
            f'<title>{ph["start_ts"]} – {ph["end_ts"]} | {bpm:.1f} BPM</title>'
            f'</rect>'
        )
        if w > 28:
            rects.append(
                f'<text x="{x + w/2:.1f}" y="{bar_height/2 + 5:.0f}" '
                f'font-size="10" fill="white" text-anchor="middle">{label}</text>'
            )

    # Time axis labels (every ~10%).
    axis_labels = []
    for pct in range(0, 101, 10):
        ms = int(total_ms * pct / 100)
        secs = ms // 1000
        ts = f"{secs//60}:{secs%60:02d}"
        ax = pct / 100 * width
        axis_labels.append(
            f'<text x="{ax:.0f}" y="{bar_height + label_height:.0f}" '
            f'font-size="10" fill="#ccc" text-anchor="middle">{ts}</text>'
        )

    svg = (
        f'<svg width="{width}" height="{total_height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="background:#1e1e1e;border-radius:4px">'
        + "".join(rects)
        + "".join(axis_labels)
        + "</svg>"
    )
    st.markdown(
        f'<div style="overflow-x:auto">{svg}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Colour: blue = lower BPM → red = higher BPM. Hover a segment for exact values.")
