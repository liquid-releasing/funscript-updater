# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Transform Catalog panel — reference guide for all phrase transforms.

Each transform entry shows:
  • Headline and description
  • Behavioral tags it is best suited for
  • Parameter table (name, type, default, range, description)
  • Live before/after Plotly charts — sliders update the preview in real-time

Transforms are grouped by capability:
  1. Passthrough
  2. Amplitude Shaping
  3. Position Adjustment
  4. Smoothing & Filtering
  5. Break / Recovery
  6. Performance / Device Realism
  7. Rhythmic Patterns
  8. Structural — Tempo
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BG    = "rgba(14,14,18,1)"
_GRID  = "rgba(80,80,80,0.25)"
_BLUE  = "#4a90d9"
_GREEN = "#2ecc71"

# ---------------------------------------------------------------------------
# Transform groups: (group_label, [transform_key, ...])
# ---------------------------------------------------------------------------

_GROUPS: List[Tuple[str, List[str]]] = [
    ("Passthrough", ["passthrough"]),
    ("Amplitude Shaping", ["amplitude_scale", "normalize", "boost_contrast"]),
    ("Position Adjustment", ["shift", "recenter", "clamp_upper", "clamp_lower", "invert"]),
    ("Smoothing & Filtering", ["smooth", "blend_seams", "final_smooth"]),
    ("Break / Recovery", ["break"]),
    ("Performance / Device Realism", ["performance"]),
    ("Rhythmic Patterns", ["beat_accent", "three_one"]),
    ("Structural — Tempo", ["halve_tempo"]),
]

# Best-fit behavioral tags for each transform key
_TAG_FIT: Dict[str, List[str]] = {
    "passthrough":     ["Any section already well-formed or below BPM threshold"],
    "amplitude_scale": ["Stingy (amplify)", "Giggle / Plateau (reduce)", "Drone"],
    "normalize":       ["Giggle", "Plateau", "Half Stroke", "Lazy"],
    "boost_contrast":  ["Giggle", "Plateau", "Lazy", "low-contrast phrases"],
    "shift":           ["Drift", "Half Stroke", "vertical repositioning"],
    "recenter":        ["Drift", "Half Stroke", "amplitude-preserving reposition"],
    "clamp_upper":     ["intense sections", "high-energy peaks"],
    "clamp_lower":     ["Break / recovery", "Lazy"],
    "invert":          ["directional correction", "artistic variation"],
    "smooth":          ["Frantic (jitter reduction)", "noisy transitions"],
    "blend_seams":     ["inter-phrase boundaries", "abrupt style changes"],
    "final_smooth":    ["post-processing finishing pass"],
    "break":           ["Break / rest zones", "recovery sections"],
    "performance":     ["Stingy", "Frantic", "Drone", "device-safety limiting"],
    "beat_accent":     ["Drone (add variation)", "Lazy", "repetitive sections"],
    "three_one":       ["Drone (rhythmic pattern)", "monotone sections"],
    "halve_tempo":     ["Frantic (too fast)", "high-BPM reduction"],
}

# ---------------------------------------------------------------------------
# Synthetic waveform generator (fixed, deterministic)
# ---------------------------------------------------------------------------

def _make_preview_actions() -> List[Dict[str, int]]:
    """Return a varied funscript waveform that clearly shows transform effects.

    Six distinct sections:
      0–1200 ms   Full-stroke moderate tempo  — baseline (0↔100)
      1200–2200   Partial amplitude / stingy  — strokes only reach 25–70
      2200–3000   Fast beats / frantic        — double tempo, full stroke
      3000–3900   Slow wide strokes           — half tempo, full stroke
      3900–4800   Drifted upward              — strokes centred around 75 (50–100)
      4800–5600   Return to full-stroke       — same as section 1
    """
    pts = [
        # --- section 1: full stroke, moderate tempo ---
        (0,    0),
        (200,  100),
        (400,  0),
        (600,  100),
        (800,  0),
        (1000, 100),
        (1200, 0),
        # --- section 2: partial amplitude (stingy / plateau) ---
        (1380, 25),
        (1560, 70),
        (1740, 25),
        (1920, 70),
        (2100, 25),
        (2200, 30),
        # --- section 3: fast beats (frantic) ---
        (2300, 100),
        (2400, 0),
        (2500, 100),
        (2600, 0),
        (2700, 100),
        (2800, 0),
        (2900, 100),
        (3000, 0),
        # --- section 4: slow wide strokes ---
        (3300, 100),
        (3600, 0),
        (3900, 100),
        # --- section 5: drifted upward (half-stroke / drift) ---
        (4100, 50),
        (4300, 100),
        (4500, 50),
        (4700, 100),
        (4800, 50),
        # --- section 6: full stroke return ---
        (5000, 0),
        (5200, 100),
        (5400, 0),
        (5600, 100),
    ]
    return [{"at": t, "pos": p} for t, p in pts]


_PREVIEW_ACTIONS = _make_preview_actions()

# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _make_chart(actions: List[Dict], color: str, title: str, height: int = 160) -> go.Figure:
    xs = [a["at"] for a in actions]
    ys = [a["pos"] for a in actions]
    fig = go.Figure(go.Scatter(
        x=xs, y=ys,
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=4),
        hovertemplate="%{y}<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=12), x=0.0, xanchor="left"),
        height=height,
        margin=dict(l=30, r=10, t=30, b=20),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        xaxis=dict(gridcolor=_GRID, zeroline=False, showticklabels=False),
        yaxis=dict(gridcolor=_GRID, zeroline=False, range=[-5, 105], title="pos"),
    )
    return fig


# ---------------------------------------------------------------------------
# Parameter widget renderer — returns current param values from session state
# ---------------------------------------------------------------------------

def _render_param_widgets(
    transform_key: str,
    params: dict,
) -> Dict[str, Any]:
    """Render sliders / number inputs for each param; return current values."""
    values: Dict[str, Any] = {}
    if not params:
        return values

    cols = st.columns(min(len(params), 3))
    for col, (pname, p) in zip(
        (cols[i % len(cols)] for i in range(len(params))),
        params.items(),
    ):
        key = f"tc_{transform_key}_{pname}"
        if p.type == "float":
            val = col.slider(
                p.label,
                min_value=float(p.min_val) if p.min_val is not None else 0.0,
                max_value=float(p.max_val) if p.max_val is not None else 1.0,
                value=float(p.default),
                step=float(p.step) if p.step is not None else 0.01,
                key=key,
                help=p.help or None,
            )
        elif p.type == "int":
            # Use slider for bounded params, number_input for large-range ones
            if p.min_val is not None and p.max_val is not None and (p.max_val - p.min_val) <= 200:
                val = col.slider(
                    p.label,
                    min_value=int(p.min_val),
                    max_value=int(p.max_val),
                    value=int(p.default),
                    step=int(p.step) if p.step is not None else 1,
                    key=key,
                    help=p.help or None,
                )
            else:
                val = col.number_input(
                    p.label,
                    min_value=int(p.min_val) if p.min_val is not None else 0,
                    max_value=int(p.max_val) if p.max_val is not None else 9999999,
                    value=int(p.default),
                    step=int(p.step) if p.step is not None else 1,
                    key=key,
                    help=p.help or None,
                )
        else:
            val = p.default
        values[pname] = val
    return values


# ---------------------------------------------------------------------------
# Single transform card
# ---------------------------------------------------------------------------

def _render_transform_card(spec) -> None:
    """Render one transform: header, tags, params, before/after charts."""
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG  # noqa: F401

    # Header
    badge = "  `structural`" if spec.structural else ""
    st.markdown(f"### {spec.name}{badge}")
    st.write(spec.description)

    # Tag fit
    tags = _TAG_FIT.get(spec.key, [])
    if tags:
        st.caption("Best for: " + " · ".join(tags))

    # Parameters table
    if spec.params:
        rows = []
        for pname, p in spec.params.items():
            range_str = ""
            if p.min_val is not None and p.max_val is not None:
                range_str = f"{p.min_val} – {p.max_val}"
            rows.append({
                "Parameter":   p.label,
                "Type":        p.type,
                "Default":     str(p.default),
                "Range":       range_str,
                "Description": p.help or "",
            })
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
        )

    # Two-column layout: Before chart (left) | sliders + After chart (right)
    before_actions = list(_PREVIEW_ACTIONS)

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(
            _make_chart(before_actions, _BLUE, "Before"),
            width="stretch",
            config={"displayModeBar": False},
            key=f"tc_chart_before_{spec.key}",
        )
    with chart_right:
        param_values = _render_param_widgets(spec.key, spec.params)
        after_actions = spec.apply(before_actions, param_values)
        st.plotly_chart(
            _make_chart(after_actions, _GREEN, "After"),
            width="stretch",
            config={"displayModeBar": False},
            key=f"tc_chart_after_{spec.key}",
        )

    st.divider()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render() -> None:
    """Render the full Transform Catalog panel."""
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG

    st.subheader("Transform Catalog")
    st.caption(
        "Reference guide for all phrase transforms. "
        "Adjust parameters to see their effect live on the preview waveform."
    )

    for group_label, keys in _GROUPS:
        specs = [TRANSFORM_CATALOG[k] for k in keys if k in TRANSFORM_CATALOG]
        if not specs:
            continue

        with st.expander(f"**{group_label}** ({len(specs)} transform{'s' if len(specs) != 1 else ''})", expanded=True):
            for spec in specs:
                _render_transform_card(spec)
