"""Detail panel — editable view for the currently selected work item.

Renders different sub-panels depending on the item type:
  - Performance  → velocity / compression / smoothing controls
  - Break        → amplitude / smoothing controls
  - Raw          → preserve-original notice + time range only
  - Neutral      → time range + type prompt

All changes are written immediately to ``project.work_items`` via
``Project.update_item_config`` / ``Project.update_item_times``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from ui.common.work_items import ItemType, _BREAK_DEFAULTS, _PERF_DEFAULTS

if TYPE_CHECKING:
    from ui.common.project import Project


def render(project: "Project") -> None:
    """Render the detail panel for the selected work item."""
    if not project.selected_item_id:
        st.info("Select an item from the Work Items panel to edit it here.")
        return

    item = project.get_item(project.selected_item_id)
    if item is None:
        st.warning("Selected item not found.")
        return

    st.subheader(f"Edit — {item.start_ts} → {item.end_ts}")
    _render_time_editor(project, item)
    st.divider()

    if item.item_type == ItemType.PERFORMANCE:
        _render_performance_controls(project, item)
    elif item.item_type == ItemType.BREAK:
        _render_break_controls(project, item)
    elif item.item_type == ItemType.RAW:
        _render_raw_info(item)
    else:
        _render_neutral_prompt(item)


# ------------------------------------------------------------------
# Shared: time range editor
# ------------------------------------------------------------------


def _render_time_editor(project: "Project", item) -> None:
    st.markdown("**Time window**")
    c1, c2 = st.columns(2)

    if project.assessment:
        duration_ms = project.assessment.duration_ms
    else:
        duration_ms = item.end_ms + 1

    new_start = c1.number_input(
        "Start (ms)",
        min_value=0,
        max_value=duration_ms,
        value=item.start_ms,
        step=100,
        key=f"start_{item.id}",
    )
    new_end = c2.number_input(
        "End (ms)",
        min_value=0,
        max_value=duration_ms,
        value=item.end_ms,
        step=100,
        key=f"end_{item.id}",
    )
    if (new_start != item.start_ms or new_end != item.end_ms) and new_end > new_start:
        project.update_item_times(item.id, int(new_start), int(new_end))

    dur_s = (item.end_ms - item.start_ms) / 1000
    st.caption(f"Duration: {dur_s:.2f} s  |  {item.start_ts} → {item.end_ts}")

    label = st.text_input("Label (optional)", value=item.label, key=f"label_{item.id}")
    if label != item.label:
        item.label = label


# ------------------------------------------------------------------
# Performance controls
# ------------------------------------------------------------------


def _render_performance_controls(project: "Project", item) -> None:
    st.markdown("### Performance settings")
    st.caption(
        "Applied via the *performance* task of the WindowCustomizer.  "
        "Controls velocity limiting, reversal softening, and position compression."
    )
    cfg = item.config

    with st.expander("Velocity & reversals", expanded=True):
        max_vel = st.slider(
            "Max velocity",
            min_value=0.05, max_value=1.0, step=0.01,
            value=float(cfg.get("max_velocity", _PERF_DEFAULTS["max_velocity"])),
            key=f"max_vel_{item.id}",
            help="Cap on inter-action velocity.  Lower = smoother, slower-feeling.",
        )
        _apply(project, item, "max_velocity", max_vel)

        rev_soft = st.slider(
            "Reversal softening",
            min_value=0.0, max_value=1.0, step=0.01,
            value=float(cfg.get("reversal_soften", _PERF_DEFAULTS["reversal_soften"])),
            key=f"rev_soft_{item.id}",
            help="Blend factor at direction-reversal points (0 = no blend, 1 = full blend).",
        )
        _apply(project, item, "reversal_soften", rev_soft)

        ht_blend = st.slider(
            "Height blend at reversals",
            min_value=0.0, max_value=1.0, step=0.01,
            value=float(cfg.get("height_blend", _PERF_DEFAULTS["height_blend"])),
            key=f"ht_blend_{item.id}",
            help="How much to blend position values at reversal points.",
        )
        _apply(project, item, "height_blend", ht_blend)

    with st.expander("Position compression"):
        c1, c2 = st.columns(2)
        compress_bot = c1.number_input(
            "Bottom limit (0–100)",
            min_value=0, max_value=100,
            value=int(cfg.get("compress_bottom", _PERF_DEFAULTS["compress_bottom"])),
            step=1,
            key=f"comp_bot_{item.id}",
        )
        _apply(project, item, "compress_bottom", compress_bot)

        compress_top = c2.number_input(
            "Top limit (0–100)",
            min_value=0, max_value=100,
            value=int(cfg.get("compress_top", _PERF_DEFAULTS["compress_top"])),
            step=1,
            key=f"comp_top_{item.id}",
        )
        _apply(project, item, "compress_top", compress_top)

    with st.expander("Smoothing & jitter"):
        lpf = st.slider(
            "Low-pass filter strength",
            min_value=0.0, max_value=1.0, step=0.01,
            value=float(cfg.get("lpf_performance", _PERF_DEFAULTS["lpf_performance"])),
            key=f"lpf_perf_{item.id}",
            help="Smoothing applied after performance transform.  0 = none.",
        )
        _apply(project, item, "lpf_performance", lpf)

        jitter = st.number_input(
            "Timing jitter (ms)",
            min_value=0, max_value=50,
            value=int(cfg.get("timing_jitter_ms", _PERF_DEFAULTS["timing_jitter_ms"])),
            step=1,
            key=f"jitter_{item.id}",
            help="Random timing offset applied to actions (adds organic feel).",
        )
        _apply(project, item, "timing_jitter_ms", jitter)

    _render_reset_button(project, item)


# ------------------------------------------------------------------
# Break controls
# ------------------------------------------------------------------


def _render_break_controls(project: "Project", item) -> None:
    st.markdown("### Break settings")
    st.caption(
        "Applied via the *break* task of the WindowCustomizer.  "
        "Pulls motion toward the centre and reduces amplitude."
    )
    cfg = item.config

    amp_reduce = st.slider(
        "Amplitude reduction",
        min_value=0.0, max_value=1.0, step=0.01,
        value=float(cfg.get("break_amplitude_reduce", _BREAK_DEFAULTS["break_amplitude_reduce"])),
        key=f"amp_reduce_{item.id}",
        help="Fraction by which stroke amplitude is reduced.  0 = no change, 1 = flat.",
    )
    _apply(project, item, "break_amplitude_reduce", amp_reduce)

    lpf = st.slider(
        "Low-pass filter strength",
        min_value=0.0, max_value=1.0, step=0.01,
        value=float(cfg.get("lpf_break", _BREAK_DEFAULTS["lpf_break"])),
        key=f"lpf_break_{item.id}",
        help="Smoothing applied to the break section.  Higher = gentler fade.",
    )
    _apply(project, item, "lpf_break", lpf)

    _render_reset_button(project, item)


# ------------------------------------------------------------------
# Raw info
# ------------------------------------------------------------------


def _render_raw_info(item) -> None:
    st.markdown("### Raw preserve")
    st.info(
        "This section will be copied verbatim from the source funscript.  "
        "No transformation or customization is applied — original actions are preserved exactly."
    )
    st.caption(f"Window: {item.start_ts} → {item.end_ts}")


# ------------------------------------------------------------------
# Neutral prompt
# ------------------------------------------------------------------


def _render_neutral_prompt(item) -> None:
    st.markdown("### Neutral section")
    st.info(
        "This section is currently **neutral** — the BPM-threshold transformer will "
        "handle it automatically.  Use the type selector in the Work Items panel to "
        "tag it as Performance, Break, or Raw for manual control."
    )
    if item.bpm > 0:
        st.metric("Section BPM", f"{item.bpm:.1f}")


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------


def _apply(project: "Project", item, key: str, value) -> None:
    """Write a config value back if it changed."""
    if item.config.get(key) != value:
        project.update_item_config(item.id, key, value)


def _render_reset_button(project: "Project", item) -> None:
    st.divider()
    if st.button("Reset to defaults", key=f"reset_{item.id}"):
        item.set_type(item.item_type)   # rebuilds config from defaults
        st.rerun()
