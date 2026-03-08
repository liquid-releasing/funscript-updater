# assessment

Structural analysis of a funscript — Step 1 of the four-step workflow.

The `FunscriptAnalyzer` class processes a `.funscript` file and produces an
`AssessmentResult` containing detected phases, cycles, patterns, phrases, beat
windows, and auto mode windows. All timestamps are output in both milliseconds
and human-readable `HH:MM:SS.mmm` format.

## Pipeline

```text
load() → analyze() → AssessmentResult → save()
```

## Usage

### Via CLI

```bash
python cli.py assess path/to/input.funscript [--output assessment.json] [--config config.json]
```

If `--output` is omitted, the JSON is saved alongside the input file with an
`_assessment.json` suffix.

### Programmatically

```python
from assessment.analyzer import FunscriptAnalyzer, AnalyzerConfig

analyzer = FunscriptAnalyzer()
analyzer.load("path/to/input.funscript")
result = analyzer.analyze()
result.save("assessment.json")
```

With a custom config:

```python
config = AnalyzerConfig(performance_cycle_threshold=8, break_cycle_threshold=1)
analyzer = FunscriptAnalyzer(config=config)
```

## Classes

### `FunscriptAnalyzer`

| Method | Description |
| --- | --- |
| `load(path)` | Load a `.funscript` file |
| `analyze() -> AssessmentResult` | Run the full analysis pipeline |

### `AnalyzerConfig`

| Field | Default | Description |
| --- | --- | --- |
| `min_velocity` | `0.02` | Minimum velocity to count as directional motion |
| `min_phase_duration_ms` | `80` | Minimum phase length in ms |
| `duration_tolerance` | `0.20` | Max fractional duration difference for similar cycles |
| `velocity_tolerance` | `0.25` | Max fractional velocity difference for similar cycles |
| `performance_cycle_threshold` | `5` | Phrases with >= this many cycles → performance window |
| `break_cycle_threshold` | `2` | Phrases with <= this many cycles → break window |

## Analysis pipeline

### Phases

Directional segments of continuous motion. Each phase is labeled `steady upward motion`,
`steady downward motion`, or `low-motion plateau`. Both `start_ms`/`end_ms` and
`start_ts`/`end_ts` are available.

### Cycles

Structural groupings of phases where the direction does not consecutively repeat.
Each cycle carries an `oscillation_count` (up-down pairs) used to compute per-cycle BPM.

### Patterns

Cycles that share the same direction sequence and similar duration are grouped into
a pattern. Each pattern records its average duration and how many cycles matched.

### Phrases

Runs of consecutive cycles that all belong to the same pattern. Each phrase carries
an `oscillation_count` (sum of its cycles) and a computed `bpm` property.

### Auto mode windows

Phrases are classified into three buckets based on cycle count:

| Bucket | Condition |
| --- | --- |
| `performance` | `cycle_count >= performance_cycle_threshold` |
| `default` | between the two thresholds |
| `break` | `cycle_count <= break_cycle_threshold` |

These windows are the starting point for Step 4 (transform). Manual override windows
take priority over auto windows on overlap.

## Assessment JSON output

```json
{
  "meta": {
    "source_file": "input.funscript",
    "analyzed_at": "2025-01-01T12:00:00",
    "duration_ms": 360000,
    "duration_ts": "00:06:00.000",
    "action_count": 1200,
    "bpm": 142.5
  },
  "phases": [
    { "start_ms": 0, "start_ts": "00:00:00.000", "end_ms": 250, "end_ts": "00:00:00.250", "label": "steady upward motion" }
  ],
  "cycles": [
    { "start_ms": 0, "start_ts": "00:00:00.000", "end_ms": 500, "end_ts": "00:00:00.500", "label": "up → down", "oscillation_count": 1, "bpm": 120.0 }
  ],
  "patterns": [ ... ],
  "phrases": [
    { "start_ms": 0, "start_ts": "00:00:00.000", "end_ms": 5000, "end_ts": "00:00:05.000",
      "pattern_label": "up → down", "cycle_count": 10, "oscillation_count": 10, "bpm": 120.0, "description": "10 cycles of pattern 'up → down'" }
  ],
  "beat_windows": [ ... ],
  "auto_mode_windows": {
    "performance": [ { "start_ms": 0, "start_ts": "...", "end_ms": 5000, "end_ts": "...", "label": "..." } ],
    "break": [],
    "default": []
  }
}
```

## Loading a saved assessment

```python
from models import AssessmentResult

result = AssessmentResult.load("assessment.json")
print(result.bpm)
print(result.phases)
```
