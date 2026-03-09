# assessment

Structural analysis of a funscript — Step 1 of the pipeline.

The `FunscriptAnalyzer` processes a `.funscript` file and produces an
`AssessmentResult` containing detected phases, cycles, patterns, phrases,
and BPM transitions. All timestamps are output in both milliseconds and
human-readable `HH:MM:SS.mmm` format.

## Pipeline

```text
load() → analyze() → AssessmentResult → save()
```

Each stage feeds the next:

```text
actions → phases → cycles → patterns → phrases → bpm_transitions
                                                ↓
                                       behavioral classification
                                       (tags + metrics per phrase)
```

## Usage

### Via CLI

```bash
python cli.py assess path/to/input.funscript [--output assessment.json] [--config config.json]
```

If `--output` is omitted, the JSON is saved alongside the input file with an
`.assessment.json` suffix.

### Programmatically

```python
from assessment.analyzer import FunscriptAnalyzer, AnalyzerConfig

analyzer = FunscriptAnalyzer()
analyzer.load("path/to/input.funscript")
result = analyzer.analyze()
result.save("output/assessment.json")
```

With a custom config:

```python
config = AnalyzerConfig(bpm_change_threshold_pct=30.0)
analyzer = FunscriptAnalyzer(config=config)
```

## Classes

### `FunscriptAnalyzer`

| Method | Description |
| --- | --- |
| `load(path)` | Load a `.funscript` file |
| `analyze() -> AssessmentResult` | Run the full analysis pipeline and return the result |

### `AnalyzerConfig`

| Field | Default | Description |
| --- | --- | --- |
| `min_velocity` | `0.02` | Velocity threshold below which motion is treated as flat |
| `min_phase_duration_ms` | `80` | Phases shorter than this are discarded |
| `duration_tolerance` | `0.20` | Max fractional duration difference for two cycles to be considered similar |
| `velocity_tolerance` | `0.25` | Max fractional velocity difference for cycle similarity |
| `bpm_change_threshold_pct` | `40.0` | Minimum absolute BPM % change between consecutive phrases to flag a transition |

## Analysis pipeline stages

### 1 — Phases

Contiguous segments of consistent directional motion, detected by sign
changes in inter-action velocity. Each phase is labeled one of:

- `steady upward motion`
- `steady downward motion`
- `low-motion plateau`

A phase is only emitted if its duration ≥ `min_phase_duration_ms`.

### 2 — Cycles

Phases are grouped into cycles, where **one cycle = one complete oscillation**
(an up segment followed by a down segment, or vice-versa, optionally
interrupted by flat segments). A new cycle is opened as soon as the
accumulating phases contain both active directions; the next direction change
closes the current cycle and starts a fresh one.

Each cycle carries:

- `label` — direction sequence, e.g. `"up → down"` or `"up → flat → down"`
- `oscillation_count` — number of up-down pairs within the cycle
- `bpm` — computed as `60 000 / duration_ms × oscillation_count`

### 3 — Patterns

Cycles with the same direction-sequence label **and** similar duration
(within `duration_tolerance`) are grouped into a pattern. Each pattern
records:

- `pattern_label` — the shared direction sequence
- `avg_duration_ms` — mean cycle duration
- `count` — number of matching cycles

### 4 — Phrases

Consecutive cycles that all belong to the same pattern are merged into a
phrase. Each phrase carries a `bpm` property (oscillations per minute over
the phrase window) and a `cycle_count`.

### 5 — BPM transitions

Consecutive phrase pairs where BPM changes by ≥ `bpm_change_threshold_pct`
percent are flagged as BPM transitions. These mark structural tempo shifts
and are the primary signal used by the UI to suggest work-item boundaries.

### 6 — Behavioral classification

After phrases are detected, `assessment/classifier.py` analyses each phrase's
action window and attaches two extra fields:

- **`metrics`** — numeric features computed from the action window:
  `mean_pos`, `span`, `mean_velocity`, `peak_velocity`, `cv_bpm`,
  `duration_ms`
- **`tags`** — list of zero or more behavioral problem labels

| Tag | Condition | Suggested fix |
| --- | --- | --- |
| `stingy` | span > 75 AND velocity > 0.35 AND BPM > 120 | `performance` |
| `giggle` | span < 20 AND centre 35–65 | `normalize` |
| `plateau` | 20 ≤ span < 40 AND centre 35–65 | `amplitude_scale` |
| `drift` | centre < 30 OR centre > 70 (span > 15) | `recenter` |
| `half_stroke` | span > 30 AND centre 38–62 offset | `recenter` |
| `drone` | duration > threshold AND cv_bpm < 0.10 | `beat_accent` |
| `lazy` | BPM < 60 AND span < 50 | `amplitude_scale` |
| `frantic` | BPM > 200 | `halve_tempo` |

Tags and metrics are saved in the assessment JSON and are used by the
Pattern Editor UI tab and the cross-funscript `catalog/pattern_catalog.py`.

## Real-world results (test funscripts)

| File | Duration | Actions | Phases | Cycles | Patterns | Phrases | BPM transitions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Timeline1` | 3:13 | 822 | 791 | 381 | 11 | 34 | 30 |
| `LongandCut-hdr` | 10:16 | 2 586 | 2 548 | 1 262 | 13 | 32 | 28 |
| `VictoriaOaks_stingy` | 1:33:12 | 23 710 | 23 708 | 11 854 | 1 | 1 | 0 (uniform tempo) |

## Assessment JSON output

```json
{
  "meta": {
    "source_file": "input.funscript",
    "analyzed_at": "2025-01-01T12:00:00",
    "duration_ms": 193472,
    "duration_ts": "00:03:13.472",
    "action_count": 822,
    "bpm": 119.86
  },
  "phases": [
    {
      "start_ms": 85, "start_ts": "00:00:00.085",
      "end_ms": 320,  "end_ts": "00:00:00.320",
      "label": "steady upward motion"
    }
  ],
  "cycles": [
    {
      "start_ms": 85,  "start_ts": "00:00:00.085",
      "end_ms": 554,   "end_ts": "00:00:00.554",
      "label": "up → down",
      "oscillation_count": 1,
      "bpm": 120.5
    }
  ],
  "patterns": [
    {
      "pattern_label": "up → down",
      "avg_duration_ms": 472,
      "count": 349,
      "cycles": ["..."]
    }
  ],
  "phrases": [
    {
      "start_ms": 85,    "start_ts": "00:00:00.085",
      "end_ms": 86506,   "end_ts": "00:01:26.506",
      "pattern_label": "up → down",
      "cycle_count": 183,
      "oscillation_count": 183,
      "bpm": 127.0,
      "description": "183 cycles of pattern 'up → down'",
      "tags": ["stingy"],
      "metrics": {
        "mean_pos": 50.2, "span": 82.0,
        "mean_velocity": 0.42, "peak_velocity": 0.55,
        "cv_bpm": 0.08, "duration_ms": 86421
      }
    }
  ],
  "bpm_transitions": [
    {
      "at_ms": 86506,  "at_ts": "00:01:26.506",
      "from_bpm": 127.0,
      "to_bpm": 63.9,
      "change_pct": -49.7,
      "description": "BPM drops 49.7% at 00:01:26.506"
    }
  ]
}
```

## Loading a saved assessment

```python
from models import AssessmentResult

result = AssessmentResult.load("output/assessment.json")
print(result.bpm)          # global average BPM
print(len(result.phrases)) # number of detected phrases
```
