# ui/streamlit — Streamlit UI

Interactive local app for reviewing, editing, and exporting funscript transforms.

## Quick start

```bash
# From the project root
pip install -r ui/streamlit/requirements.txt

# Desktop launcher (recommended)
python launcher.py

# Or run directly
streamlit run ui/streamlit/app.py
```

Opens at `http://localhost:8501`.

## Local mode vs web mode

`launcher.py` sets `FUNSCRIPT_FORGE_LOCAL=1` and starts a local HTTP media
server on a second port. In this mode:

- File paths are entered directly (no upload needed)
- Recent files are remembered across sessions (`output/recent_funscripts.json`)
- Audio/video streams directly from disk — no base64 encoding, no file size limit
- Media files are validated against magic-byte signatures before loading

Without the launcher (or when deployed to the cloud), the app falls back to
`st.file_uploader` for both funscript and media files.

---

## Sidebar

| Control | Description |
| --- | --- |
| Funscript picker | Recently used files dropdown + path input (local) or file uploader (web) |
| Media file | Path input (local) or file uploader (web) for audio/video |
| Min phrase length | Shortest allowed phrase (s); shorter phrases are merged |
| Amplitude sensitivity | How much stroke-depth change triggers a new phrase boundary |
| Fast rendering threshold | Funscripts above this action count use a grey line for speed |
| Transform BPM threshold | Phrases at or above this BPM receive the Amplitude Scale suggestion |
| Re-analyse | Force a fresh assessment with the current settings |
| ↩ Undo / ↪ Redo | 50-level undo/redo; tooltip shows the operation label. See [UNDO.md](UNDO.md). |
| Add manual item | Define a work item by typing start/end times (ms) and a type |
| Export window JSONs | Write `performance.json`, `break.json`, `raw.json` to `output/` |
| Save project | Write a full project snapshot to `output/<name>.project.json` |

Settings auto-apply when changed; the assessment reruns automatically.

---

## Welcome screen

Shown before any funscript is loaded:

- Wide wordmark logo + cinematic forge banner
- Icon row: Phrase Selector (anvil) / Pattern Editor (worktable) / Transform Catalog (oven)
- "How to get started" steps and "What the assessment detects" table

---

## Tabs

### 0. Phrase Selector

Full-funscript chart with phrase bounding boxes. When phrase transforms have been
accepted the chart shows the edited funscript and a `💾 These edits have not been
saved — ready for export.` banner appears.

**Navigation:**

- **⏮ Prev / Next ⏭** — step through phrases.
- **P1, P2, …** — jump directly to any phrase.
- Click a point on the chart to select that phrase.

**Phrase Detail panel** (appears when a phrase is selected):

```text
┌──────────────────────────────┬─────────────────────┐
│  Original chart              │  ⏮ Prev    Next ⏭   │
│  (hover dot = cycle number)  │  Transform controls  │
├──────────────────────────────│  ✂ Split phrase      │
│  Preview — {Transform Name}  │  ──────────────────  │
│  Preview chart               │  ✓ Accept  ✕ Cancel  │
│  Position stats table        │                      │
└──────────────────────────────┴─────────────────────┘
```

- **✓ Accept** — stores the transform in session state and returns to the selector.
- **✕ Cancel** — discards only the current phrase's proposed transform.
- **✂ Split phrase** — divides the phrase at a cycle boundary.

**Assessment details expander** (below the chart):

Full pipeline output for the loaded funscript:

- **Summary** — eight metrics: duration, average BPM, action count, phases, cycles, patterns, phrases, BPM transitions.
- **Phrases** — colour-coded BPM timeline + per-row table with **Focus** button.
- **BPM Transitions** — step chart with transition markers + per-row table with **Focus** button.
- **Behavioral Patterns** — phrase-count bar chart per tag + per-row table with **Focus in Pattern Editor** button.
- **Phases** — collapsible expander with direction-breakdown bar chart and first 50 phases.

### 1. Pattern Editor

Behavioral pattern batch-fix workspace. Phrases are pre-classified into 8 behavioral tags:

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

**Pattern Behaviors catalog expander** (at the top):

- Gantt-style behavioral timeline (one row per tag)
- Tag summary table with **Sample** button and **Focus in Pattern Editor** button
- Library aggregate stats

**Editor layout:**

```text
[Left: tag buttons with counts]  [Right: detail area]
                                  ├─ Selector chart (all matching phrases)
                                  ├─ Instance table (Start, Duration, BPM, Span, Centre, Velocity)
                                  ├─ Prev / Next navigation
                                  ├─ Original chart  │  Preview chart
                                  └─ Transform controls + Apply / Apply to all
```

- **Apply** — apply to the current instance only and mark its work item Done.
- **Apply to all** — copy the current transform (and split structure, scaled proportionally) to every instance and mark all Done.
- **Build download** — compile all stored transforms into a downloadable funscript.

### 2. Transform Catalog

Reference guide for all 17 phrase transforms, grouped by capability:

| Group | Transforms |
| --- | --- |
| Passthrough | passthrough |
| Amplitude Shaping | amplitude_scale, normalize, boost_contrast |
| Position Adjustment | shift, recenter, clamp_upper, clamp_lower, invert |
| Smoothing & Filtering | smooth, blend_seams, final_smooth |
| Break / Recovery | break |
| Performance / Device Realism | performance |
| Rhythmic Patterns | beat_accent, three_one |
| Structural — Tempo | halve_tempo |

Each entry shows: description, best-fit behavioral tags, a parameter table, live sliders, and side-by-side Before/After charts.

### 3. Export

Aggregates all applied transforms and produces a downloadable edited funscript.

**Preview chart** — static chart showing the full proposed export. Updates automatically.

**Completed transforms** (manually applied in either editor):

| Column | Description |
| --- | --- |
| # | Phrase number |
| Time | Start → End timestamp |
| Dur (s) | Duration in seconds |
| Transform | Name of the transform |
| Source | `Phrase Editor` or `Pattern Editor` |
| BPM | Phrase BPM; `old → new` when the transform changes tempo |
| Cycles | Cycle count; `old → new` when changed |
| 🗑 / ↩ | Reject a row or restore it |

**Recommended transforms** — auto-suggested for untouched phrases. Not included in
the export unless explicitly accepted (✓ button).

**Options:**

- **Add blended seams** — bilateral LPF at high-velocity style boundaries.
- **Final smooth** — light global LPF (strength 0.10) as a finishing pass.
- **⬇ Download edited funscript** — builds and streams the result.

---

## Panels

Each panel is an independent module in `panels/`:

| Module | Responsibility |
| --- | --- |
| `panels/viewer.py` | Phrase Selector tab — full chart + phrase detail |
| `panels/phrase_detail.py` | Phrase Detail panel (charts, transforms, apply) |
| `panels/assessment.py` | Assessment details expander content |
| `panels/pattern_editor.py` | Pattern Editor tab — behavioral batch-fix editor |
| `panels/catalog_view.py` | Pattern Behaviors catalog expander content |
| `panels/transform_catalog.py` | Transform Catalog tab — reference guide with live previews |
| `panels/export_panel.py` | Export tab — transform change log + download |
| `panels/media_player.py` | Audio/video player with phrase restriction and corruption check |

Panels do **not** hold state — all state lives in `st.session_state.project`
and `st.session_state.view_state`.

## Output files

All outputs go to `output/` (gitignored).

| File | Description |
| --- | --- |
| `<name>_edited.funscript` | Export tab download (all applied transforms) |
| `<name>_pattern_edited.funscript` | Pattern Editor download |
| `<name>.performance.json` | Performance window list for customizer |
| `<name>.break.json` | Break window list |
| `<name>.raw.json` | Raw preserve window list |
| `<name>.project.json` | Full project state (work items + types + configs) |
| `pattern_catalog.json` | Persistent cross-funscript behavioral pattern catalog |
| `recent_funscripts.json` | Recently opened file paths (local mode only) |

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).  Written by human and Claude AI (Claude Sonnet).*
