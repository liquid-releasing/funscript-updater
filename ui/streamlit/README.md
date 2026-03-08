# ui/streamlit — Streamlit UI

Interactive local app (and Streamlit Cloud deployable) for the Funscript Updater pipeline.

## Quick start

```bash
# From the project root
pip install -r ui/streamlit/requirements.txt
streamlit run ui/streamlit/app.py
```

Opens at `http://localhost:8501`.

## Layout

```
Sidebar                        Main area (tabs)
───────────────────────────    ──────────────────────────────────────
• File picker                  1. Assessment
• Load / Analyse button           Summary stats (8 metrics)
• Session summary                 Phases breakdown chart
• Add manual item form            Cycles → Patterns table
• Export buttons                  Phrases BPM timeline (SVG)
                                  BPM transitions table

                               2. Work Items
                                  Scrollable list of all sections
                                  Per-row type selector
                                  Edit button → selects for tab 3

                               3. Edit (detail panel)
                                  Time window editor
                                  Performance controls (sliders)
                                  Break controls (sliders)
                                  Raw preserve notice
                                  Neutral prompt

                               4. Export
                                  Window summary tables
                                  Write JSON files button
```

## Panels

Each panel is an independent module in `panels/`:

| Module | Tab | Responsibility |
|---|---|---|
| `panels/assessment.py` | Assessment | Read-only pipeline output display |
| `panels/work_items.py` | Work Items | Interactive section tagger |
| `panels/detail.py` | Edit | Editable controls for the selected item |

Panels do **not** hold state themselves — all state lives in
`st.session_state.project` (a `ui.common.project.Project` instance).

## Item types and their customizer tasks

| Type | Icon | Customizer task | Effect |
|---|---|---|---|
| Performance | 🔥 | Task 2 | Velocity limiting, reversal softening, position compression |
| Break | 🌊 | Task 3 | Amplitude reduction, centre pull |
| Raw | 🎯 | Task 4 | Copy original actions verbatim |
| Neutral | ⚪ | (none) | BPM-threshold transformer decides |

## Output files

All outputs go to `output/` (gitignored).

| File | Description |
|---|---|
| `<name>.assessment.json` | Assessment result (auto-saved on first load) |
| `<name>.performance.json` | Performance window list for customizer |
| `<name>.break.json` | Break window list |
| `<name>.raw.json` | Raw preserve window list |
| `<name>.project.json` | Full project state (work items + types + configs) |

## Extending

To add a new panel:
1. Create `panels/my_panel.py` with a `render(project)` function.
2. Import it in `app.py` and add a tab entry.

The `ui/common` layer handles all business logic; panels are purely
responsible for rendering and translating user gestures into
`project.*` method calls.
