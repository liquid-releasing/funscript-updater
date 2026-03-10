# funscript-forge

![Funscript Forge](media/funscriptforge-logo-wide.png)

A structure-aware post-processor for funscripts. It analyzes the motion
structure of an existing script, lets you review and tag sections through an
interactive UI, and generates an improved script with smoother defaults,
expressive performance sections, and gentle breaks.

---

## Features

### Analysis

- Structural analysis: phases → cycles → patterns → phrases → BPM transitions
- Behavioral classification into 8 tags (stingy, giggle, plateau, drift, half-stroke, drone, lazy, frantic)
- Duration-based phrase splitting for uniform-tempo funscripts (no more single-phrase output on long uniform files)
- Real-time progress indicator shows each pipeline stage as it runs
- Cross-funscript pattern catalog — accumulates stats across all analysed files (persistent JSON)

### Phrase Selector (Streamlit UI)

- Full-funscript colour-coded chart with phrase bounding boxes; click any phrase to open its detail panel
- Per-phrase transform selection with live parameter sliders and Before / After preview
- Cycle-based phrase split — slider selects the split boundary; a dashed line marks it on the chart; hover any dot to see its cycle number
- ✓ Accept stores the transform in session state; ✕ Cancel discards only the current phrase's pending change
- Selector chart shows the accumulated edited funscript (with banner) once any transform has been accepted

### Pattern Editor (Streamlit UI)

- Select phrases by behavioral tag; view all matching instances at once
- Per-instance transform + per-segment split (split into non-overlapping sub-ranges, each with its own transform)
- Apply to all — copies the current instance's transform (or split structure, scaled proportionally) to every other instance of the same tag
- Selector chart also reflects accepted phrase-editor transforms

### Audio / Video Player

- Phrase-restricted HTML5 player embedded in the sidebar — plays only the currently selected phrase window
- Animated red playhead overlaid on the waveform chart; Back 5 s / Forward 5 s controls
- **📌 Set split here** — click during playback to send the current timestamp to the Pattern Editor as a split point
- Local mode: media streams directly from disk at full quality (no file size limit, no upload wait)
- Web mode: media uploaded via browser and encoded inline; no server required
- Magic-byte validation on all 10 supported types (MP3, MP4, M4A, MOV, WAV, OGG, WebM, MKV, AAC, AVI)

### Export (Streamlit UI)

- Static preview chart at the top shows the full proposed export
- Completed transforms (from Phrase Editor or Pattern Editor) listed with reject / restore per row
- Recommended transforms (tag-aware auto-suggestions) listed separately; each must be explicitly accepted before it is included in the download
- Optional post-processing: blend seams (bilateral LPF at high-velocity style boundaries) and final smooth (light global LPF)
- **Output integrity** — all positions clamped to [0, 100] and timestamps sorted/deduplicated automatically; warning shown if any actions were clamped
- **Export log** — every downloaded funscript contains a `_forge_log` key recording the transform name, parameters, source, and export timestamp for each change (reproducible sessions)
- **Full pipeline export** — collapsible panel runs BPM Transformer + Window Customizer directly in the browser; result downloads as a separate `_pipeline.funscript` independent of phrase-editor transforms
- **Quality gate** — velocity and short-interval checks before download; pass/fail badge with an issues table (capped at 50 rows)
- Download builds the full result on demand

### Undo / Redo

- 50-level undo/redo stack for accepted phrase transforms
- Sidebar ↩ Undo / ↪ Redo buttons with operation-label tooltips
- Keyboard shortcuts: `Ctrl+Z` undo, `Ctrl+Y` / `Ctrl+Shift+Z` redo, `Ctrl+S` save

### Accessibility

- WCAG 2.1 Level AA — all Critical items and five of seven Major items resolved
- `aria-label` on all audio player buttons; `role="timer"` on the time display
- Screen-reader-only text on rejected export rows; BPM value labels on phrase timeline bars
- Keyboard shortcut support throughout; `lang="en"` injected at page load

### CLI

- `assess`, `transform`, `customize`, `pipeline` — full analysis and transform pipeline
- `phrase-transform` — apply any catalog transform to individual phrases from the command line
- `finalize` — blend seams + final smooth as standalone post-processing
- `export-plan` — mirror of the UI Export tab; supports `--apply` to write output directly
- `catalog` — query and manage the cross-funscript pattern catalog
- `test` — run all 698 tests

---

## User workflow

### 1 — Analyze

The analyzer reads a `.funscript` file and detects its motion structure,
working through five stages:

```text
actions → phases → cycles → patterns → phrases → BPM transitions
```

- **Phases** — individual up, down, or flat direction segments
- **Cycles** — one complete oscillation (one up + one down phase)
- **Patterns** — cycles with the same direction sequence and similar duration
- **Phrases** — consecutive runs of the same pattern, each with a BPM value
- **BPM transitions** — points where tempo changes significantly between phrases

The output is a single JSON file capturing the full structural picture.

### 2 — Review in the UI

Open the Streamlit app and load your funscript. The **Assessment** tab shows
the full pipeline output — a colour-coded phrase timeline, BPM transitions
table, and drill-down detail for patterns and phases.

The **Phrase Editor** tab shows the full funscript as a colour-coded chart
with phrase bounding boxes.  Click any phrase to open its detail panel where
you can select a transform, tune its parameters with live sliders, and see a
Before / After preview.  Use **Apply to all** to copy the same transform to
every instance of the same behavioral tag.

The **Pattern Editor** tab lets you fix behavioral issues phrase by phrase.
Each phrase instance shows an original chart and a live preview as you adjust
transforms.  For phrases that span a long section (e.g. a single pattern
covering most of the file), you can **split** the phrase into non-overlapping
sub-ranges and apply a different transform to each one.  Split boundaries
are shown as dashed lines on both charts.  Use **Apply to all** to copy the
split structure — scaled proportionally — to every other instance of the same
behavioral tag.

The **Transform Catalog** tab is a reference guide for all 17 transforms
grouped by capability.  Each entry includes a description, best-fit
behavioral tags, a parameter table, and live Before / After charts with
interactive sliders.

### 3 — Export

The **Export** tab aggregates every transform you have applied in the editors,
plus optionally the auto-recommended transforms for untouched phrases.  A
change log shows each planned transform with start / end time, duration,
transform name, source (Phrase Editor / Pattern Editor / Recommended), and
before → after BPM and cycle count where applicable.  Click 🗑 on any row to
reject that change before downloading.

**Tag-aware auto-suggestions** (`suggest_transform`, checked in priority order):

| Tag | Suggested transform | Notes |
| --- | --- | --- |
| `frantic` | `halve_tempo` | BPM > 200 |
| `giggle`, `plateau`, `lazy` | `amplitude_scale` | Amplify; scale computed to target peak hi ≈ 65 |
| `stingy` | `amplitude_scale` | Reduce; scale computed to target peak hi ≈ 65 |
| `drift`, `half_stroke` | `recenter` | `target_center = 50` |
| `drone` | `beat_accent` | Adds rhythmic variation |
| *(no tag, transition)* | `smooth` | Pattern label contains "transition" |
| *(no tag, low BPM)* | `passthrough` | BPM < threshold |
| *(no tag, narrow span)* | `normalize` | `amplitude_span < 40` |
| *(no tag, high BPM)* | `amplitude_scale` | Fallback |

Two optional post-processing passes run over the full action list just before
the file is built:

- **Add blended seams** — detects high-velocity jumps between differently-styled
  sections and applies a bilateral LPF at those seams, leaving normal strokes
  untouched.
- **Final smooth** — a light global LPF (strength 0.10) as a finishing polish.

Click **Download edited funscript** to build and save the result.

You can also query the same plan from the CLI — see `export-plan` below.

### 4 — Transform and customize

After reviewing in the UI, run the full pipeline to produce the final funscript.

#### Option A — in the browser (Export tab)

Open the **Export** tab and expand **"Run full pipeline — BPM Transformer + Window Customizer"**.
Adjust the BPM threshold and amplitude scale sliders, toggle whether to apply your Work Item
windows, then click **▶ Run Pipeline**. Download the result with
**⬇ Download pipeline result**.  This is independent of any phrase-editor transforms and
produces a `_pipeline.funscript` file with an embedded `_forge_log`.

#### Option B — command line

```bash
# Step 1 — analyze (or use the UI; it saves a cached JSON automatically)
python cli.py assess input.funscript --output output/assessment.json

# Step 2 — transform (BPM-threshold baseline)
python cli.py transform input.funscript \
    --assessment output/assessment.json \
    --output output/transformed.funscript

# Step 3 — customize (apply your tagged windows)
python cli.py customize output/transformed.funscript \
    --assessment output/assessment.json \
    --perf output/input.performance.json \
    --break output/input.break.json \
    --raw output/input.raw.json \
    --output output/final.funscript

# Or run both steps at once
python cli.py pipeline input.funscript --output-dir output/
```

---

## Getting started

### Install

```bash
pip install -r requirements.txt
pip install -r ui/streamlit/requirements.txt
```

### Launch the UI

```bash
# Desktop launcher (recommended) — starts local HTTP media server for audio/video streaming
python launcher.py

# Or run directly (web/upload mode)
streamlit run ui/streamlit/app.py
```

Opens at `http://localhost:8501`. Select a funscript from the sidebar and
click **Load / Analyse** to see the assessment results immediately.

The desktop launcher enables local mode: file paths are entered directly, recent files are
remembered across sessions, and audio/video streams from disk with no upload or size limit.

### Analyze from the command line

```bash
python cli.py assess path/to/file.funscript --output output/assessment.json
```

---

## Project structure

```text
funscript-forge/
├── assessment/               # Step 1: structural analysis + behavioral classification
│   ├── analyzer.py           #   FunscriptAnalyzer
│   ├── classifier.py         #   BehavioralTag, TAGS registry, annotate_phrases
│   └── readme.md
├── catalog/                  # Cross-funscript pattern catalog
│   └── pattern_catalog.py    #   PatternCatalog (persistent JSON)
├── pattern_catalog/          # Step 2: BPM-threshold baseline transform
│   ├── transformer.py        #   FunscriptTransformer
│   ├── phrase_transforms.py  #   TRANSFORM_CATALOG (17 named transforms)
│   └── config.py             #   TransformerConfig
├── user_customization/       # Step 3: window-based fine-tuning
│   ├── customizer.py         #   WindowCustomizer
│   └── config.py             #   CustomizerConfig
├── visualizations/           # matplotlib motion chart
│   └── motion.py
├── ui/                       # All UI code
│   ├── common/               #   Framework-agnostic models and logic
│   │   ├── work_items.py     #   WorkItem + ItemType
│   │   ├── project.py        #   Project session state
│   │   ├── pipeline.py       #   run_pipeline / run_pipeline_in_memory
│   │   └── tests/
│   ├── streamlit/            #   Streamlit app (local + cloud deployable)
│   │   ├── app.py
│   │   └── panels/
│   └── web/                  #   FastAPI + frontend (planned)
├── tests/                    # Core pipeline unit tests
├── models.py                 # Shared dataclasses (Phrase now carries tags + metrics)
├── utils.py                  # Timestamp helpers, low-pass filter
├── cli.py                    # CLI entry point
└── requirements.txt
```

---

## CLI reference

```bash
# Assess
python cli.py assess <funscript> [--output <path>] [--config <json>]
                     [--min-phrase-duration SECONDS] [--amplitude-tolerance FRACTION]

# Transform (BPM-threshold baseline)
python cli.py transform <funscript> --assessment <path>
                        [--output <path>] [--config <json>]

# Customize (window-based fine-tuning)
python cli.py customize <funscript> --assessment <path>
                        [--output <path>] [--config <json>]
                        [--perf <json>] [--break <json>] [--raw <json>] [--beats <json>]

# Full pipeline (assess → transform → customize in one step)
python cli.py pipeline <funscript> --output-dir <dir>
                       [--perf <json>] [--break <json>] [--raw <json>] [--beats <json>]
                       [--transformer-config <json>] [--customizer-config <json>]

# Phrase-level transform (applies a catalog transform to individual phrases)
python cli.py phrase-transform <funscript> --assessment <path>
                               --transform smooth --phrase 3 [--param strength=0.25]
                               --transform normalize --all
                               --suggest [--bpm-threshold 120]   # tag-aware auto-pick
                               [--output <path>] [--dry-run]

# Finalize (blend seams + final smooth as post-processing)
python cli.py finalize <funscript> [--output <path>]
                       [--param seam_max_velocity=0.3] [--param smooth_strength=0.05]
                       [--skip-seams] [--skip-smooth]

# Export plan (mirror of the UI Export tab)
python cli.py export-plan <funscript> [--assessment <path>]
                          [--transforms overrides.json] [--no-recommended]
                          [--bpm-threshold BPM] [--format table|json]
                          [--apply] [--output <path>] [--dry-run]

# Catalog
python cli.py catalog [--catalog <path>] [--tag TAG] [--remove FUNSCRIPT] [--clear]

# Utilities
python cli.py visualize <funscript> --assessment <path> [--output <path>]
python cli.py config    [--customizer] [--analyzer] [--output <path>]
python cli.py test
```

---

## Running tests

```bash
# Core pipeline + integration + UI tests (638 tests)
python -m unittest discover -s tests -v

# UI layer (60 tests)
python -m unittest discover -s ui/common/tests -v

# All at once (698 tests)
python cli.py test
```

---

## Documentation

| README | Description |
| --- | --- |
| [assessment/readme.md](assessment/readme.md) | Structural analysis pipeline — phases, cycles, patterns, phrases, BPM transitions (Step 1) |
| [pattern_catalog/README.md](pattern_catalog/README.md) | BPM-threshold baseline transformer (Step 2) |
| [user_customization/README.md](user_customization/README.md) | Window-based fine-tuning customizer (Step 3) |
| [ui/README.md](ui/README.md) | Streamlit UI overview — launcher, local mode, sidebar controls, all four tabs |
| [ui/streamlit/README.md](ui/streamlit/README.md) | Detailed Streamlit panel reference — Phrase Editor, Pattern Editor, Export |
| [ui/streamlit/UNDO.md](ui/streamlit/UNDO.md) | Undo/redo — what is captured, how to use it, architecture, extending it |
| [ui/common/README.md](ui/common/README.md) | Framework-agnostic business logic: `Project`, `WorkItem`, `ViewState` |
| [user_transforms/README.md](user_transforms/README.md) | Adding custom transforms via JSON recipe files |
| [plugins/README.md](plugins/README.md) | Adding custom transforms via Python plugins |
| [visualizations/README.md](visualizations/README.md) | Matplotlib motion chart components |
| [tests/README.md](tests/README.md) | Test suite structure and coverage |
| [internal/ACCESSIBILITY.md](internal/ACCESSIBILITY.md) | WCAG 2.1 AA accessibility assessment — issues, severity, recommended fixes |
| [BUILD.md](BUILD.md) | Building a standalone installer on Windows and macOS |

---

![Liquid Releasing](media/liquid-releasing-Color-Logo.svg)

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](LICENSE).  Written by human and Claude AI (Claude Sonnet).*
