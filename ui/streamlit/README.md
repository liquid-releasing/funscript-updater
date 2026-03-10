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
| Add manual item | Define a work item by typing start/end times (ms) and a type |
| Export window JSONs | Write `performance.json`, `break.json`, `raw.json` to `output/` |
| Save project | Write a full project snapshot to `output/<name>.project.json` |

Settings auto-apply when changed; the assessment reruns automatically.

---

## Tabs

### 1. Assessment

Full pipeline output for the loaded funscript.

- **Summary** — eight metrics: duration, average BPM, action count, phases, cycles, patterns, phrases, BPM transitions.
- **Phrases** — colour-coded BPM timeline strip + per-row table with **Focus** button (zooms Phrase Editor to that time range). Columns: #, Time, BPM, Duration, Description, Tags.
- **BPM Transitions** — step chart showing BPM at each phrase midpoint with transition markers + per-row table with **Focus** button.
- **Behavioral Patterns** — phrase-count bar chart per behavioral tag + per-row table with **Focus** button (switches to Pattern Editor). Columns: Tag, Description, Phrases, BPM range.
- **Phases** — collapsible expander with direction-breakdown bar chart and first 50 phases.

### 2. Phrase Editor

Full-funscript chart with phrase bounding boxes. When phrase transforms have been accepted the chart shows the edited funscript and a `💾 These edits have not been saved — ready for export.` banner appears.

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

- **✓ Accept** — stores the transform in session state and returns to the phrase selector (transforms persist until Cancel or re-analysis).
- **✕ Cancel** — discards all stored transforms and returns to the selector.
- **✂ Split phrase** — divides the current phrase into two at a cycle boundary.

  **How to split:**
  1. Click **✂ Split phrase** in the transform controls column.
  2. Split mode replaces the transform controls with a cycle slider labelled *Split on cycle (1–N)*.
  3. Drag the slider to the cycle where you want the split. The caption shows *"Splits between cycle N and N+1 · M:SS"* and a white dashed line appears on the original chart at that timestamp.
  4. Hover dots on the chart show the cycle number (`cycle N`) to help you orient.
  5. Click **✂ Split** to confirm. Two new phrases are created (A covers the first half, B the second); the view navigates to phrase A automatically.
  6. Click **Cancel split** at any time to exit split mode without making changes.

  Phrases with fewer than 2 detected cycles cannot be split by cycle — a warning is shown instead.
- Hovering a chart dot shows `t=… ms  pos=…  cycle N` for quick orientation.

### 3. Pattern Behaviors

Cross-funscript behavioral pattern catalog.

**This funscript section:**

- Gantt-style behavioral timeline (one row per tag)
- Tag summary table with **Sample** button (shows a live waveform preview) and **Open in Pattern Editor** button
- Per-tag stats: phrase count, BPM range, span range, centre, velocity

**Your library section:**

- Phrase counts and files indexed
- Tag frequency bar chart
- Aggregate stats table and per-file breakdown

The catalog is stored at `output/pattern_catalog.json` and auto-updated on each assessment.

### 4. Pattern Editor

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

**Layout:**

```text
[Left: tag buttons with counts]  [Right: detail area]
                                  ├─ Selector chart (all matching phrases;
                                  │    shows edited funscript when transforms
                                  │    are accepted — same 💾 banner as Phrase Editor)
                                  ├─ Instance table (Start, Duration, BPM,
                                  │    Span, Centre, Velocity, Apply checkbox)
                                  ├─ Prev / Next navigation
                                  ├─ Original chart  │  Preview chart
                                  └─ Transform controls + Apply / Apply to all
```

- **Apply checkbox** — uncheck to exclude an instance from the download build.
- **Apply** — apply to the current instance only and mark its work item Done.
- **Apply to all** — copy the current transform to every checked instance and mark all Done.
- **Build download** — compile all stored transforms into a downloadable funscript.

### 5. Transform Catalog

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

Each entry shows: description, best-fit behavioral tags, a parameter table, live sliders, and side-by-side Before/After charts that update as you adjust the sliders.

### 6. Export

Aggregates all applied transforms from both editors and produces a downloadable edited funscript.

**Preview chart** — a static, non-interactive chart at the top of the tab shows the full proposed export (all non-rejected, accepted transforms applied). Updates automatically when transforms are accepted, rejected, or restored.

**Options and download:**

- **Add blended seams to reduce abrupt style changes** — runs `blend_seams` over the full action list after all phrase transforms are applied.  Detects high-velocity jumps between differently-styled sections and applies a bilateral low-pass filter symmetrically at those seams, leaving normal strokes untouched.
- **Conduct final smooth for post process finishing** — runs `final_smooth` (a light LPF at strength 0.10) over the entire result as a final polish pass.  Applied after seam blending when both are enabled.
- **⬇ Download edited funscript** — builds the result from the current plan (phrase transforms → optional seam blend → optional final smooth) and streams it as a `.funscript` file; disabled when nothing is active.

**Completed transforms** (manually applied in Phrase Editor or Pattern Editor):

| Column | Description |
| --- | --- |
| # | Phrase number |
| Time | Start → End timestamp |
| Dur (s) | Duration in seconds |
| Transform | Name of the transform |
| Source | `Phrase Editor` or `Pattern Editor` |
| BPM | Phrase BPM; `old → new` when the transform changes tempo |
| Cycles | Cycle count; `old → new` when changed |
| 🗑 / ↩ | Reject a row (dims it with strikethrough) or restore it |

**Recommended transforms** (auto-suggested for untouched phrases):

Phrases with no manually-applied transform receive an auto-suggested transform from `suggest_transform()`. Tag-based rules take priority: `frantic` → Halve Tempo; `giggle`/`plateau`/`lazy` → Amplitude Scale (amplify to peak hi ≈ 65); `stingy` → Amplitude Scale (reduce to peak hi ≈ 65); `drift`/`half_stroke` → Recenter (50); `drone` → Beat Accent. Untagged phrases fall back to BPM rules: transition → Smooth; low BPM → Passthrough; narrow span → Normalize; high BPM → Amplitude Scale.

Recommended transforms are **not** exported unless explicitly accepted (✓ button). Once accepted the button shows ✅ (click to un-accept). Each row also has a ✏ edit button (opens Phrase Editor on that phrase) and 🗑 reject.

The rejected-phrase set clears automatically when a new funscript is loaded.

---

## Panels

Each panel is an independent module in `panels/`:

| Module | Responsibility |
| --- | --- |
| `panels/viewer.py` | Phrase Editor orchestration (full chart + phrase detail) |
| `panels/phrase_detail.py` | Phrase Detail panel (charts, transforms, apply) |
| `panels/assessment.py` | Assessment tab — pipeline output display |
| `panels/pattern_editor.py` | Behavioral pattern batch-fix editor |
| `panels/catalog_view.py` | Pattern Behaviors tab — cross-funscript catalog analytics |
| `panels/transform_catalog.py` | Transform Catalog tab — reference guide with live previews |
| `panels/export_panel.py` | Export tab — transform change log + download |

Panels do **not** hold state — all state lives in `st.session_state.project`
(a `ui.common.project.Project`) and `st.session_state.view_state`
(a `ui.common.view_state.ViewState`).

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

## Performance notes

- Detail charts compute colour data only for the visible window (not the full funscript).
- The fast rendering threshold controls when the phrase selector switches from per-segment coloured lines to a single grey line.
- Pattern Editor instance charts use minimal raw Plotly; original actions are cached in session state.
- Pattern Editor download bytes are built only on demand via **Build download**.
