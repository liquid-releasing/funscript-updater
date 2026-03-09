"""pattern_editor.py — Pattern-type batch editor.

Layout
------
[Left 1/5]: Pattern type buttons (one per unique label, shows instance count)
[Right 4/5]:
  - Subheader: "Pattern: {label} — N instances"
  - Selector chart (height=160): full funscript, all instances as orange vrects,
    selected instance brighter, each labeled #1 #2 etc.
  - Instance buttons: row of small buttons (max 8 per row), checkmark prefix if
    transform set, "primary" type if selected
  - [Divider if instance selected]
  - Three-column detail: [original chart (2) | preview chart (2) | controls+buttons (1)]
    - Controls col: transform selectbox, param sliders, Apply-to-all, prev/next,
      divider, finalize expander, download button
    - Both charts show the cycle window only (start_ms to end_ms)
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
    if project is None or not project.is_loaded:
        st.info("Load and analyse a funscript first.")
        return

    # Gather all patterns from assessment
    assessment_dict = project.assessment.to_dict()
    raw_patterns: List[dict] = assessment_dict.get("patterns", [])

    if not raw_patterns:
        st.info("No patterns detected in this funscript.")
        return

    # Group cycles by pattern_label (multiple dicts may share the same label)
    grouped: Dict[str, List[dict]] = {}
    for pat in raw_patterns:
        label = pat.get("pattern_label", "unknown")
        cycles = pat.get("cycles", [])
        if label not in grouped:
            grouped[label] = []
        grouped[label].extend(cycles)

    # Sorted list of unique labels
    labels = sorted(grouped.keys())

    # Session state defaults
    if "pe_selected_label" not in st.session_state or st.session_state.pe_selected_label not in labels:
        st.session_state.pe_selected_label = labels[0] if labels else None
    if "pe_selected_instance" not in st.session_state:
        st.session_state.pe_selected_instance = 0

    selected_label: Optional[str] = st.session_state.pe_selected_label
    funscript_path: str = project.funscript_path
    duration_ms: int = project.assessment.duration_ms

    # Two-column layout: left type buttons | right detail
    col_types, col_detail = st.columns([1, 4])

    with col_types:
        st.markdown("**Pattern Types**")
        for lbl in labels:
            count = len(grouped[lbl])
            is_active = lbl == selected_label
            if st.button(
                f"{lbl}\n({count})",
                key=f"pe_type_{lbl}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                if lbl != st.session_state.pe_selected_label:
                    st.session_state.pe_selected_label = lbl
                    st.session_state.pe_selected_instance = 0
                    st.rerun(scope="app")

    with col_detail:
        if selected_label is None:
            st.info("Select a pattern type on the left.")
            return

        cycles = grouped[selected_label]
        phrase_idx = min(st.session_state.pe_selected_instance, len(cycles) - 1)
        st.session_state.pe_selected_instance = phrase_idx

        _detail_fragment(
            funscript_path=funscript_path,
            selected_label=selected_label,
            cycles=cycles,
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

    n_instances = len(cycles)
    st.subheader(f"Pattern: {selected_label} — {n_instances} instance{'s' if n_instances != 1 else ''}")

    # Load original actions once for the whole fragment
    with open(funscript_path) as f:
        original_actions: List[dict] = json.load(f)["actions"]

    # ------------------------------------------------------------------
    # Selector chart — full funscript with instance vrects
    # ------------------------------------------------------------------
    _draw_selector_chart(
        actions=original_actions,
        cycles=cycles,
        selected_idx=phrase_idx,
        duration_ms=duration_ms,
        selected_label=selected_label,
    )

    # ------------------------------------------------------------------
    # Instance buttons
    # ------------------------------------------------------------------
    MAX_PER_ROW = 8
    rows = [cycles[i : i + MAX_PER_ROW] for i in range(0, n_instances, MAX_PER_ROW)]
    row_offsets = list(range(0, n_instances, MAX_PER_ROW))

    for row_cycles, row_start in zip(rows, row_offsets):
        btn_cols = st.columns(len(row_cycles))
        for col, (i_rel, cyc) in zip(btn_cols, enumerate(row_cycles)):
            inst_idx = row_start + i_rel
            has_tx = _instance_has_transform(selected_label, inst_idx)
            label_prefix = "✓ " if has_tx else ""
            btn_label = f"{label_prefix}#{inst_idx + 1}"
            is_sel = inst_idx == phrase_idx
            with col:
                if st.button(
                    btn_label,
                    key=f"pe_inst_{selected_label}_{inst_idx}",
                    type="primary" if is_sel else "secondary",
                    use_container_width=True,
                ):
                    if inst_idx != phrase_idx:
                        st.session_state.pe_selected_instance = inst_idx
                        st.rerun(scope="app")

    # ------------------------------------------------------------------
    # Detail editor for the selected instance
    # ------------------------------------------------------------------
    st.divider()

    cycle = cycles[phrase_idx]
    start_ms: int = cycle["start_ms"]
    end_ms: int = cycle["end_ms"]
    inst_idx: int = phrase_idx

    # Resolve transform from session state (read immediately, not one rerun behind)
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

    # Compute preview
    preview_actions = _apply_transform_to_cycle(original_actions, cycle, spec, param_values)

    # Three-column layout: original | preview | controls
    col_orig, col_prev, col_ctrl = st.columns([2, 2, 1])

    with col_orig:
        st.caption(f"**Original — #{inst_idx + 1}**")
        _draw_instance_chart(
            actions=original_actions,
            start_ms=start_ms,
            end_ms=end_ms,
            duration_ms=duration_ms,
            key=f"pe_orig_{selected_label}_{inst_idx}_{transform_key}",
            height=220,
        )

    with col_prev:
        st.caption(f"**Preview — {spec.name}**")
        _draw_instance_chart(
            actions=preview_actions,
            start_ms=start_ms,
            end_ms=end_ms,
            duration_ms=duration_ms,
            key=f"pe_prev_{selected_label}_{inst_idx}_{transform_key}",
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
# Instance chart (cycle window only)
# ------------------------------------------------------------------


def _draw_instance_chart(
    actions: List[dict],
    start_ms: int,
    end_ms: int,
    duration_ms: int,
    key: str,
    height: int = 220,
) -> None:
    from visualizations.chart_data import compute_chart_data
    from visualizations.funscript_chart import FunscriptChart

    window_actions = [a for a in actions if start_ms <= a["at"] <= end_ms]
    series = compute_chart_data(window_actions)

    chart = FunscriptChart(
        series, [],
        "",
        end_ms - start_ms,
        large_funscript_threshold=10_000_000,
    )

    class _VS:
        zoom_start_ms = start_ms
        zoom_end_ms = end_ms
        color_mode = "amplitude"
        show_phrases = False
        selection_start_ms = None
        selection_end_ms = None
        def has_zoom(self): return True
        def has_selection(self): return False

    fig = chart._build_figure(_VS(), height=height)
    fig.update_xaxes(range=[start_ms, end_ms], autorange=False)

    st.plotly_chart(fig, key=key, config={"displayModeBar": False})


# ------------------------------------------------------------------
# Transform application
# ------------------------------------------------------------------


def _apply_transform_to_cycle(
    original_actions: List[dict],
    cycle: dict,
    spec,
    param_values: dict,
) -> List[dict]:
    """Return a deep-copied action list with the transform applied to the cycle window."""
    c_start = cycle["start_ms"]
    c_end = cycle["end_ms"]

    result = copy.deepcopy(original_actions)
    cycle_slice = [a for a in result if c_start <= a["at"] <= c_end]
    transformed = spec.apply(cycle_slice, param_values)

    if spec.structural:
        outside = [a for a in result if not (c_start <= a["at"] <= c_end)]
        return sorted(outside + transformed, key=lambda a: a["at"])

    t_to_pos = {a["at"]: a["pos"] for a in transformed}
    for a in result:
        if a["at"] in t_to_pos:
            a["pos"] = t_to_pos[a["at"]]

    return result


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

    # Build fully-edited action list: apply all stored instance transforms
    edited = _build_all_transforms(cycles, selected_label, original_actions)

    # Apply finalize passes
    finalized = copy.deepcopy(edited)
    if apply_seams:
        finalized = TRANSFORM_CATALOG["blend_seams"].apply(finalized, seam_params or None)
    if apply_smooth:
        finalized = TRANSFORM_CATALOG["final_smooth"].apply(finalized, smooth_params or None)

    # Load original funscript JSON envelope
    try:
        with open(funscript_path) as f:
            raw = json.load(f)
    except Exception:
        raw = {}

    raw["actions"] = sorted(finalized, key=lambda a: a["at"])
    edited_bytes = json.dumps(raw, indent=2).encode()

    stem = os.path.splitext(os.path.basename(funscript_path))[0]
    if stem.endswith(".original"):
        stem = stem[:-9]
    download_name = f"{stem}_pattern_edited.funscript"

    st.download_button(
        "Download",
        data=edited_bytes,
        file_name=download_name,
        mime="application/json",
        key=f"pe_download_{selected_label}",
        use_container_width=True,
        help=f"Download as {download_name}",
    )


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
        transformed = spec.apply(cycle_slice, param_values)

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
