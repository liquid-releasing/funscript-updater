"""assessment_nav.py — Assessment item navigator panel.

Shows a tabbed list of each assessment type (phases, cycles, patterns,
phrases, BPM transitions).  Clicking a row sets the ViewState selection
and zoom to that item's time range so all three viewer panels jump to it.
"""

from __future__ import annotations

from typing import Optional

from utils import ms_to_timestamp


def render(project, view_state) -> None:
    """Render the assessment navigator.

    Parameters
    ----------
    project:
        Loaded :class:`~ui.common.project.Project`.
    view_state:
        Shared :class:`~ui.common.view_state.ViewState` — updated in place
        when the user selects an item.
    """
    import streamlit as st

    if not project or not project.is_loaded:
        st.info("Load a funscript to use the navigator.")
        return

    ad = project.assessment.to_dict()

    tab_phases, tab_cycles, tab_patterns, tab_phrases, tab_trans = st.tabs([
        f"Phases ({len(ad.get('phases', []))})",
        f"Cycles ({len(ad.get('cycles', []))})",
        f"Patterns ({len(ad.get('patterns', []))})",
        f"Phrases ({len(ad.get('phrases', []))})",
        f"BPM Transitions ({len(ad.get('bpm_transitions', []))})",
    ])

    with tab_phases:
        _render_time_item_list(
            ad.get("phases", []),
            view_state,
            label_key="label",
            list_key="nav_phases",
        )

    with tab_cycles:
        _render_time_item_list(
            ad.get("cycles", []),
            view_state,
            label_key="label",
            extra_keys={"osc": "oscillations"},
            list_key="nav_cycles",
        )

    with tab_patterns:
        _render_pattern_list(ad.get("patterns", []), view_state)

    with tab_phrases:
        _render_time_item_list(
            ad.get("phrases", []),
            view_state,
            label_key="pattern_label",
            extra_keys={"bpm": "BPM"},
            list_key="nav_phrases",
        )

    with tab_trans:
        _render_transition_list(ad.get("bpm_transitions", []), view_state)


# ------------------------------------------------------------------
# List renderers
# ------------------------------------------------------------------

def _render_time_item_list(
    items: list,
    view_state,
    label_key: str = "label",
    extra_keys: Optional[dict] = None,
    list_key: str = "nav_list",
) -> None:
    """Generic renderer for items with start_ms / end_ms / label."""
    import streamlit as st

    if not items:
        st.caption("None detected.")
        return

    for i, item in enumerate(items):
        start = item.get("start_ms", 0)
        end   = item.get("end_ms",   0)
        label = item.get(label_key, "")
        duration = end - start

        extra = ""
        if extra_keys:
            parts = []
            for field, display in extra_keys.items():
                val = item.get(field)
                if val is not None:
                    if isinstance(val, float):
                        parts.append(f"{display}: {val:.1f}")
                    else:
                        parts.append(f"{display}: {val}")
            extra = "  |  " + "  ".join(parts) if parts else ""

        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                f"**{ms_to_timestamp(start)}** — {ms_to_timestamp(end)}"
                f"  `{duration:,} ms`  {label}{extra}"
            )
        with col2:
            if st.button("Focus", key=f"{list_key}_{i}"):
                _padding = min(500, duration // 10)
                view_state.set_zoom(
                    max(0, start - _padding),
                    end + _padding,
                )
                view_state.set_selection(start, end)
                import streamlit as st
                st.rerun()

        st.divider()


def _render_pattern_list(patterns: list, view_state) -> None:
    """Renderer for patterns (which contain a list of cycle ranges)."""
    import streamlit as st

    if not patterns:
        st.caption("None detected.")
        return

    for i, pt in enumerate(patterns):
        label      = pt.get("pattern_label", f"Pattern {i+1}")
        count      = pt.get("cycle_count", 0)
        avg_dur_ms = int(pt.get("avg_duration_ms", 0))
        cycles     = pt.get("cycles", [])

        with st.expander(f"{label}  ({count} cycles, ~{avg_dur_ms:,} ms each)"):
            for j, cy in enumerate(cycles):
                start = cy.get("start_ms", 0)
                end   = cy.get("end_ms",   0)
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f"Cycle {j+1}: **{ms_to_timestamp(start)}** — {ms_to_timestamp(end)}"
                    )
                with col2:
                    if st.button("Focus", key=f"nav_patterns_{i}_{j}"):
                        _padding = min(500, (end - start) // 10)
                        view_state.set_zoom(
                            max(0, start - _padding),
                            end + _padding,
                        )
                        view_state.set_selection(start, end)
                        import streamlit as st
                        st.rerun()


def _render_transition_list(transitions: list, view_state) -> None:
    """Renderer for BPM transition markers."""
    import streamlit as st

    if not transitions:
        st.caption("No significant BPM transitions detected.")
        return

    for i, tr in enumerate(transitions):
        at_ms    = tr.get("at_ms", 0)
        from_bpm = tr.get("from_bpm", 0)
        to_bpm   = tr.get("to_bpm",   0)
        pct      = tr.get("change_pct", 0)
        sign     = "+" if pct >= 0 else ""

        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                f"**{ms_to_timestamp(at_ms)}**  "
                f"{from_bpm:.0f} BPM → {to_bpm:.0f} BPM  "
                f"(`{sign}{pct:.1f}%`)"
            )
        with col2:
            if st.button("Focus", key=f"nav_trans_{i}"):
                _window = 5_000
                view_state.set_zoom(
                    max(0, at_ms - _window),
                    at_ms + _window,
                )
                view_state.set_selection(
                    max(0, at_ms - 500),
                    at_ms + 500,
                )
                import streamlit as st
                st.rerun()

        st.divider()
