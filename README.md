# funscript-updater

A structure-aware, beat-sensitive post-processor for funscripts. Analyzes an existing script's motion structure and produces a new script with smoother defaults, expressive performance sections, gentle breaks, and beat-locked accents.

---

## Workflow

### Step 1 — Assess the current funscript

Run the analyzer against your source funscript. This produces a single JSON file describing the motion structure.

```bash
python cli.py assess path/to/input.funscript --output assessment.json
```

The assessment JSON contains (with both `_ms` and `_ts` fields for every timestamp):

| Section | What it captures |
| --- | --- |
| `phases` | Fine-grained up/down/flat direction segments |
| `cycles` | Full oscillations (one up + one down phase) |
| `patterns` | Groups of similar-duration cycles |
| `phrases` | Runs of the same pattern — the long-form structure |
| `beat_windows` | Cycle and phrase start/end boundaries |
| `auto_mode_windows` | Suggested performance / break / default regions |

### Step 2 — Review suggested updates

Open `assessment.json` and review `auto_mode_windows`. The analyzer classifies phrases by cycle count:

- **performance** — phrases with ≥ 5 cycles (high-energy, fast sections)
- **break** — phrases with ≤ 2 cycles (low-energy, slow sections)
- **default** — everything else

Use `visualize` to see the structure plotted over the raw motion curve:

```bash
python cli.py visualize path/to/input.funscript --assessment assessment.json --output viz.png
```

### Step 3 — Manual updates

Override any auto window by creating JSON files with human-readable timestamps (`HH:MM:SS.mmm`). Manual windows take priority — any auto window overlapping a manual one is removed.

#### manual_performance.json

```json
[
  { "start": "00:01:10.000", "end": "00:01:25.000", "label": "chorus buildup" }
]
```

#### manual_break.json

```json
[
  { "start": "00:02:05.000", "end": "00:02:12.500", "label": "verse rest" }
]
```

#### raw_windows.json

Sections where original actions are copied verbatim — highest priority, no transform applied.

```json
[
  { "start": "00:03:10.000", "end": "00:03:16.561", "label": "keep original" }
]
```

Use empty arrays `[]` if you don't need any manual overrides yet.

### Step 4 — Generate new funscript

```bash
python cli.py transform path/to/input.funscript \
    --assessment assessment.json \
    --output output.funscript \
    --perf manual_performance.json \
    --break manual_break.json \
    --raw raw_windows.json
```

Optional flags:

- `--config transformer_config.json` — custom transform settings (see below)
- `--beats beats.json` — beat times in ms (`[{"time": 1200}, ...]`), enables Task 6
- `--save-merged merged.json` — save the final merged window snapshot for inspection

---

## The Six Tasks

| Task | Mode | What it does |
| --- | --- | --- |
| 1 | Default | Half-speed timing + double amplitude outside performance windows |
| 2 | Performance | Velocity limiting, reversal softening, position compression |
| 3 | Break | Pulls positions toward center (50), reduces amplitude |
| 4 | Raw preserve | Copies original timestamps and positions verbatim |
| 5 | Cycle dynamics | Cosine-shaped push/pull aligned to cycle midpoints |
| 6 | Beat accents | Small nudges near detected beat times |

---

## Installation

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
```

`matplotlib` is the only dependency and is only required for `visualize`.

---

## Project Structure

```text
funscript-updater/
├── assessment/
│   ├── analyzer.py       # FunscriptAnalyzer — runs Steps 1 analysis pipeline
│   └── visualizer.py     # FunscriptVisualizer — plots motion + structure
├── suggested_updates/
│   ├── config.py         # TransformerConfig dataclass (all tunable parameters)
│   └── transformer.py    # FunscriptTransformer — runs Steps 4 six tasks
├── tests/
│   ├── fixtures/
│   │   └── sample.funscript
│   ├── test_utils.py
│   ├── test_analyzer.py
│   └── test_transformer.py
├── models.py             # Shared dataclasses (Phase, Cycle, Pattern, Phrase, Window, AssessmentResult)
├── utils.py              # Shared utilities (parse_timestamp, ms_to_timestamp, overlaps, low_pass_filter)
├── cli.py                # CLI entry point
└── requirements.txt
```

---

## CLI Reference

```bash
python cli.py assess <funscript> [--output <path>] [--config <analyzer_config.json>]
python cli.py transform <funscript> --assessment <path> [--output <path>]
                        [--config <transformer_config.json>]
                        [--beats <beats.json>]
                        [--perf <manual_performance.json>]
                        [--break <manual_break.json>]
                        [--raw <raw_windows.json>]
                        [--save-merged <merged.json>]
python cli.py visualize <funscript> --assessment <path> [--output <path>]
python cli.py config [--output <path>]    # dump default transformer config
python cli.py test                        # run unit tests
```

---

## Transformer Config

Dump the default config to a file, edit it, and pass it with `--config`:

```bash
python cli.py config --output my_config.json
python cli.py transform input.funscript --assessment assessment.json --config my_config.json
```

Key parameters:

| Parameter | Default | Effect |
| --- | --- | --- |
| `time_scale` | 2.0 | Timing multiplier in default mode (2.0 = half speed) |
| `amplitude_scale` | 2.0 | Position spread multiplier around center |
| `lpf_default` | 0.10 | Smoothing in default sections |
| `lpf_performance` | 0.16 | Smoothing in performance sections |
| `lpf_break` | 0.30 | Smoothing in break sections |
| `max_velocity` | 0.32 | Position-per-ms velocity cap in performance mode |
| `beat_accent_amount` | 4 | Position nudge amount near beats |

---

## API (for UI integration)

All classes are designed to be driven from a future UI without any CLI dependency.

```python
from assessment.analyzer import FunscriptAnalyzer, AnalyzerConfig
from assessment.visualizer import FunscriptVisualizer
from suggested_updates.transformer import FunscriptTransformer
from suggested_updates.config import TransformerConfig
from models import AssessmentResult

# Step 1
analyzer = FunscriptAnalyzer(config=AnalyzerConfig(performance_cycle_threshold=4))
analyzer.load("input.funscript")
result = analyzer.analyze()
result.save("assessment.json")

# Step 4
transformer = FunscriptTransformer(config=TransformerConfig(time_scale=1.5))
transformer.load_funscript("input.funscript")
transformer.load_assessment(result)          # or load_assessment_from_file("assessment.json")
transformer.load_manual_overrides(perf_path="manual_performance.json")
transformer.merge_windows()
transformer.transform()
transformer.save("output.funscript")
```

---

## Running Tests

```bash
python cli.py test
# or directly:
python -m unittest discover tests
```
