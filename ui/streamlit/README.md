# ui/streamlit — Streamlit UI

Interactive local app for reviewing, editing, and exporting funscript transforms.

## Quick start

```bash
# From the project root
pip install -r ui/streamlit/requirements.txt
streamlit run ui/streamlit/app.py
```

Opens at `http://localhost:8501`.

## Sidebar

| Control | Description |
| --- | --- |
| Funscript selector | Pick a `.funscript` file from `test_funscript/` |
| Min phrase length | Shortest allowed phrase (s); shorter phrases are merged |
| Amplitude sensitivity | How much stroke-depth change triggers a new phrase boundary |
| Fast rendering threshold | Funscripts above this action count use a grey line for speed |
| Transform BPM threshold | Phrases at or above this BPM receive the Amplitude Scale suggestion |
| Re-analyse | Force a fresh assessment with the current settings |

Settings auto-apply when changed; the assessment reruns automatically.

## Tabs

### 1. Phrase Selector

The primary workspace.  Shows the full funscript as a colour-coded chart
(velocity or amplitude mode) with phrase bounding boxes overlaid.

#### Selecting a phrase

- Click anywhere inside a phrase box on the chart, or
- Click a numbered phrase button (P1, P2, …) below the chart.

Once a phrase is selected the chart is hidden and the **Phrase Detail** panel
appears in its place.

#### Chart controls (visible in selector mode only)

| Control | Effect |
| --- | --- |
| Color mode radio | Switch between velocity and amplitude colouring |
| From / To text inputs | Type a timestamp (`M:SS`) to jump to a time range |
| ◀ / ▶ | Scroll left / right by one-third of the current window |
| All | Reset zoom to show the full funscript |
| ＋ / － | Zoom in / out (halve or double the time window) |

#### Large funscript rendering

Funscripts above the fast rendering threshold (default: 10 000 actions) use a
single grey connecting line for speed; smaller funscripts use per-segment
coloured lines that match the dot colours.

---

### Phrase Detail (replaces Phrase Selector when a phrase is selected)

```text
┌─────────────────────────────────┬──────────────┐
│  P{N} — Phrase Detail           │              │
│  Original chart (fixed x-axis)  │  Transform   │
├─────────────────────────────────│  controls    │
│  Preview — {Transform Name}     │              │
│  Preview chart (fixed x-axis)   │  ⏮ Prev      │
│  [position stats table]         │     Next ⏭   │
│  *(not saved)*                  │  ── divider ─│
│                                 │  💾 Save      │
└─────────────────────────────────│  ✕ Cancel    │
                                  └──────────────┘
```

**Original chart** — the phrase as it exists in the loaded funscript.

**Preview chart** — live preview with the selected transform applied.  Only the
phrase slice is transformed; surrounding context uses original positions.

Both charts:

- Share the same fixed x-axis width (based on the longest phrase in the file
  so stroke velocity is visually comparable across all phrases).
- Show the selected phrase at full brightness; surrounding context is dimmed.
- Have the modebar removed — the timescale cannot be accidentally changed.

#### Position stats table (below the preview chart)

| Column | Meaning |
| --- | --- |
| Min | Lowest position value in the preview phrase slice |
| Max | Highest position value |
| Range | Max − Min (stroke depth indicator) |
| Mean | Average position |
| Actions | Number of actions in the phrase |

#### Transform controls

Choose from the catalog of named transforms.  The rule-based suggestion for
the phrase is shown in a caption; the selectbox defaults to Passthrough so
the user starts with no change applied.

Transforms with parameters expose sliders that update the preview in real time.

| Transform | Effect |
| --- | --- |
| Passthrough | No change |
| Amplitude Scale | Scale stroke depth around midpoint (50) |
| Normalize Range | Expand positions to fill a target range |
| Smooth | Low-pass filter to reduce jitter |
| Clamp Upper Half | Compress into 50–100 zone |
| Clamp Lower Half | Compress into 0–50 zone |
| Invert | Mirror positions around 50 |
| Boost Contrast | Push toward 0 and 100 extremes |

#### Navigation

- ⏮ Prev / Next ⏭ — move to the previous or next phrase (transform choices are
  remembered per phrase within the session).

#### Save / Cancel

- 💾 **Save** — applies all stored per-phrase transforms (across the entire
  funscript), downloads the result as `{name}.edited.funscript`, and returns
  to the phrase selector.  The original file is never modified.
- ✕ **Cancel** — discards all stored transforms and returns to the phrase
  selector without downloading.

---

### 2. Assessment

Read-only display of the pipeline output: summary metrics, phase breakdown,
cycle → pattern table, phrase BPM timeline, and BPM transition table.

### 3. Navigator

Assessment navigator: scroll through phases, cycles, patterns, and phrases
with linked chart highlighting.

### 4. Work Items

Scrollable list of all detected sections.  Each row shows time range, BPM,
and a type selector (Performance / Break / Raw / Neutral).  Click **Edit** to
open the detail panel for that item.

### 5. Edit

Detail panel for the selected work item.  Shows type-specific controls
(performance velocity limits, break amplitude settings, etc.).

### 6. Pattern Editor

Behavioral pattern batch-fix workspace.  Phrases are pre-classified by
`assessment/classifier.py` into 8 behavioral tags:

| Tag | Problem | Suggested transform |
| --- | --- | --- |
| Stingy | Full-range, high-speed, no nuance | performance |
| Giggle | Tiny centred micro-motion | normalize |
| Plateau | Small amplitude, dead-centre | amplitude_scale |
| Drift | Centre of gravity displaced off-centre | recenter |
| Half Stroke | Real motion confined to one half of range | recenter |
| Drone | Long monotone repeat, no variation | beat_accent |
| Lazy | Slow and shallow | amplitude_scale |
| Frantic | BPM > 200, near device limit | halve_tempo |

#### Layout

```text
[Left: tag buttons with counts]  [Right: detail area]
                                  ├─ Selector chart (full funscript,
                                  │    matching phrases highlighted)
                                  ├─ Instance table (Start, Duration, BPM,
                                  │    Span, Centre, Velocity, Apply checkbox)
                                  ├─ Original chart │ Preview chart │ Controls
                                  └─ Finalize options + Build download
```

- **Apply checkbox** (default checked) — uncheck to exclude an instance from the download build.
- **Apply to all** — copy the current transform + params to every instance.
- **Build download** — compiles all stored transforms + finalize passes into a downloadable funscript.  Only runs on demand (not on every slider tick).

### 7. Catalog

Read-only analytics across all assessed funscripts.

#### This funscript section

- Gantt-style behavioral timeline: one row per tag, bars show where each pattern appears
- Tag summary table: phrase count, BPM range, span range, centre, velocity, suggested fix
- Sample chart: click a table row to see the first matching phrase's motion + metrics

#### Your library section

- Phrase counts and files indexed
- Tag frequency bar chart
- Aggregate stats table (BPM/span/velocity ranges per tag)
- Per-file breakdown expander

The catalog is stored at `output/pattern_catalog.json` and auto-updated whenever a funscript is analysed.

### 8. Export

Summary tables of typed work items and a button to write JSON window files
for the downstream customizer pipeline.

## Panels

Each panel is an independent module in `panels/`:

| Module | Responsibility |
| --- | --- |
| `panels/viewer.py` | Phrase Selector + Phrase Detail orchestration |
| `panels/phrase_detail.py` | Phrase Detail panel (charts, transforms, save/cancel) |
| `panels/assessment.py` | Read-only pipeline output display |
| `panels/assessment_nav.py` | Assessment navigator |
| `panels/work_items.py` | Interactive section tagger |
| `panels/detail.py` | Editable controls for the selected work item |
| `panels/pattern_editor.py` | Behavioral pattern batch-fix editor |
| `panels/catalog_view.py` | Cross-funscript pattern catalog analytics |

Panels do **not** hold state — all state lives in `st.session_state.project`
(a `ui.common.project.Project`) and `st.session_state.view_state`
(a `ui.common.view_state.ViewState`).

## Output files

All outputs go to `output/` (gitignored).

| File | Description |
| --- | --- |
| `<name>.edited.funscript` | User-edited funscript (downloaded via Save button) |
| `<name>_pattern_edited.funscript` | Pattern Editor download |
| `<name>.performance.json` | Performance window list for customizer |
| `<name>.break.json` | Break window list |
| `<name>.raw.json` | Raw preserve window list |
| `<name>.project.json` | Full project state (work items + types + configs) |
| `pattern_catalog.json` | Persistent cross-funscript behavioral pattern catalog |

## Performance notes

- The phrase selector chart is hidden while a phrase is selected — no chart
  redraw overhead during editing.
- Detail charts compute colour data only for the visible window (not the full
  funscript) so they render quickly even for long files.
- The fast rendering threshold in the sidebar controls when the phrase selector
  switches from per-segment coloured lines to a single grey line.
- Pattern Editor instance charts use minimal raw Plotly (no amplitude
  colour calculation); original actions are cached in session state.
- Pattern Editor download bytes are built only on demand via **Build download**.
