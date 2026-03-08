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
  1. Assessment  — pipeline output inspection
  2. Work Items  — interactive section tagger
  3. Edit        — detail panel for the selected item
  4. Export      — summary of output files
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
from ui.common.work_items import ItemType, WorkItem
from ui.streamlit.panels import assessment as assessment_panel
from ui.streamlit.panels import detail as detail_panel
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

    # Check for a cached assessment JSON.
    base = os.path.splitext(selected_file)[0]
    cached_assessment = os.path.join(st.session_state.output_dir, f"{base}.assessment.json")
    use_cached = (
        os.path.exists(cached_assessment)
        and st.sidebar.checkbox("Use cached assessment", value=True)
    )

    if st.sidebar.button("Load / Analyse", type="primary"):
        with st.spinner("Running assessment…"):
            st.session_state.project = Project.from_funscript(
                funscript_path,
                existing_assessment_path=cached_assessment if use_cached else None,
            )
            if not use_cached:
                os.makedirs(st.session_state.output_dir, exist_ok=True)
                st.session_state.project.save_assessment(cached_assessment)
        st.success("Loaded!")
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

    tab_assessment, tab_work_items, tab_edit, tab_export = st.tabs(
        ["Assessment", "Work Items", "Edit", "Export"]
    )

    with tab_assessment:
        assessment_panel.render(project)

    with tab_work_items:
        work_items_panel.render(project)

    with tab_edit:
        detail_panel.render(project)

    with tab_export:
        _render_export_tab(project)


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
