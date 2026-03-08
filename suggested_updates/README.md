# suggested_updates

BPM-threshold based transformation of funscripts (Pipeline Stage 2).

The transformer reads the assessment output from Stage 1 and decides, phrase
by phrase, whether each action should be passed through unchanged or receive
an amplitude transform.

## How it works

| Condition | Result |
| --- | --- |
| phrase BPM < `bpm_threshold` | Original position kept (pass-through) |
| phrase BPM ≥ `bpm_threshold` | Position scaled around centre (50) by `amplitude_scale` |
| Action outside all phrases | Overall assessment BPM used for the threshold comparison |

A low-pass filter smooths the high-BPM regions after the per-action pass.
Global time scaling (`time_scale`) is applied before phrase lookup so that
timeline boundaries remain consistent.

## Configuration — `TransformerConfig`

| Field | Default | Description |
| --- | --- | --- |
| `bpm_threshold` | `120.0` | BPM above which the transform fires |
| `amplitude_scale` | `2.0` | Scale factor applied around centre (50) |
| `lpf_default` | `0.10` | Low-pass filter strength for high-BPM phrases |
| `time_scale` | `1.0` | Global time multiplier (1.0 = no change) |

Config can be saved/loaded as JSON:

```python
from suggested_updates import TransformerConfig

cfg = TransformerConfig(bpm_threshold=100.0, amplitude_scale=1.8)
cfg.save("transformer_config.json")
cfg2 = TransformerConfig.load("transformer_config.json")
```

## Usage

### Programmatically

```python
from suggested_updates import FunscriptTransformer, TransformerConfig
from models import AssessmentResult

transformer = FunscriptTransformer()
transformer.load_funscript("input.funscript")
transformer.load_assessment_from_file("assessment.json")
transformer.transform()
transformer.save("transformed.funscript")

# Inspect log
for line in transformer.get_log():
    print(line)
```

### Via CLI

```bash
python cli.py transform input.funscript \
    --assessment assessment.json \
    --output transformed.funscript
```

## Modules

| File | Contents |
| --- | --- |
| `transformer.py` | `FunscriptTransformer` class |
| `config.py` | `TransformerConfig` dataclass |
| `__init__.py` | Re-exports `FunscriptTransformer`, `TransformerConfig` |

## Tests

```bash
python -m unittest tests.test_transformer -v
```

15 tests covering: load, transform output shape, positions in `[0, 100]`,
timestamps non-negative, save → valid JSON, log output, pass-through at high
threshold, all-transform at zero threshold, time-scale applied globally, and
config round-trip / save-load / unknown-key handling.
