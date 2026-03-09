"""pattern_editor.py — Behavioral pattern editor.

Phrases are classified into behavioral tags (stingy, giggle, drone, …)
by assessment/classifier.py.  This tab lets you:
  1. Select a tag to see all matching phrases.
  2. Pick one phrase instance and apply a transform (with live preview).
  3. Apply the same transform to all matching phrases at once.
  4. Download the fully edited funscript.

Layout
------
[Left 1/5]: Behavioral tag buttons with match counts + suggested transform
[Right 4/5]:
  - Subheader + tag description
  - Selector chart: full funscript, matching phrases highlighted
  - Instance buttons (one per matching phrase)
  - Detail area: [original (2) | preview (2) | controls (1)]

Performance notes
-----------------
- original_actions cached in session state (no re-read on every slider tick)
- Preview computed on the window slice only (no deepcopy of full action list)
- Instance charts use minimal raw Plotly lines (no FunscriptChart overhead)
- Download bytes only built when user clicks "Build download"
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Optional

import streamlit as st


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------


def render(project) -> None:
    """Render the Pattern Editor tab."""
    from assessment.classifier import TAGS

    if project is None or not project.is_loaded:
        st.info("Load and analyse a funscript first.")
        return

    assessment_dict = project.assessment.to_dict()
    phrases: List[dict] = assessment_dict.get("phrases", [])

    if not phrases:
        st.info("No phrases detected — run the assessment first.")
        return

    # Group phrases by behavioral tag
    tag_to_phrases: Dict[str, List[dict]] = {}
    for ph in phrases:
        for tag in ph.get("tags", []):
            tag_to_phrases.setdefault(tag, []).append(ph)

    # Order tags by count descending; preserve TAGS registry order within same count
    tag_order = sorted(
        [t for t in TAGS if t in tag_to_phrases],
        key=lambda t: -len(tag_to_phrases[t]),
    )
    # Phrases with no tags at all → show an "unclassified" group
    unclassified = [ph for ph in phrases if not ph.get("tags")]
    if unclassified:
        tag_to_phrases["unclassified"] = unclassified
        tag_order.append("unclassified")

    if not tag_order:
        st.success("No behavioral issues detected in any phrase.")
        return

    # Session state
    valid_tags = tag_order
    if "pe_selected_label" not in st.session_state or st.session_state.pe_selected_label not in valid_tags:
        st.session_state.pe_selected_label = valid_tags[0]
    if "pe_selected_instance" not in st.session_state:
        st.session_state.pe_selected_instance = 0

    selected_tag: str  = st.session_state.pe_selected_label
    funscript_path: str = project.funscript_path
    duration_ms: int   = project.assessment.duration_ms

    col_tags, col_detail = st.columns([1, 4])

    # Catalog stats (best-effort — catalog may be empty)
    catalog = st.session_state.get("pattern_catalog")
    catalog_stats = catalog.get_tag_stats() if catalog else {}

    with col_tags:
        st.markdown("**Behavioral tags**")
        for tag in tag_order:
            meta  = TAGS.get(tag)
            count = len(tag_to_phrases[tag])
            label = meta.label if meta else tag.replace("_", " ").title()
            cat   = catalog_stats.get(tag, {})
            total = cat.get("count", 0)
            files = cat.get("funscripts", 0)
            hint_parts = []
            if meta:
                hint_parts.append(f"Suggested: {meta.suggested_transform}")
            if total:
                hint_parts.append(f"Catalog: {total} phrases in {files} file{'s' if files != 1 else ''}")
            is_active = (tag == selected_tag)
            if st.button(
                f"{label}  ·  {count}",
                key=f"pe_tag_{tag}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
                help="  |  ".join(hint_parts) if hint_parts else None,
            ):
                if tag != selected_tag:
                    st.session_state.pe_selected_label   = tag
                    st.session_state.pe_selected_instance = 0
                    st.rerun(scope="app")

    with col_detail:
        matching = tag_to_phrases[selected_tag]
        phrase_idx = min(st.session_state.pe_selected_instance, len(matching) - 1)
        st.session_state.pe_selected_instance = phrase_idx

        # The detail fragment treats each matching phrase as one "cycle" window
        _detail_fragment(
            funscript_path=funscript_path,
            selected_label=selected_tag,
            cycles=matching,      # each phrase dict has start_ms / end_ms
            phrase_idx=phrase_idx,
            duration_ms=duration_ms,
        )


# ------------------------------------------------------------------
# Detail fragment — selector chart, instance buttons, editor
# ------------------------------------------------------------------


@st.fragment
def _detail_fragment(
    funscript_path: str,
    selected_label: str,
    cycles: List[dict],
    phrase_idx: int,
    duration_ms: int,
) -> None:
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG
    from assessment.classifier import TAGS

    n_instances = len(cycles)
    meta = TAGS.get(selected_label)
    display_name = meta.label if meta else selected_label.replace("_", " ").title()
    st.subheader(f"{display_name}  ·  {n_instances} phrase{'s' if n_instances != 1 else ''}")
    if meta:
        st.caption(meta.description)
        st.caption(f"Suggested fix: **{meta.suggested_transform}** — {meta.fix_hint}")

    # Catalog context for this tag
    catalog = st.session_state.get("pattern_catalog")
    if catalog:
        cs = catalog.get_tag_stats().get(selected_label, {})
        if cs.get("count", 0) > 0:
            st.caption(
                f"Catalog: **{cs['count']}** phrases tagged *{display_name}* "
                f"across **{cs['funscripts']}** file{'s' if cs['funscripts'] != 1 else ''} — "
                f"typical BPM {cs['bpm_min']}–{cs['bpm_max']} "
                f"· span {cs['span_min']}–{cs['span_max']}"
            )

    # ------------------------------------------------------------------
    # Cache original actions — read once per funscript path, not every rerun
    # ------------------------------------------------------------------
    cache_key = f"pe_actions_{funscript_path}"
    if cache_key not in st.session_state:
        with open(funscript_path) as f:
            st.session_state[cache_key] = json.load(f)["actions"]
    original_actions: List[dict] = st.session_state[cache_key]

    # ------------------------------------------------------------------
    # Selector chart — full funscript with instance overlays
    # ------------------------------------------------------------------
    _draw_selector_chart(
        actions=original_actions,
        cycles=cycles,
        selected_idx=phrase_idx,
        duration_ms=duration_ms,
        selected_label=selected_label,
    )

    # ------------------------------------------------------------------
    # Instance table — click a row to select that phrase
    # ------------------------------------------------------------------
    _render_instance_table(
        cycles=cycles,
        selected_label=selected_label,
        phrase_idx=phrase_idx,
    )

    # ------------------------------------------------------------------
    # Detail editor for the selected instance
    # ------------------------------------------------------------------
    st.divider()

    cycle = cycles[phrase_idx]
    start_ms: int = cycle["start_ms"]
    end_ms: int   = cycle["end_ms"]
    inst_idx: int = phrase_idx

    # Resolve transform from session state
    catalog_keys = list(TRANSFORM_CATALOG.keys())
    catalog_labels = [TRANSFORM_CATALOG[k].name for k in catalog_keys]

    sel_key = f"pe_tx_sel_{selected_label}_{inst_idx}"
    sel_label_val = st.session_state.get(sel_key)
    if sel_label_val and sel_label_val in catalog_labels:
        transform_key = catalog_keys[catalog_labels.index(sel_label_val)]
    else:
        stored = st.session_state.get(f"pe_transform_{selected_label}_{inst_idx}", {})
        transform_key = stored.get("transform_key", "passthrough")

    spec = TRANSFORM_CATALOG.get(transform_key, TRANSFORM_CATALOG["passthrough"])

    # Read current param values from session state
    param_values: Dict[str, Any] = {}
    for pk, param in spec.params.items():
        sv = st.session_state.get(f"pe_tx_{selected_label}_{inst_idx}_{pk}")
        param_values[pk] = sv if sv is not None else param.default

    # Compute preview window only — no deepcopy of full action list
    original_window = [a for a in original_actions if start_ms <= a["at"] <= end_ms]
    preview_window  = _apply_transform_to_window(original_window, cycle, spec, param_values)

    # Three-column layout: original | preview | controls
    col_orig, col_prev, col_ctrl = st.columns([2, 2, 1])

    with col_orig:
        st.caption(f"**Original — #{inst_idx + 1}**")
        _draw_instance_chart(
            actions=original_window,
            start_ms=start_ms,
            end_ms=end_ms,
            key=f"pe_orig_{selected_label}_{inst_idx}_{transform_key}",
            height=220,
        )

    with col_prev:
        st.caption(f"**Preview — {spec.name}**")
        _draw_instance_chart(
            actions=preview_window,
            start_ms=start_ms,
            end_ms=end_ms,
            key=f"pe_prev_{selected_label}_{inst_idx}_{transform_key}_{'_'.join(str(v) for v in param_values.values())}",
            height=220,
        )
        st.caption("*(not saved)*")

    with col_ctrl:
        _render_controls(
            selected_label=selected_label,
            inst_idx=inst_idx,
            cycle=cycle,
            cycles=cycles,
            n_instances=n_instances,
            original_actions=original_actions,
            funscript_path=funscript_path,
        )


# ------------------------------------------------------------------
# Instance table
# ------------------------------------------------------------------


def _render_instance_table(
    cycles: List[dict],
    selected_label: str,
    phrase_idx: int,
) -> None:
    """Render a selectable dataframe of all phrase instances for the active tag."""
    import pandas as pd
    from assessment.classifier import TAGS
    from utils import ms_to_timestamp

    meta = TAGS.get(selected_label)
    suggested = meta.suggested_transform if meta else "—"

    rows = []
    for i, cy in enumerate(cycles):
        m   = cy.get("metrics", {})
        stored  = st.session_state.get(f"pe_transform_{selected_label}_{i}", {})
        tx_key  = stored.get("transform_key", "")
        has_tx  = bool(tx_key and tx_key != "passthrough")
        # Mark selected row with an arrow so it's visible after navigation
        marker  = "▶" if i == phrase_idx else ("✓" if has_tx else "")
        rows.append({
            " ":          marker,
            "#":          i + 1,
            "Pattern":    cy.get("pattern_label", "—"),
            "Start":      ms_to_timestamp(cy["start_ms"]),
            "End":        ms_to_timestamp(cy["end_ms"]),
            "Duration":   ms_to_timestamp(cy["end_ms"] - cy["start_ms"]),
            "BPM":        round(cy.get("bpm", 0), 1),
            "Span":       round(m.get("span", 0), 1),
            "Centre":     round(m.get("mean_pos", 50), 1),
            "Velocity":   round(m.get("mean_velocity", 0), 3),
            "CV BPM":     round(m.get("cv_bpm", 0), 3),
            "Suggested":  tx_key if has_tx else suggested,
        })

    df = pd.DataFrame(rows)

    sel = st.dataframe(
        df,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"pe_instance_table_{selected_label}",
        column_config={
            " ":        st.column_config.TextColumn(width="small"),
            "#":        st.column_config.NumberColumn(width="small"),
            "Pattern":  st.column_config.TextColumn(width="medium"),
            "Start":    st.column_config.TextColumn(width="small"),
            "End":      st.column_config.TextColumn(width="small"),
            "Duration": st.column_config.TextColumn(width="small"),
            "BPM":      st.column_config.NumberColumn(width="small"),
            "Span":     st.column_config.NumberColumn(width="small"),
            "Centre":   st.column_config.NumberColumn(width="small"),
            "Velocity": st.column_config.NumberColumn(width="small", format="%.3f"),
            "CV BPM":   st.column_config.NumberColumn(width="small", format="%.3f"),
            "Suggested":st.column_config.TextColumn(width="medium"),
        },
    )

    sel_rows = sel.selection.get("rows", []) if sel and hasattr(sel, "selection") else []
    if sel_rows and sel_rows[0] != phrase_idx:
        st.session_state.pe_selected_instance = sel_rows[0]
        st.rerun(scope="app")


# ------------------------------------------------------------------
# Selector chart
# ------------------------------------------------------------------


def _draw_selector_chart(
    actions: List[dict],
    cycles: List[dict],
    selected_idx: int,
    duration_ms: int,
    selected_label: str,
) -> None:
    import plotly.graph_objects as go

    if not actions:
        return

    times_all = [a["at"] for a in actions]
    pos_all   = [a["pos"] for a in actions]

    fig = go.Figure()

    # Base layer: full funscript in dark grey
    fig.add_trace(go.Scatter(
        x=times_all, y=pos_all,
        mode="lines",
        line=dict(color="rgba(100,100,100,0.30)", width=1),
        showlegend=False, hoverinfo="skip",
    ))

    # Overlay each instance — white for selected, orange for others
    for i, cy in enumerate(cycles):
        seg = [(a["at"], a["pos"]) for a in actions
               if cy["start_ms"] <= a["at"] <= cy["end_ms"]]
        if not seg:
            continue
        sx, sy = zip(*seg)
        is_sel = (i == selected_idx)
        color = "rgba(255,255,255,0.95)" if is_sel else "rgba(255,165,0,0.60)"
        width = 2 if is_sel else 1.5
        fig.add_trace(go.Scatter(
            x=sx, y=sy,
            mode="lines",
            line=dict(color=color, width=width),
            showlegend=False, hoverinfo="skip",
        ))

    # Label only the selected instance
    sel_cy = cycles[selected_idx]
    fig.add_annotation(
        x=sel_cy["start_ms"], y=95,
        text=f"#{selected_idx + 1}",
        showarrow=False, xanchor="left", yanchor="top",
        font=dict(size=10, color="rgba(255,255,255,0.9)"),
        bgcolor="rgba(0,0,0,0)",
    )

    _BG = "rgba(14,14,18,1)"
    fig.update_layout(
        height=150,
        margin=dict(l=0, r=0, t=4, b=24),
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        xaxis=dict(
            range=[0, duration_ms], autorange=False,
            showgrid=False, zeroline=False,
            tickfont=dict(color="rgba(180,180,180,0.6)", size=9),
        ),
        yaxis=dict(
            range=[0, 100], showgrid=False, zeroline=False,
            showticklabels=False,
        ),
    )

    st.plotly_chart(
        fig,
        key=f"pe_sel_chart_{selected_label}_{selected_idx}",
        config={"displayModeBar": False},
    )


# ------------------------------------------------------------------
# Instance chart (window only) — minimal raw Plotly, no FunscriptChart
# ------------------------------------------------------------------


def _draw_instance_chart(
    actions: List[dict],
    start_ms: int,
    end_ms: int,
    key: str,
    height: int = 220,
) -> None:
    import plotly.graph_objects as go

    if not actions:
        st.caption("*(no actions in window)*")
        return

    xs = [a["at"] for a in actions]
    ys = [a["pos"] for a in actions]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys,
        mode="lines+markers",
        line=dict(color="rgba(200,200,200,0.85)", width=1.5),
        marker=dict(size=3, color="rgba(200,200,200,0.7)"),
        showlegend=False, hoverinfo="skip",
    ))

    _BG = "rgba(14,14,18,1)"
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=4, b=24),
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        xaxis=dict(
            range=[start_ms, end_ms], autorange=False,
            showgrid=False, zeroline=False,
            tickfont=dict(color="rgba(180,180,180,0.6)", size=9),
        ),
        yaxis=dict(
            range=[0, 100], showgrid=False, zeroline=False,
            showticklabels=False,
        ),
    )

    st.plotly_chart(fig, key=key, config={"displayModeBar": False})


# ------------------------------------------------------------------
# Transform application — operates on window slice only
# ------------------------------------------------------------------


def _apply_transform_to_window(
    window_actions: List[dict],
    cycle: dict,
    spec,
    param_values: dict,
) -> List[dict]:
    """Apply *spec* to *window_actions* (already filtered to the cycle window).

    Returns a list of actions covering the same window with the transform applied.
    Only the window slice is copied — the full action list is never touched.
    """
    if not window_actions:
        return []

    slice_copy = copy.deepcopy(window_actions)
    transformed = spec.apply(slice_copy, param_values)
    return transformed


# ------------------------------------------------------------------
# Controls column
# ------------------------------------------------------------------


def _render_controls(
    selected_label: str,
    inst_idx: int,
    cycle: dict,
    cycles: List[dict],
    n_instances: int,
    original_actions: List[dict],
    funscript_path: str,
) -> None:
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG

    catalog_keys = list(TRANSFORM_CATALOG.keys())
    catalog_labels = [TRANSFORM_CATALOG[k].name for k in catalog_keys]
    passthrough_idx = catalog_keys.index("passthrough") if "passthrough" in catalog_keys else 0

    # Determine current index for selectbox default
    stored = st.session_state.get(f"pe_transform_{selected_label}_{inst_idx}", {})
    stored_key = stored.get("transform_key", "passthrough")
    try:
        default_idx = catalog_keys.index(stored_key)
    except ValueError:
        default_idx = passthrough_idx

    st.markdown("**Transform**")

    chosen_label = st.selectbox(
        "Select transform",
        options=catalog_labels,
        index=default_idx,
        key=f"pe_tx_sel_{selected_label}_{inst_idx}",
        label_visibility="collapsed",
    )
    chosen_key = catalog_keys[catalog_labels.index(chosen_label)]
    spec = TRANSFORM_CATALOG[chosen_key]

    st.caption(spec.description)

    cycle_duration_ms = cycle["end_ms"] - cycle["start_ms"]

    # UI overrides for beat_accent
    _ui_int_overrides: dict = {}
    if chosen_key == "beat_accent":
        _ui_int_overrides["start_at_ms"] = dict(
            max_value=cycle_duration_ms,
            step=500,
        )
        _ui_int_overrides["max_accents"] = dict(max_value=60)

    # Clamp stale session state values
    for _pk, _ov in _ui_int_overrides.items():
        _sk = f"pe_tx_{selected_label}_{inst_idx}_{_pk}"
        _cap = _ov.get("max_value")
        if _cap is not None and st.session_state.get(_sk, 0) > _cap:
            st.session_state[_sk] = _cap

    param_values: Dict[str, Any] = {}
    for pk, param in spec.params.items():
        if param.type == "float":
            param_values[pk] = st.slider(
                param.label,
                min_value=float(param.min_val or 0.0),
                max_value=float(param.max_val or 1.0),
                value=float(param.default),
                step=float(param.step or 0.05),
                help=param.help,
                key=f"pe_tx_{selected_label}_{inst_idx}_{pk}",
            )
        elif param.type == "int":
            overrides = _ui_int_overrides.get(pk, {})
            param_values[pk] = st.slider(
                param.label,
                min_value=int(param.min_val or 0),
                max_value=int(overrides.get("max_value", param.max_val or 100)),
                value=int(param.default),
                step=int(overrides.get("step", param.step or 1)),
                help=param.help,
                key=f"pe_tx_{selected_label}_{inst_idx}_{pk}",
            )

    # Persist transform state
    st.session_state[f"pe_transform_{selected_label}_{inst_idx}"] = {
        "transform_key": chosen_key,
        "param_values": param_values,
    }

    # Apply to all button
    if st.button(
        "Apply to all",
        key=f"pe_apply_all_{selected_label}_{inst_idx}",
        use_container_width=True,
        help=f"Copy this transform to all {n_instances} instances of '{selected_label}'",
    ):
        for i in range(n_instances):
            st.session_state[f"pe_transform_{selected_label}_{i}"] = {
                "transform_key": chosen_key,
                "param_values": copy.deepcopy(param_values),
            }
        st.rerun(scope="app")

    st.write("")

    # Prev / Next navigation
    st.caption(f"#{inst_idx + 1} of {n_instances}")
    col_p, col_n = st.columns(2)
    with col_p:
        if st.button(
            "⏮ Prev",
            key=f"pe_prev_{selected_label}_{inst_idx}",
            disabled=(inst_idx == 0),
            use_container_width=True,
        ):
            st.session_state.pe_selected_instance = inst_idx - 1
            st.rerun(scope="app")
    with col_n:
        if st.button(
            "Next ⏭",
            key=f"pe_next_{selected_label}_{inst_idx}",
            disabled=(inst_idx >= n_instances - 1),
            use_container_width=True,
        ):
            st.session_state.pe_selected_instance = inst_idx + 1
            st.rerun(scope="app")

    st.divider()

    # Finalize + download
    _render_finalize_and_download(
        selected_label=selected_label,
        cycles=cycles,
        original_actions=original_actions,
        funscript_path=funscript_path,
    )


# ------------------------------------------------------------------
# Finalize options + download
# ------------------------------------------------------------------


def _render_finalize_and_download(
    selected_label: str,
    cycles: List[dict],
    original_actions: List[dict],
    funscript_path: str,
) -> None:
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG

    with st.expander("Finalize options", expanded=False):
        st.caption("Applied to the full script before download.")

        apply_seams = st.checkbox(
            "Blend seams",
            value=True,
            key=f"pe_fin_blend_seams_{selected_label}",
            help="Smooth high-velocity transitions at cycle boundaries.",
        )
        apply_smooth = st.checkbox(
            "Final smooth",
            value=True,
            key=f"pe_fin_final_smooth_{selected_label}",
            help="Light global LPF finishing pass.",
        )

        seam_params: dict = {}
        smooth_params: dict = {}

        if apply_seams:
            sp = TRANSFORM_CATALOG["blend_seams"].params
            seam_params["max_velocity"] = st.slider(
                sp["max_velocity"].label,
                min_value=float(sp["max_velocity"].min_val),
                max_value=float(sp["max_velocity"].max_val),
                value=float(sp["max_velocity"].default),
                step=float(sp["max_velocity"].step),
                help=sp["max_velocity"].help,
                key=f"pe_fin_seam_vel_{selected_label}",
            )
            seam_params["max_strength"] = st.slider(
                sp["max_strength"].label,
                min_value=float(sp["max_strength"].min_val),
                max_value=float(sp["max_strength"].max_val),
                value=float(sp["max_strength"].default),
                step=float(sp["max_strength"].step),
                help=sp["max_strength"].help,
                key=f"pe_fin_seam_str_{selected_label}",
            )

        if apply_smooth:
            fp = TRANSFORM_CATALOG["final_smooth"].params
            smooth_params["strength"] = st.slider(
                fp["strength"].label,
                min_value=float(fp["strength"].min_val),
                max_value=float(fp["strength"].max_val),
                value=float(fp["strength"].default),
                step=float(fp["strength"].step),
                help=fp["strength"].help,
                key=f"pe_fin_smooth_str_{selected_label}",
            )

        st.divider()

        # Build download only on explicit request — not on every slider tick
        if st.button(
            "Build download",
            key=f"pe_build_{selected_label}",
            use_container_width=True,
            help="Compile all transforms + finalize passes into a downloadable funscript.",
        ):
            edited = _build_all_transforms(cycles, selected_label, original_actions)

            finalized = copy.deepcopy(edited)
            if apply_seams:
                finalized = TRANSFORM_CATALOG["blend_seams"].apply(finalized, seam_params or None)
            if apply_smooth:
                finalized = TRANSFORM_CATALOG["final_smooth"].apply(finalized, smooth_params or None)

            try:
                with open(funscript_path) as f:
                    raw = json.load(f)
            except Exception:
                raw = {}

            raw["actions"] = sorted(finalized, key=lambda a: a["at"])
            st.session_state[f"pe_download_bytes_{selected_label}"] = json.dumps(raw, indent=2).encode()

    # Download button — shown once bytes have been built
    dl_bytes = st.session_state.get(f"pe_download_bytes_{selected_label}")
    if dl_bytes:
        stem = os.path.splitext(os.path.basename(funscript_path))[0]
        if stem.endswith(".original"):
            stem = stem[:-9]
        download_name = f"{stem}_pattern_edited.funscript"

        st.download_button(
            "Download",
            data=dl_bytes,
            file_name=download_name,
            mime="application/json",
            key=f"pe_download_{selected_label}",
            use_container_width=True,
            help=f"Download as {download_name}",
        )
    else:
        st.caption("Open *Finalize options* and click **Build download** to prepare the file.")


# ------------------------------------------------------------------
# Build edited actions for all instances of a label
# ------------------------------------------------------------------


def _build_all_transforms(
    cycles: List[dict],
    selected_label: str,
    original_actions: List[dict],
) -> List[dict]:
    """Apply all stored per-instance transforms to original_actions."""
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG

    result = copy.deepcopy(original_actions)

    for i, cycle in enumerate(cycles):
        stored = st.session_state.get(f"pe_transform_{selected_label}_{i}", {})
        tx_key = stored.get("transform_key")
        if not tx_key or tx_key == "passthrough":
            continue
        param_values = stored.get("param_values", {})
        spec = TRANSFORM_CATALOG.get(tx_key)
        if not spec:
            continue

        c_start = cycle["start_ms"]
        c_end = cycle["end_ms"]
        cycle_slice = [a for a in result if c_start <= a["at"] <= c_end]
        transformed = spec.apply(copy.deepcopy(cycle_slice), param_values)

        if spec.structural:
            outside = [a for a in result if not (c_start <= a["at"] <= c_end)]
            result = sorted(outside + transformed, key=lambda a: a["at"])
        else:
            t_to_pos = {a["at"]: a["pos"] for a in transformed}
            for a in result:
                if a["at"] in t_to_pos:
                    a["pos"] = t_to_pos[a["at"]]

    return result


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------


def _instance_has_transform(selected_label: str, inst_idx: int) -> bool:
    """Return True if a non-passthrough transform is stored for this instance."""
    stored = st.session_state.get(f"pe_transform_{selected_label}_{inst_idx}", {})
    tx_key = stored.get("transform_key")
    return bool(tx_key and tx_key != "passthrough")
