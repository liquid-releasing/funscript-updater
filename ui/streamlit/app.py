"""Funscript Updater — Streamlit UI entry point.

Launch with:
    streamlit run ui/streamlit/app.py

Layout
------
Sidebar
  • File picker (test_funscript/*.original.funscript)
  • Assessment controls (run / load cached)
  • Export buttons

Main area  (tabs)
  1. Viewer      — three-panel colour-coded chart with assessment navigator
  2. Assessment  — pipeline output inspection
  3. Work Items  — interactive section tagger
  4. Edit        — detail panel for the selected item
  5. Export      — summary of output files
"""

from __future__ import annotations

import os
import sys

# Ensure project root is importable from any working directory.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from ui.common.project import Project
from ui.common.view_state import ViewState
from ui.common.work_items import ItemType, WorkItem
from ui.streamlit.panels import assessment as assessment_panel
from ui.streamlit.panels import assessment_nav as assessment_nav_panel
from ui.streamlit.panels import detail as detail_panel
from ui.streamlit.panels import viewer as viewer_panel
from ui.streamlit.panels import work_items as work_items_panel

# ------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ------------------------------------------------------------------

st.set_page_config(
    page_title="Funscript Updater",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# Session state initialisation
# ------------------------------------------------------------------

if "project" not in st.session_state:
    st.session_state.project: Project | None = None

if "output_dir" not in st.session_state:
    st.session_state.output_dir = os.path.join(_ROOT, "output")

if "view_state" not in st.session_state:
    st.session_state.view_state = ViewState()

if "proposed_actions" not in st.session_state:
    st.session_state.proposed_actions = None

if "last_loaded_file" not in st.session_state:
    st.session_state.last_loaded_file = None

if "large_funscript_threshold" not in st.session_state:
    st.session_state.large_funscript_threshold = 10_000

if "last_loaded_cfg" not in st.session_state:
    st.session_state.last_loaded_cfg = None

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------


def _sidebar() -> None:
    st.sidebar.title("Funscript Updater")
    st.sidebar.markdown("---")

    # --- File selection ---
    st.sidebar.subheader("Funscript")
    funscript_dir = os.path.join(_ROOT, "test_funscript")
    candidates = sorted(
        f for f in os.listdir(funscript_dir)
        if f.endswith(".funscript")
    ) if os.path.isdir(funscript_dir) else []

    if not candidates:
        st.sidebar.warning(f"No .funscript files found in {funscript_dir}")
        return

    selected_file = st.sidebar.selectbox(
        "Select funscript",
        options=candidates,
        index=0,
    )
    funscript_path = os.path.join(funscript_dir, selected_file)

    # --- Phrase detection parameters ---
    with st.sidebar.expander("Phrase detection settings", expanded=True):
        min_phrase_s = st.slider(
            "Min phrase length (s)", min_value=5, max_value=120, value=20, step=5,
            help="Phrases shorter than this are merged into a neighbour.",
        )
        amp_sensitivity = st.select_slider(
            "Amplitude sensitivity",
            options=["Low (0.35)", "Medium (0.30)", "High (0.25)"],
            value="Medium (0.30)",
            help="How much stroke-depth change triggers a new phrase.",
        )

    # --- Chart settings ---
    with st.sidebar.expander("Chart settings"):
        large_funscript_threshold = st.number_input(
            "Fast rendering threshold (actions)",
            min_value=100,
            max_value=100_000,
            value=10_000,
            step=500,
            help=(
                "Funscripts with more actions than this use a single grey "
                "connecting line for speed.  Smaller funscripts use per-segment "
                "coloured lines that match the dot colours."
            ),
        )
    st.session_state.large_funscript_threshold = int(large_funscript_threshold)

    amp_tol_map = {"Low (0.35)": 0.35, "Medium (0.30)": 0.30, "High (0.25)": 0.25}

    from assessment.analyzer import AnalyzerConfig
    analyzer_cfg = AnalyzerConfig(
        min_phrase_duration_ms=min_phrase_s * 1000,
        amplitude_tolerance=amp_tol_map[amp_sensitivity],
    )
    cfg_key = (funscript_path, min_phrase_s, amp_sensitivity)

    # Auto-load when the file or settings change.
    needs_load = (
        cfg_key != st.session_state.last_loaded_cfg
    )

    if needs_load or st.sidebar.button("Re-analyse", type="primary"):
        with st.spinner("Running assessment…"):
            st.session_state.project = Project.from_funscript(
                funscript_path,
                analyzer_config=analyzer_cfg,
            )
            st.session_state.last_loaded_cfg  = cfg_key
            st.session_state.last_loaded_file = selected_file
            st.session_state.view_state       = ViewState()
        st.rerun()

    st.sidebar.markdown("---")

    # --- Project state ---
    project: Project | None = st.session_state.project
    if project and project.is_loaded:
        s = project.summary()
        st.sidebar.markdown(f"**{s['name']}**")
        st.sidebar.caption(
            f"Duration: {s['duration']}  |  Avg BPM: {s['bpm']:.1f}\n\n"
            f"{s['phrases']} phrases  •  {s['bpm_transitions']} transitions"
        )

        # Work item type summary.
        type_counts = {}
        for item in project.work_items:
            type_counts[item.item_type] = type_counts.get(item.item_type, 0) + 1
        if type_counts:
            summary_lines = [f"**Work items ({len(project.work_items)})**"]
            icons = {ItemType.PERFORMANCE: "🔥", ItemType.BREAK: "🌊",
                     ItemType.RAW: "🎯", ItemType.NEUTRAL: "⚪"}
            for itype, count in sorted(type_counts.items(), key=lambda x: x[0].value):
                summary_lines.append(f"{icons[itype]} {itype.value.title()}: {count}")
            st.sidebar.markdown("\n\n".join(summary_lines))

        st.sidebar.markdown("---")

        # --- Manual item ---
        with st.sidebar.expander("Add manual item"):
            m_start = st.number_input("Start (ms)", min_value=0, value=0, step=1000, key="m_start")
            m_end = st.number_input("End (ms)", min_value=0, value=10000, step=1000, key="m_end")
            m_type = st.selectbox(
                "Type",
                options=["Performance", "Break", "Raw", "Neutral"],
                key="m_type",
            )
            m_label = st.text_input("Label", key="m_label")
            if st.button("Add item"):
                type_map = {
                    "Performance": ItemType.PERFORMANCE,
                    "Break": ItemType.BREAK,
                    "Raw": ItemType.RAW,
                    "Neutral": ItemType.NEUTRAL,
                }
                project.add_item(WorkItem(
                    start_ms=int(m_start), end_ms=int(m_end),
                    item_type=type_map[m_type], label=m_label, source="manual",
                ))
                st.rerun()

        st.sidebar.markdown("---")

        # --- Export ---
        st.sidebar.subheader("Export")
        if st.sidebar.button("Export window JSONs"):
            written = project.export_windows(st.session_state.output_dir)
            if written:
                st.sidebar.success("Written:\n" + "\n".join(written.values()))
            else:
                st.sidebar.info("No typed items to export yet.")

        project_save_path = os.path.join(
            st.session_state.output_dir, f"{project.name}.project.json"
        )
        if st.sidebar.button("Save project"):
            project.export_project(project_save_path)
            st.sidebar.success(f"Saved to {project_save_path}")


# ------------------------------------------------------------------
# Main area
# ------------------------------------------------------------------


def _main() -> None:
    project: Project | None = st.session_state.project

    if project is None or not project.is_loaded:
        st.title("Funscript Updater")
        st.markdown(
            "Use the **sidebar** to select a funscript and click **Load / Analyse** "
            "to begin.  The assessment pipeline will detect phases, cycles, patterns, "
            "and phrases, then present them as interactive work items for you to review."
        )
        st.divider()
        st.markdown(
            "### Pipeline\n"
            "1. **Assess** — structural analysis (phases → cycles → patterns → phrases)\n"
            "2. **Work Items** — review and tag detected sections\n"
            "3. **Edit** — fine-tune per-section settings\n"
            "4. **Export** — write JSON window files for the customizer\n"
        )
        return

    tab_viewer, tab_assessment, tab_nav, tab_work_items, tab_edit, tab_export = st.tabs(
        ["Phrase Selector", "Assessment", "Navigator", "Work Items", "Edit", "Export"]
    )

    with tab_viewer:
        _render_viewer_tab(project)

    with tab_assessment:
        assessment_panel.render(project)

    with tab_nav:
        st.subheader("Assessment Navigator")
        assessment_nav_panel.render(project, view_state=st.session_state.view_state)

    with tab_work_items:
        work_items_panel.render(project)

    with tab_edit:
        detail_panel.render(project)

    with tab_export:
        _render_export_tab(project)


def _render_viewer_tab(project: Project) -> None:
    view_state = st.session_state.view_state
    viewer_panel.render(project, view_state, large_funscript_threshold=st.session_state.large_funscript_threshold)


def _commit_actions(project: Project, committed_actions: list) -> None:
    """Replace the project's funscript data with committed_actions and re-assess."""
    import json
    import tempfile
    import streamlit as st

    with tempfile.NamedTemporaryFile(
        suffix=".funscript", delete=False, mode="w"
    ) as tmp:
        with open(project.funscript_path) as src:
            data = json.load(src)
        data["actions"] = committed_actions
        json.dump(data, tmp)
        tmp_path = tmp.name

    with st.spinner("Re-assessing…"):
        updated = Project.from_funscript(tmp_path)
        # Carry the funscript path back so future loads still work
        updated.funscript_path = project.funscript_path
        st.session_state.project = updated
        st.session_state.proposed_actions = None
        st.session_state.view_state = ViewState()

    os.unlink(tmp_path)
    st.success("Committed. Assessment rebuilt.")
    st.rerun()


def _render_export_tab(project: Project) -> None:
    st.subheader("Export")

    typed = [w for w in project.work_items if w.item_type != ItemType.NEUTRAL]
    if not typed:
        st.info("Tag some work items as Performance, Break, or Raw first.")
        return

    for itype, label, icon in [
        (ItemType.PERFORMANCE, "Performance", "🔥"),
        (ItemType.BREAK, "Break", "🌊"),
        (ItemType.RAW, "Raw", "🎯"),
    ]:
        items = [w for w in project.work_items if w.item_type == itype]
        if items:
            st.markdown(f"**{icon} {label} windows ({len(items)})**")
            rows = [{"start": w.start_ts, "end": w.end_ts, "label": w.label or "—"} for w in items]
            import pandas as pd
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.divider()
    if st.button("Write JSON files", type="primary"):
        written = project.export_windows(st.session_state.output_dir)
        if written:
            for type_name, path in written.items():
                st.success(f"{type_name}: `{path}`")
        else:
            st.warning("Nothing to export.")


# ------------------------------------------------------------------
# Entry
# ------------------------------------------------------------------

_sidebar()
_main()
