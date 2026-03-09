"""export_panel.py — Export tab: transform change log + download.

Two sections
------------
1. Completed transforms  — manually applied in Phrase Editor or Pattern Editor.
   Each row has a 🗑 reject button.
2. Recommended transforms — auto-suggested for phrases that have no manual transform.
   Each row has a ✏ edit button (opens Phrase Editor) and a 🗑 reject button.

The Download button applies all non-rejected entries from both lists.
"""

from __future__ import annotations

import copy
import json
from typing import Dict, List, Optional

import streamlit as st

from utils import ms_to_timestamp

# Column widths / headers for each table
_COL_W_DONE    = [0.4, 2.8, 1.0, 2.8, 1.8, 2.0, 1.5, 0.6]
_HEADERS_DONE  = ["#", "Time", "Dur (s)", "Transform", "Source", "BPM", "Cycles", ""]

_COL_W_REC     = [0.4, 2.8, 1.0, 3.2, 2.0, 1.5, 0.5, 0.5]
_HEADERS_REC   = ["#", "Time", "Dur (s)", "Transform", "BPM", "Cycles", "", ""]


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def render(project) -> None:
    """Render the Export tab."""
    if project is None or not project.is_loaded:
        st.info("Load a funscript first.")
        return

    assessment_dict = project.assessment.to_dict()
    phrases: List[dict] = assessment_dict.get("phrases", [])
    if not phrases:
        st.info("No phrases detected — run the assessment first.")
        return

    bpm_threshold: float = st.session_state.get("bpm_threshold", 120.0)

    if "export_rejected" not in st.session_state:
        st.session_state.export_rejected = set()

    tag_to_idxs: Dict[str, List[int]] = {}
    for i, ph in enumerate(phrases):
        for tag in ph.get("tags", []):
            tag_to_idxs.setdefault(tag, []).append(i)

    completed_plan, recommended_plan = _build_plans(phrases, tag_to_idxs, bpm_threshold)
    full_plan = completed_plan + recommended_plan

    # ----------------------------------------------------------------
    # Header controls
    # ----------------------------------------------------------------
    col_chk, col_dl = st.columns([5, 3])

    with col_chk:
        blend_seams = st.checkbox(
            "Add blended seams to reduce abrupt style changes",
            value=True,
            key="export_blend_seams",
        )
        final_smooth = st.checkbox(
            "Conduct final smooth for post process finishing",
            value=True,
            key="export_final_smooth",
        )

    with col_dl:
        active_entries = [
            e for e in full_plan
            if e["phrase_idx"] not in st.session_state.export_rejected
        ]
        if active_entries or blend_seams or final_smooth:
            dl_bytes = _build_download_bytes(
                project, phrases, full_plan,
                blend_seams=blend_seams,
                final_smooth=final_smooth,
            )
            st.download_button(
                "⬇ Download edited funscript",
                data=dl_bytes,
                file_name=f"{project.name}_edited.funscript",
                mime="application/json",
                type="primary",
            )
        else:
            st.button(
                "⬇ Download edited funscript",
                disabled=True,
                type="primary",
            )

    st.divider()

    # ----------------------------------------------------------------
    # Section 1 — Completed transforms
    # ----------------------------------------------------------------
    st.markdown("#### Completed transforms")
    _render_completed(completed_plan)

    st.divider()

    # ----------------------------------------------------------------
    # Section 2 — Recommended transforms
    # ----------------------------------------------------------------
    st.markdown("#### Recommended transforms")
    _render_recommended(recommended_plan)


# ------------------------------------------------------------------
# Plan building
# ------------------------------------------------------------------

def _build_plans(
    phrases: List[dict],
    tag_to_idxs: Dict[str, List[int]],
    bpm_threshold: float,
) -> tuple:
    """Return (completed_plan, recommended_plan) — two separate lists."""
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

    completed: List[dict] = []
    recommended: List[dict] = []

    for idx, phrase in enumerate(phrases):
        tx_key: Optional[str] = None
        param_values: dict = {}
        source: Optional[str] = None

        # 1. Phrase Editor
        phrase_tx = st.session_state.get(f"phrase_transform_{idx}", {})
        if phrase_tx.get("transform_key") and phrase_tx["transform_key"] != "passthrough":
            tx_key       = phrase_tx["transform_key"]
            param_values = phrase_tx.get("param_values", {})
            source       = "Phrase Editor"

        # 2. Pattern Editor
        if not tx_key:
            for tag in phrase.get("tags", []):
                tag_idxs = tag_to_idxs.get(tag, [])
                try:
                    i = tag_idxs.index(idx)
                except ValueError:
                    continue
                pe_tx = st.session_state.get(f"pe_transform_{tag}_{i}", {})
                if pe_tx.get("transform_key") and pe_tx["transform_key"] != "passthrough":
                    tx_key       = pe_tx["transform_key"]
                    param_values = pe_tx.get("param_values", {})
                    source       = "Pattern Editor"
                    break

        def _make_entry(key, params, src):
            old_bpm    = phrase.get("bpm", 0.0)
            old_cycles = phrase.get("cycle_count") or 0
            new_bpm    = old_bpm / 2    if key == "halve_tempo" else None
            new_cycles = old_cycles // 2 if key == "halve_tempo" else None
            spec       = TRANSFORM_CATALOG.get(key)
            return {
                "phrase_idx":   idx,
                "start_ms":     phrase["start_ms"],
                "end_ms":       phrase["end_ms"],
                "tx_key":       key,
                "tx_name":      spec.name if spec else key,
                "param_values": params,
                "source":       src,
                "old_bpm":      old_bpm,
                "new_bpm":      new_bpm,
                "old_cycles":   old_cycles,
                "new_cycles":   new_cycles,
            }

        if tx_key:
            completed.append(_make_entry(tx_key, param_values, source))
        else:
            # Untouched — build recommended entry
            rec, rec_params = suggest_transform(phrase, bpm_threshold)
            if rec and rec != "passthrough":
                recommended.append(_make_entry(rec, rec_params, "Recommended"))

    return completed, recommended


# ------------------------------------------------------------------
# Completed transforms table
# ------------------------------------------------------------------

def _render_completed(plan: List[dict]) -> None:
    rejected: set = st.session_state.export_rejected

    if not plan:
        st.caption("No transforms applied yet — edit phrases in the Phrase Editor or Pattern Editor.")
        return

    active  = sum(1 for e in plan if e["phrase_idx"] not in rejected)
    rej_cnt = len(plan) - active
    summary = f"{active} transform{'s' if active != 1 else ''} will be applied"
    if rej_cnt:
        summary += f" &nbsp;·&nbsp; {rej_cnt} rejected"
    st.caption(summary + " — click 🗑 to reject, ↩ to restore")

    hcols = st.columns(_COL_W_DONE)
    for hc, lbl in zip(hcols, _HEADERS_DONE):
        hc.caption(lbl)

    for entry in plan:
        idx      = entry["phrase_idx"]
        is_rej   = idx in rejected
        time_str = f"{ms_to_timestamp(entry['start_ms'])} → {ms_to_timestamp(entry['end_ms'])}"
        dur_s    = f"{(entry['end_ms'] - entry['start_ms']) / 1000:.1f}"
        bpm_str  = (
            f"{entry['old_bpm']:.1f} → {entry['new_bpm']:.1f}"
            if entry["new_bpm"] is not None else f"{entry['old_bpm']:.1f}"
        )
        cyc_str  = (
            f"{entry['old_cycles']} → {entry['new_cycles']}"
            if entry["new_cycles"] is not None else str(entry["old_cycles"])
        )

        rc = st.columns(_COL_W_DONE)
        if is_rej:
            _dim = lambda s: f"<span style='opacity:0.35'>{s}</span>"
            rc[0].markdown(_dim(f"<s>{idx + 1}</s>"), unsafe_allow_html=True)
            rc[1].markdown(_dim(time_str),             unsafe_allow_html=True)
            rc[2].markdown(_dim(dur_s),                unsafe_allow_html=True)
            rc[3].markdown(_dim(f"<s>{entry['tx_name']}</s>"), unsafe_allow_html=True)
            rc[4].markdown(_dim(entry["source"]),      unsafe_allow_html=True)
            rc[5].markdown(_dim(bpm_str),              unsafe_allow_html=True)
            rc[6].markdown(_dim(cyc_str),              unsafe_allow_html=True)
            if rc[7].button("↩", key=f"done_restore_{idx}", help="Restore"):
                st.session_state.export_rejected.discard(idx)
                st.rerun()
        else:
            rc[0].markdown(
                f"<span style='white-space:nowrap'>{idx + 1}</span>",
                unsafe_allow_html=True,
            )
            rc[1].write(time_str)
            rc[2].write(dur_s)
            rc[3].write(entry["tx_name"])
            rc[4].write(entry["source"])
            rc[5].write(bpm_str)
            rc[6].write(cyc_str)
            if rc[7].button("🗑", key=f"done_reject_{idx}", help="Reject"):
                st.session_state.export_rejected.add(idx)
                st.rerun()


# ------------------------------------------------------------------
# Recommended transforms table
# ------------------------------------------------------------------

def _render_recommended(plan: List[dict]) -> None:
    rejected: set = st.session_state.export_rejected

    if not plan:
        st.caption("All phrases have manual transforms — nothing to recommend.")
        return

    active  = sum(1 for e in plan if e["phrase_idx"] not in rejected)
    rej_cnt = len(plan) - active
    summary = f"{active} recommendation{'s' if active != 1 else ''} will be applied"
    if rej_cnt:
        summary += f" &nbsp;·&nbsp; {rej_cnt} rejected"
    st.caption(summary + " — click ✏ to edit in Phrase Editor, 🗑 to reject")

    hcols = st.columns(_COL_W_REC)
    for hc, lbl in zip(hcols, _HEADERS_REC):
        hc.caption(lbl)

    for entry in plan:
        idx      = entry["phrase_idx"]
        is_rej   = idx in rejected
        time_str = f"{ms_to_timestamp(entry['start_ms'])} → {ms_to_timestamp(entry['end_ms'])}"
        dur_s    = f"{(entry['end_ms'] - entry['start_ms']) / 1000:.1f}"
        bpm_str  = (
            f"{entry['old_bpm']:.1f} → {entry['new_bpm']:.1f}"
            if entry["new_bpm"] is not None else f"{entry['old_bpm']:.1f}"
        )
        cyc_str  = (
            f"{entry['old_cycles']} → {entry['new_cycles']}"
            if entry["new_cycles"] is not None else str(entry["old_cycles"])
        )
        param_caption = None
        if entry.get("param_values"):
            param_caption = "  ".join(f"{k}={v}" for k, v in entry["param_values"].items())

        rc = st.columns(_COL_W_REC)
        if is_rej:
            _dim = lambda s: f"<span style='opacity:0.35'>{s}</span>"
            rc[0].markdown(_dim(f"<s>{idx + 1}</s>"), unsafe_allow_html=True)
            rc[1].markdown(_dim(time_str),             unsafe_allow_html=True)
            rc[2].markdown(_dim(dur_s),                unsafe_allow_html=True)
            rc[3].markdown(_dim(f"<s>{entry['tx_name']}</s>"), unsafe_allow_html=True)
            rc[4].markdown(_dim(bpm_str),              unsafe_allow_html=True)
            rc[5].markdown(_dim(cyc_str),              unsafe_allow_html=True)
            # rc[6] edit slot — empty when rejected
            if rc[7].button("↩", key=f"rec_restore_{idx}", help="Restore"):
                st.session_state.export_rejected.discard(idx)
                st.rerun()
        else:
            rc[0].markdown(
                f"<span style='white-space:nowrap'>{idx + 1}</span>",
                unsafe_allow_html=True,
            )
            rc[1].write(time_str)
            rc[2].write(dur_s)
            rc[3].write(entry["tx_name"])
            if param_caption:
                rc[3].caption(param_caption)
            rc[4].write(bpm_str)
            rc[5].write(cyc_str)
            if rc[6].button("✏", key=f"rec_edit_{idx}", help="Edit in Phrase Editor"):
                st.session_state.view_state.set_selection(entry["start_ms"], entry["end_ms"])
                st.session_state.goto_tab = 1
                st.rerun()
            if rc[7].button("🗑", key=f"rec_reject_{idx}", help="Reject"):
                st.session_state.export_rejected.add(idx)
                st.rerun()


# ------------------------------------------------------------------
# Download builder
# ------------------------------------------------------------------

def _build_download_bytes(
    project,
    phrases: List[dict],
    plan: List[dict],
    *,
    blend_seams: bool = False,
    final_smooth: bool = False,
) -> bytes:
    """Apply all non-rejected transforms in plan order and return JSON bytes."""
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG

    with open(project.funscript_path, encoding="utf-8") as f:
        fs_data = json.load(f)

    rejected: set = st.session_state.get("export_rejected", set())
    result = copy.deepcopy(fs_data.get("actions", []))

    for entry in plan:
        if entry["phrase_idx"] in rejected:
            continue
        spec = TRANSFORM_CATALOG.get(entry["tx_key"])
        if not spec:
            continue

        start_ms     = entry["start_ms"]
        end_ms       = entry["end_ms"]
        param_values = entry["param_values"] or {}

        phrase_slice = [a for a in result if start_ms <= a["at"] <= end_ms]
        transformed  = spec.apply(phrase_slice, param_values if param_values else None)
        if not transformed:
            continue

        if spec.structural:
            outside = [a for a in result if not (start_ms <= a["at"] <= end_ms)]
            result  = sorted(outside + transformed, key=lambda a: a["at"])
        else:
            t_to_pos = {a["at"]: a["pos"] for a in transformed}
            for a in result:
                if a["at"] in t_to_pos:
                    a["pos"] = t_to_pos[a["at"]]

    if blend_seams:
        spec = TRANSFORM_CATALOG.get("blend_seams")
        if spec:
            result = spec.apply(result, None) or result

    if final_smooth:
        spec = TRANSFORM_CATALOG.get("final_smooth")
        if spec:
            result = spec.apply(result, None) or result

    out = dict(fs_data)
    out["actions"] = result
    return json.dumps(out, indent=2).encode()
