# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""transform_picker.py — Reusable two-step transform selector for Streamlit panels.

Usage
-----
    from ui.streamlit.transform_picker import render_transform_picker

    chosen_key = render_transform_picker(
        prefix       = f"txpick_{phrase_idx}",
        param_prefix = f"param_{phrase_idx}",
        current_key  = "passthrough",
    )

The selected key is also stored in ``st.session_state[f"{prefix}_key"]`` so
that button callbacks running before re-render can read it.

Cleanup (Accept / Cancel)
--------------------------
    for k in list(st.session_state):
        if k.startswith(f"txpick_{phrase_idx}_") or k.startswith(f"param_{phrase_idx}_"):
            del st.session_state[k]
"""
from __future__ import annotations

from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _category_for_key(
    key: str,
    categories: dict[str, list[tuple[str, str]]],
) -> str:
    """Return the category name that contains *key*, else the first category."""
    for cat, pairs in categories.items():
        if any(k == key for k, _ in pairs):
            return cat
    return next(iter(categories))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_picker_key(prefix: str) -> str:
    """Return the currently selected transform key for a picker by reading its
    widget session-state directly.

    Call this **before** ``render_transform_picker()`` — e.g. when rendering a
    preview chart that appears above the picker in the layout.  Streamlit
    updates widget session-state keys at the start of every run, so this
    always reflects the user's latest selection even before the picker widget
    code executes.

    Returns ``"passthrough"`` when no selection has been made yet (first
    render or after a reset).
    """
    from pattern_catalog.phrase_transforms import get_transforms_by_category

    cat = st.session_state.get(f"{prefix}_cat")
    if cat is None:
        return "passthrough"

    categories = get_transforms_by_category()
    pairs = categories.get(cat, [])
    if not pairs:
        return "passthrough"

    sel_label = st.session_state.get(f"{prefix}_{cat}_sel")
    if sel_label is None:
        # Category just switched — default to first item in the new category
        return pairs[0][0]

    sel_map = {lbl: k for k, lbl in pairs}
    return sel_map.get(sel_label, "passthrough")

def render_transform_picker(
    prefix: str,
    param_prefix: str,
    current_key: str = "passthrough",
    transform_overrides: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> str:
    """Render a two-step transform selector (category pills + transform dropdown)
    followed by its parameter sliders.

    Parameters
    ----------
    prefix:
        Unique key prefix for the category radio and transform selectbox.
        Each category gets its own selectbox state so switching categories
        remembers the last selection per category.
    param_prefix:
        Prefix for parameter slider session-state keys: ``f"{param_prefix}_{pk}"``.
    current_key:
        Transform key to pre-select on first render (before any session state
        exists for this picker).  Ignored on subsequent renders — the stored
        widget state takes over.
    transform_overrides:
        ``{transform_key: {param_key: {"max_value": int, "step": int}}}`` —
        per-transform, per-param limits that override catalog defaults.
        Resolved after the transform is chosen, so no chicken-and-egg issue.

    Returns
    -------
    chosen_key : str
        The currently selected transform key.
    """
    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG, get_transforms_by_category

    transform_overrides = transform_overrides or {}
    categories = get_transforms_by_category()
    cat_names  = list(categories.keys())

    # Which category contains current_key? (used only for first-render index)
    default_cat     = _category_for_key(current_key, categories)
    default_cat_idx = cat_names.index(default_cat)

    # Step 1 — category radio (horizontal pills)
    chosen_cat = st.radio(
        "Category",
        options=cat_names,
        index=default_cat_idx,
        horizontal=True,
        key=f"{prefix}_cat",
        label_visibility="collapsed",
    )

    pairs  = categories[chosen_cat]
    keys   = [k for k, _ in pairs]
    labels = [lbl for _, lbl in pairs]

    # Step 2 — transform selectbox (one per category so state is independent)
    sel_idx = keys.index(current_key) if current_key in keys else 0
    chosen_label = st.selectbox(
        "Transform",
        options=labels,
        index=sel_idx,
        key=f"{prefix}_{chosen_cat}_sel",
        label_visibility="collapsed",
    )
    chosen_key = keys[labels.index(chosen_label)]

    # Persist chosen key for button callbacks
    st.session_state[f"{prefix}_key"] = chosen_key

    spec = TRANSFORM_CATALOG[chosen_key]
    if spec.description:
        st.caption(spec.description)

    # Resolve per-transform param overrides now that chosen_key is known
    ui_int_overrides = transform_overrides.get(chosen_key, {})

    # Clamp any stale session-state values before rendering sliders
    for pk, ov in ui_int_overrides.items():
        sk  = f"{param_prefix}_{pk}"
        cap = ov.get("max_value")
        if cap is not None and st.session_state.get(sk, 0) > cap:
            st.session_state[sk] = cap

    # Parameter sliders
    for pk, param in spec.params.items():
        sk        = f"{param_prefix}_{pk}"
        overrides = ui_int_overrides.get(pk, {})
        if param.type == "float":
            st.slider(
                param.label,
                min_value=float(param.min_val or 0.0),
                max_value=float(param.max_val or 1.0),
                value=float(param.default),
                step=float(param.step or 0.05),
                help=param.help or None,
                key=sk,
            )
        elif param.type == "int":
            st.slider(
                param.label,
                min_value=int(param.min_val or 0),
                max_value=int(overrides.get("max_value", param.max_val or 100)),
                value=int(param.default),
                step=int(overrides.get("step", param.step or 1)),
                help=param.help or None,
                key=sk,
            )

    return chosen_key
