# ui — Streamlit UI

Interactive local app for the Funscript Forge pipeline.

## Quick start

```bash
# Install dependencies (once, from the project root)
pip install -r ui/streamlit/requirements.txt

# Launch
streamlit run ui/streamlit/app.py
```

Opens at `http://localhost:8501`. The app can also be deployed to
Streamlit Community Cloud with no code changes.

---

## Sidebar

The sidebar is always visible and controls which funscript is loaded and
how the assessment is run.

### File picker

A dropdown lists every `.funscript` file found in the `test_funscript/`
directory. Selecting a different file or changing any setting below
triggers an automatic re-assessment.

### Phrase detection settings

| Control | Default | Effect |
| --- | --- | --- |
| Min phrase length (s) | 20 s | Phrases shorter than this are merged into a neighbour |
| Amplitude sensitivity | Medium (0.30) | How much stroke-depth change triggers a new phrase boundary |

A **Re-analyse** button forces a fresh assessment even when the file and
settings have not changed.

### Chart settings

| Control | Default | Effect |
| --- | --- | --- |
| Fast rendering threshold (actions) | 10,000 | Funscripts above this count use a grey line for speed |
| Transform BPM threshold | 120 | Phrases at/above this BPM receive the Amplitude Scale suggestion |

### Session summary

Once a funscript is loaded, the sidebar shows the file name, total
duration, average BPM, phrase count, and BPM-transition count.

### Add manual item

An expander lets you define a work item by typing start/end times (ms),
choosing a type, and optionally adding a label.

### Export

- **Export window JSONs** — writes `performance.json`, `break.json`, and
  `raw.json` to `output/`, ready for the customizer.
- **Save project** — writes a full project snapshot to `output/<name>.project.json`.

---

## Tabs

### 1. Assessment

Full pipeline output: summary metrics, phrases table with Focus buttons,
BPM transitions chart and table with Focus buttons, behavioral patterns
bar chart and table with Focus buttons, and a phases expander.

### 2. Phrase Editor

Full-funscript interactive chart with phrase bounding boxes and a
per-phrase detail panel for transform editing (Original + Preview charts,
transform controls, Apply / Apply to all).

### 3. Pattern Behaviors

Cross-funscript behavioral pattern catalog — Gantt timeline, tag summary
with Sample waveform previews, and aggregate library stats.

### 4. Pattern Editor

Behavioral pattern batch-fix workspace. Phrases are pre-classified into
8 tags (Stingy, Giggle, Plateau, Drift, Half Stroke, Drone, Lazy,
Frantic). Select a tag, navigate instances with Prev/Next, apply
transforms individually or to all instances, then build a download.

### 5. Transform Catalog

Reference guide for all 17 phrase transforms grouped by capability.
Each entry shows description, best-fit tags, a parameter table, and
live Before/After charts with interactive sliders.

### 6. Export

Transform change log showing every planned transform (from Phrase Editor, Pattern Editor, or auto-recommended) with start/end time, duration, transform name, source, and before → after BPM / cycle count.  Each row has a 🗑 reject button.  A **Download edited funscript** button builds and streams the result.  Also accessible via `python cli.py export-plan`.

---

## Subdirectories

| Directory | Contents |
| --- | --- |
| `common/` | Framework-agnostic business logic: `Project`, `WorkItem`, `ViewState`. No Streamlit dependency. See [`common/README.md`](common/README.md). |
| `streamlit/` | Streamlit app entry point (`app.py`) and panel modules. See [`streamlit/README.md`](streamlit/README.md). |

## Tests

```bash
# UI common-layer tests (60 tests)
python -m unittest discover -s ui/common/tests -v

# Full test suite (482 tests)
python cli.py test
```
