# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Funscript Forge — Streamlit UI entry point.

Launch with:
    streamlit run ui/streamlit/app.py

Layout
------
Sidebar
  • File picker (test_funscript/*.original.funscript)
  • Assessment controls (run / load cached)
  • Export buttons

Main area  (tabs)
  1. Assessment        — pipeline output inspection
  2. Phrase Editor     — three-panel colour-coded chart with assessment navigator
  3. Pattern Behaviors — catalog of tagged phrase patterns
  4. Pattern Editor    — per-instance waveform shaping
  5. Transform Catalog — reference guide for all phrase transforms
  6. Export            — summary of output files
"""

from __future__ import annotations

import json
import os
import sys

# Ensure project root is importable from any working directory.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

# True when launched from launcher.py (desktop / PyInstaller).
# False when accessed via the web UI or plain `streamlit run`.
_IS_LOCAL = os.environ.get("FUNSCRIPT_FORGE_LOCAL") == "1"

from ui.common.project import Project
from ui.common.view_state import ViewState
from ui.common.work_items import ItemType, WorkItem  # WorkItem kept for sidebar manual-add
from ui.streamlit.panels import assessment as assessment_panel
from ui.streamlit.panels import catalog_view as catalog_view_panel
from ui.streamlit.panels import export_panel
from ui.streamlit.panels import pattern_editor as pattern_editor_panel
from ui.streamlit.panels import transform_catalog as transform_catalog_panel
from ui.streamlit.panels import viewer as viewer_panel

# ------------------------------------------------------------------
# Page config (must be the first Streamlit call)
# ------------------------------------------------------------------

_LOGO = os.path.join(_ROOT, "media", "funscriptforge.png")
st.set_page_config(
    page_title="Funscript Forge",
    page_icon=_LOGO if os.path.exists(_LOGO) else "🎵",
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

if "pattern_catalog" not in st.session_state:
    from catalog.pattern_catalog import PatternCatalog
    _catalog_path = os.path.join(_ROOT, "output", "pattern_catalog.json")
    st.session_state.pattern_catalog = PatternCatalog(_catalog_path)

if "view_state" not in st.session_state:
    st.session_state.view_state = ViewState()

if "proposed_actions" not in st.session_state:
    st.session_state.proposed_actions = None

if "last_loaded_file" not in st.session_state:
    st.session_state.last_loaded_file = None

if "large_funscript_threshold" not in st.session_state:
    st.session_state.large_funscript_threshold = 10_000

if "last_assessment_elapsed" not in st.session_state:
    st.session_state.last_assessment_elapsed = None

if "bpm_threshold" not in st.session_state:
    st.session_state.bpm_threshold = 120.0

if "last_loaded_cfg" not in st.session_state:
    st.session_state.last_loaded_cfg = None

# ------------------------------------------------------------------
# Local-mode helpers: recent-files list and path pickers
# ------------------------------------------------------------------

_RECENTS_FILE = "recent_funscripts.json"
_RECENTS_MAX  = 10


def _load_recents(output_dir: str) -> list[str]:
    """Load the list of recently used funscript paths from disk."""
    path = os.path.join(output_dir, _RECENTS_FILE)
    try:
        with open(path) as fh:
            data = json.load(fh)
        return [p for p in data if isinstance(p, str) and os.path.isfile(p)]
    except Exception:
        return []


def _save_recents(output_dir: str, file_path: str) -> None:
    """Prepend *file_path* to the recents list and persist."""
    recents = _load_recents(output_dir)
    if file_path in recents:
        recents.remove(file_path)
    recents.insert(0, file_path)
    recents = recents[:_RECENTS_MAX]
    path = os.path.join(output_dir, _RECENTS_FILE)
    os.makedirs(output_dir, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(recents, fh, indent=2)


_BROWSE_SENTINEL = "— enter a path below —"


def _funscript_picker_local(output_dir: str) -> str | None:
    """Local-mode funscript picker: selectbox of recents + text-input fallback.

    Returns the selected absolute path, or ``None`` if nothing valid is chosen.
    """
    st.sidebar.subheader("Funscript")
    recents = _load_recents(output_dir)
    options = recents + [_BROWSE_SENTINEL]
    sel = st.sidebar.selectbox(
        "Recent files",
        options=options,
        format_func=lambda p: os.path.basename(p) if p != _BROWSE_SENTINEL else p,
        key="local_funscript_sel",
        label_visibility="collapsed",
    )

    if sel == _BROWSE_SENTINEL:
        typed = st.sidebar.text_input(
            "Path to .funscript",
            key="local_funscript_typed",
            placeholder=r"C:\path\to\video.funscript",
            label_visibility="collapsed",
        ).strip()
        if not typed:
            st.sidebar.caption("Paste or type the full path to a .funscript file.")
            return None
        if not os.path.isfile(typed):
            st.sidebar.warning("File not found.")
            return None
        return typed

    return sel  # already validated by _load_recents


def _media_picker_local(funscript_path: str, output_dir: str) -> None:
    """Local-mode media picker: auto-detect by stem, or type a path manually."""
    # Auto-detect once per funscript switch.
    if st.session_state.get("media_auto_for") != funscript_path:
        from ui.streamlit.panels.media_player import find_matching_media, MEDIA_EXTS
        _auto = find_matching_media(funscript_path, os.path.dirname(funscript_path))
        if _auto:
            st.session_state["media_path"] = _auto
        st.session_state["media_auto_for"] = funscript_path

    # Show current media + clear button.
    _mp = st.session_state.get("media_path")
    if _mp and os.path.exists(_mp):
        _mc1, _mc2 = st.sidebar.columns([5, 1])
        _mc1.caption(f"🎵 {os.path.basename(_mp)}")
        if _mc2.button("✕", key="clear_media", help="Remove media"):
            st.session_state.pop("media_path", None)
            st.session_state.pop("media_auto_for", None)
            st.rerun()
        return  # don't show picker when a file is already loaded

    # Manual path entry.
    typed = st.sidebar.text_input(
        "Audio/video path (optional)",
        key="local_media_typed",
        placeholder=r"C:\path\to\video.mp4",
        label_visibility="collapsed",
    ).strip()
    if typed:
        if os.path.isfile(typed):
            st.session_state["media_path"] = typed
            st.rerun()
        else:
            st.sidebar.warning("Media file not found.")


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------


def _sidebar() -> None:
    _logo = os.path.join(_ROOT, "media", "funscriptforge.png")
    if os.path.exists(_logo):
        st.sidebar.image(_logo, width="stretch")
    else:
        st.sidebar.title("Funscript Forge")
    st.sidebar.markdown("---")

    # --- File picker: local path input or web upload ---
    output_dir = st.session_state.output_dir

    if _IS_LOCAL:
        funscript_path = _funscript_picker_local(output_dir)
        if funscript_path is None:
            return
        _media_picker_local(funscript_path, output_dir)
    else:
        # Web mode: file upload widgets (kept for the web UI deployment).
        st.sidebar.subheader("Funscript")
        uploaded = st.sidebar.file_uploader(
            "Upload a funscript",
            type=["funscript"],
            label_visibility="collapsed",
            help="Upload a .funscript file to analyse it.",
        )
        if uploaded is not None:
            uploads_dir = os.path.join(output_dir, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            save_path = os.path.join(uploads_dir, uploaded.name)
            with open(save_path, "wb") as _fh:
                _fh.write(uploaded.read())
            st.session_state["last_upload_name"] = uploaded.name

        media_uploaded = st.sidebar.file_uploader(
            "Upload audio/video for context playback",
            type=["mp3", "m4a", "wav", "ogg", "mp4", "mkv", "mov"],
            label_visibility="collapsed",
            help="Upload audio or video matching this funscript to enable playback while editing.",
        )
        if media_uploaded is not None:
            uploads_dir = os.path.join(output_dir, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            media_save_path = os.path.join(uploads_dir, media_uploaded.name)
            with open(media_save_path, "wb") as _mfh:
                _mfh.write(media_uploaded.read())
            st.session_state["media_path"] = media_save_path

        # Build candidate list: uploaded files first, then test_funscript/.
        _path_for: dict[str, str] = {}
        uploads_dir = os.path.join(output_dir, "uploads")
        if os.path.isdir(uploads_dir):
            for _f in sorted(os.listdir(uploads_dir)):
                if _f.endswith(".funscript"):
                    _path_for[f"[↑] {_f}"] = os.path.join(uploads_dir, _f)

        funscript_dir = os.path.join(_ROOT, "test_funscript")
        if os.path.isdir(funscript_dir):
            for _f in sorted(os.listdir(funscript_dir)):
                if _f.endswith(".funscript"):
                    _path_for[_f] = os.path.join(funscript_dir, _f)

        if not _path_for:
            st.sidebar.warning("No .funscript files found. Upload one above.")
            return

        candidate_labels = list(_path_for.keys())
        _default_idx = 0
        _last_upload  = st.session_state.get("last_upload_name")
        if _last_upload:
            _upload_label = f"[↑] {_last_upload}"
            if _upload_label in candidate_labels:
                _default_idx = candidate_labels.index(_upload_label)

        selected_label = st.sidebar.selectbox(
            "Select funscript",
            options=candidate_labels,
            index=_default_idx,
        )
        funscript_path = _path_for[selected_label]

        # Auto-detect media by stem in uploads dir.
        if st.session_state.get("media_auto_for") != funscript_path:
            from ui.streamlit.panels.media_player import find_matching_media
            _auto = find_matching_media(funscript_path, uploads_dir)
            if _auto:
                st.session_state["media_path"] = _auto
            st.session_state["media_auto_for"] = funscript_path

        _mp = st.session_state.get("media_path")
        if _mp and os.path.exists(_mp):
            _mc1, _mc2 = st.sidebar.columns([5, 1])
            _mc1.caption(f"🎵 {os.path.basename(_mp)}")
            if _mc2.button("✕", key="clear_media", help="Remove media"):
                st.session_state.pop("media_path", None)
                st.session_state.pop("media_auto_for", None)
                st.rerun()

    selected_file = os.path.basename(funscript_path)

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

    # --- Chart / transform settings ---
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
        bpm_threshold = st.number_input(
            "Transform BPM threshold",
            min_value=40,
            max_value=300,
            value=120,
            step=5,
            help=(
                "Phrases at or above this BPM are suggested the Amplitude Scale "
                "transform; phrases below are suggested Passthrough."
            ),
        )
    st.session_state.large_funscript_threshold = int(large_funscript_threshold)
    st.session_state.bpm_threshold = float(bpm_threshold)

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
        import time

        # Progress indicator (#14): sidebar placeholder shows current stage.
        _stage_ph = st.sidebar.empty()

        def _on_stage(stage: str) -> None:
            _stage_ph.caption(f"⟳ {stage}")

        with st.spinner("Running assessment…"):
            _t0 = time.time()
            st.session_state.project = Project.from_funscript(
                funscript_path,
                analyzer_config=analyzer_cfg,
                progress_callback=_on_stage,
            )
            st.session_state.last_assessment_elapsed = time.time() - _t0
            st.session_state.last_loaded_cfg  = cfg_key
            st.session_state.last_loaded_file = selected_file
            st.session_state.view_state       = ViewState()
            if _IS_LOCAL:
                _save_recents(output_dir, funscript_path)
            st.session_state.export_rejected  = set()
            st.session_state.export_accepted  = set()

            # Auto-update the pattern catalog with this funscript's tagged phrases
            try:
                _proj    = st.session_state.project
                _phrases = _proj.assessment.to_dict().get("phrases", [])
                _cat     = st.session_state.pattern_catalog
                _cat.add_assessment(
                    funscript_name=selected_file,
                    phrases=_phrases,
                    duration_ms=_proj.assessment.duration_ms,
                )
                _cat.save()
            except Exception:
                pass  # catalog update is best-effort; never block the UI

        _stage_ph.empty()
        st.rerun()

    st.sidebar.markdown("---")

    # --- Project state ---
    project: Project | None = st.session_state.project
    if project and project.is_loaded:
        s = project.summary()
        st.sidebar.markdown(f"**{s['name']}**")
        elapsed = st.session_state.last_assessment_elapsed
        timing_str = f"  |  assessed in {elapsed:.1f}s" if elapsed is not None else ""
        st.sidebar.caption(
            f"Duration: {s['duration']}  |  Avg BPM: {s['bpm']:.1f}{timing_str}\n\n"
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
        st.title("Funscript Forge")
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

    tab_assessment, tab_viewer, tab_catalog, tab_pattern, tab_transforms, tab_export = st.tabs(
        ["Assessment", "Phrase Editor", "Pattern Behaviors", "Pattern Editor", "Transform Catalog", "Export"]
    )

    with tab_assessment:
        assessment_panel.render(project)

    with tab_viewer:
        _render_viewer_tab(project)

    with tab_catalog:
        catalog_view_panel.render(project)

    with tab_pattern:
        pattern_editor_panel.render(project)

    with tab_transforms:
        transform_catalog_panel.render()

    with tab_export:
        export_panel.render(project)

    # Programmatic tab navigation: set st.session_state.goto_tab = <0-based index>
    # before calling st.rerun(); the JS below clicks the tab after DOM is ready.
    if "goto_tab" in st.session_state:
        tab_idx = st.session_state.pop("goto_tab")
        import streamlit.components.v1 as components
        components.html(
            f"""<script>
                (function() {{
                    var tabs = window.parent.document.querySelectorAll('[data-testid="stTab"]');
                    if (tabs[{tab_idx}]) tabs[{tab_idx}].click();
                }})();
            </script>""",
            height=0,
        )


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


# ------------------------------------------------------------------
# Entry
# ------------------------------------------------------------------

_sidebar()
_main()
