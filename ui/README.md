# ui — Streamlit UI

Interactive local app for the Funscript Updater pipeline.

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
| Amplitude sensitivity | Medium (0.30) | How much stroke-depth change triggers a new phrase boundary (Low = 0.35, Medium = 0.30, High = 0.25) |

A **Re-analyse** button forces a fresh assessment even when the file and
settings have not changed.

### Chart settings

| Control | Default | Effect |
| --- | --- | --- |
| Fast rendering threshold (actions) | 10,000 | Funscripts above this action count use a single grey connecting line for speed; smaller ones use per-segment coloured lines |

### Session summary

Once a funscript is loaded, the sidebar shows the file name, total
duration, average BPM, phrase count, and BPM-transition count, plus a
breakdown of tagged work items by type.

### Add manual item

An expander lets you define a work item by typing start/end times (ms),
choosing a type, and optionally adding a label. Useful for sections the
automatic assessment did not detect.

### Export

Two buttons are available after a funscript is loaded:

- **Export window JSONs** — writes `performance.json`, `break.json`, and
  `raw.json` to the `output/` directory, ready for the customizer.
- **Save project** — writes a full project snapshot (work items, types,
  per-item configs) to `output/<name>.project.json`.

---

## Tabs

### Phrase Selector

A full-width interactive chart of the funscript with phrase bounding boxes
overlaid. Use it to visually select and inspect phrases.

**Navigation:**

- **Prev / Next buttons** — step through phrases one at a time; the
  viewport scrolls to keep the active phrase centred.
- **P1, P2, … buttons** — jump directly to any phrase (arranged in rows
  of 10).
- **Click a point on the chart** — selects the phrase that contains that
  timestamp.
- **Drag a box on the chart** — sets the viewport to that time range.

**Viewport controls** (scroll / zoom toolbar above the chart):

- Left (◀) / Right (▶) — scroll by one-third of the current window width.
- All — reset to the full funscript.
- +/− — zoom in (halve the window) or out (double the window).
- The two text fields accept timestamps in `M:SS` or `HH:MM:SS.mmm` format
  and move the viewport immediately on entry.

**Colour mode** toggle switches the dot colours between velocity-coded
and amplitude-coded.

Selecting a phrase shows a detail row below the chart: start, end,
duration, BPM, pattern label, and cycle count.

### Assessment

Read-only display of the full pipeline output for the loaded funscript.

- **Summary** — eight metrics: duration, average BPM, action count, phase
  count, cycle count, pattern count, phrase count, BPM-transition count.
- **Phases** — direction-breakdown bar chart plus a table of the first 20
  phases (start, end, label).
- **Cycles → Patterns** — table of detected patterns sorted by occurrence
  count, with average duration and BPM.
- **Phrases & BPM transitions** — a colour-coded SVG timeline bar (blue =
  low BPM, red = high BPM), a BPM-transitions table showing each
  from/to change and percentage, and an expandable phrase-detail table.

### Navigator

A clickable list of every assessment item grouped into five inner tabs:
Phases, Cycles, Patterns, Phrases, and BPM Transitions.

Each row has a **Focus** button that scrolls the Phrase Selector chart to
that item's time range and highlights it. Use this tab to quickly jump to
any specific phase, cycle, or BPM transition.

### Work Items

The main tagging workspace. Every detected section (phrase or BPM
transition) appears as a row showing its time range, duration, BPM, and
current type. A dropdown on each row lets you re-classify it:

| Type | Icon | What the customizer does |
| --- | --- | --- |
| Performance | 🔥 | Velocity limiting, reversal softening, position compression |
| Break | 🌊 | Amplitude reduction, pull toward centre |
| Raw | 🎯 | Copy original actions verbatim, no transforms |
| Neutral | ⚪ | Transformer decides automatically (no manual window) |

Click **Edit** on any row to open that item in the Edit tab.

### Edit

Controls for the currently selected work item.

**Time window** — adjust start and end times (ms) and add an optional
label. Changes take effect immediately.

**Performance items** expose three expanders:

- *Velocity & reversals* — max velocity, reversal softening, height blend
- *Position compression* — bottom and top position limits
- *Smoothing & jitter* — low-pass filter strength, timing jitter (ms)

**Break items** expose:

- Amplitude reduction (fraction pulled toward centre)
- Low-pass filter strength

**Raw items** show a notice that the section will be preserved verbatim.

**Neutral items** show a prompt to tag the section if manual control is
needed.

A **Reset to defaults** button restores all controls for the item to the
`CustomizerConfig` defaults.

### Export tab

A summary table of all typed work items (Performance, Break, Raw) grouped
by type. A **Write JSON files** button writes the window files to `output/`:

| File | Contents |
| --- | --- |
| `<name>.performance.json` | Performance windows for the customizer |
| `<name>.break.json` | Break windows |
| `<name>.raw.json` | Raw preserve windows |

---

## Adaptive rendering threshold

The **Fast rendering threshold** sidebar control (default 10,000 actions)
determines the chart rendering strategy:

- **Below threshold** — each segment between consecutive actions is drawn
  in a colour that matches the surrounding dot colours (velocity or
  amplitude). This gives the most informative view but is slower for large
  files.
- **At or above threshold** — all connecting lines are drawn in a single
  grey pass for speed, while dots retain their individual colours.

Reduce the threshold if segment colours are important for a large file and
rendering time is acceptable; raise it if the chart feels slow.

---

## Subdirectories

| Directory | Contents |
| --- | --- |
| `common/` | Framework-agnostic business logic: `Project`, `WorkItem`, `ViewState`, pipeline helpers. No Streamlit dependency. See [`common/README.md`](common/README.md). |
| `streamlit/` | Streamlit app entry point (`app.py`) and panel modules. |

## Tests

```bash
# UI common-layer tests (38 tests)
python -m unittest discover -s ui/common/tests -v

# Core pipeline tests (76 tests)
python -m unittest discover -s tests -v
```
