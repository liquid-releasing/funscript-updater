"""export_panel.py — Export tab: transform change log + download.

Shows every planned transform (manually applied in the Phrase Editor or
Pattern Editor, plus optionally the system-recommended transforms for
untouched phrases).  Each row in the log can be rejected with the trash
button.  The Download button builds and streams the edited funscript.
"""

from __future__ import annotations

import copy
import json
from typing import Dict, List, Optional

import streamlit as st

from utils import ms_to_timestamp

# Log table column widths and headers
_COL_W   = [0.4, 2.8, 1.0, 2.5, 2.0, 2.0, 1.5, 0.7]
_HEADERS = ["#", "Time", "Dur (s)", "Transform", "Source", "BPM", "Cycles", ""]


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

    # Persistent per-session rejected set; cleared when a new file is loaded
    if "export_rejected" not in st.session_state:
        st.session_state.export_rejected = set()

    # Build tag → [phrase-index, …] map for Pattern Editor transform lookup
    tag_to_idxs: Dict[str, List[int]] = {}
    for i, ph in enumerate(phrases):
        for tag in ph.get("tags", []):
            tag_to_idxs.setdefault(tag, []).append(i)

    # ----------------------------------------------------------------
    # Header controls
    # ----------------------------------------------------------------
    col_chk, col_dl = st.columns([5, 3])

    with col_chk:
        include_recommended = st.checkbox(
            "Include recommended transforms for untouched phrases",
            value=True,
            key="export_include_recommended",
        )
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

    # Build the plan now so the download button can use it
    plan = _build_plan(phrases, tag_to_idxs, include_recommended, bpm_threshold)

    with col_dl:
        active_entries = [
            e for e in plan
            if e["phrase_idx"] not in st.session_state.export_rejected
        ]
        if active_entries:
            dl_bytes = _build_download_bytes(
                project, phrases, plan,
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
    # Transform change log
    # ----------------------------------------------------------------
    _render_log(plan)


# ------------------------------------------------------------------
# Plan building
# ------------------------------------------------------------------

def _build_plan(
    phrases: List[dict],
    tag_to_idxs: Dict[str, List[int]],
    include_recommended: bool,
    bpm_threshold: float,
) -> List[dict]:
    """Return one plan-entry dict per phrase that will receive a transform."""
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

    plan: List[dict] = []

    for idx, phrase in enumerate(phrases):
        tx_key: Optional[str] = None
        param_values: dict = {}
        source: Optional[str] = None

        # 1. Phrase Editor (phrase_transform_{idx})
        phrase_tx = st.session_state.get(f"phrase_transform_{idx}", {})
        if phrase_tx.get("transform_key") and phrase_tx["transform_key"] != "passthrough":
            tx_key       = phrase_tx["transform_key"]
            param_values = phrase_tx.get("param_values", {})
            source       = "Phrase Editor"

        # 2. Pattern Editor (pe_transform_{tag}_{i})
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

        # 3. Recommended (untouched phrases only)
        if not tx_key and include_recommended:
            rec, rec_params = suggest_transform(phrase, bpm_threshold)
            if rec and rec != "passthrough":
                tx_key       = rec
                param_values = rec_params
                source       = "Recommended"

        if not tx_key:
            continue  # passthrough — nothing to log

        # Compute before/after BPM and cycle count
        old_bpm: float = phrase.get("bpm", 0.0)
        old_cycles: int = phrase.get("cycle_count") or 0

        if tx_key == "halve_tempo":
            new_bpm: Optional[float] = old_bpm / 2
            new_cycles: Optional[int] = old_cycles // 2
        else:
            new_bpm    = None   # unchanged
            new_cycles = None

        spec    = TRANSFORM_CATALOG.get(tx_key)
        tx_name = spec.name if spec else tx_key

        plan.append({
            "phrase_idx":  idx,
            "start_ms":    phrase["start_ms"],
            "end_ms":      phrase["end_ms"],
            "tx_key":      tx_key,
            "tx_name":     tx_name,
            "param_values": param_values,
            "source":      source,
            "old_bpm":     old_bpm,
            "new_bpm":     new_bpm,
            "old_cycles":  old_cycles,
            "new_cycles":  new_cycles,
        })

    return plan


# ------------------------------------------------------------------
# Log table
# ------------------------------------------------------------------

def _render_log(plan: List[dict]) -> None:
    rejected: set = st.session_state.export_rejected

    if not plan:
        st.info(
            "No transforms planned.  Edit phrases in the **Phrase Editor** or "
            "**Pattern Editor**, or enable **Include recommended transforms** above."
        )
        return

    active_count   = sum(1 for e in plan if e["phrase_idx"] not in rejected)
    rejected_count = len(plan) - active_count
    summary = f"{active_count} transform{'s' if active_count != 1 else ''} will be applied"
    if rejected_count:
        summary += f" &nbsp;·&nbsp; {rejected_count} rejected"
    st.caption(summary + " — click 🗑 to reject, ↩ to restore")

    # Header row
    hcols = st.columns(_COL_W)
    for hc, lbl in zip(hcols, _HEADERS):
        hc.caption(lbl)

    for entry in plan:
        idx      = entry["phrase_idx"]
        is_rej   = idx in rejected
        time_str = (
            f"{ms_to_timestamp(entry['start_ms'])} → "
            f"{ms_to_timestamp(entry['end_ms'])}"
        )
        dur_s = f"{(entry['end_ms'] - entry['start_ms']) / 1000:.1f}"

        # BPM: show arrow only when the transform changes tempo
        bpm_str = (
            f"{entry['old_bpm']:.1f} → {entry['new_bpm']:.1f}"
            if entry["new_bpm"] is not None
            else f"{entry['old_bpm']:.1f}"
        )
        # Cycles: same logic
        cyc_str = (
            f"{entry['old_cycles']} → {entry['new_cycles']}"
            if entry["new_cycles"] is not None
            else str(entry["old_cycles"])
        )

        rc = st.columns(_COL_W)
        if is_rej:
            _dim = lambda s: f"<span style='opacity:0.35'>{s}</span>"
            rc[0].markdown(_dim(f"<s>{idx + 1}</s>"), unsafe_allow_html=True)
            rc[1].markdown(_dim(time_str),             unsafe_allow_html=True)
            rc[2].markdown(_dim(dur_s),                unsafe_allow_html=True)
            rc[3].markdown(_dim(f"<s>{entry['tx_name']}</s>"), unsafe_allow_html=True)
            rc[4].markdown(_dim(entry["source"]),      unsafe_allow_html=True)
            rc[5].markdown(_dim(bpm_str),              unsafe_allow_html=True)
            rc[6].markdown(_dim(cyc_str),              unsafe_allow_html=True)
            if rc[7].button("↩", key=f"export_restore_{idx}", help="Restore"):
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
            if rc[7].button("🗑", key=f"export_reject_{idx}", help="Reject"):
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

    # Post-processing passes (applied to the full action list)
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
