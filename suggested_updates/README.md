# suggested_updates

BPM-threshold based transformation of funscripts (Pipeline Stage 2).

The transformer reads the assessment output from Stage 1 and decides,
phrase by phrase, whether each action should be passed through unchanged
or receive an amplitude transform.

## How it works

| Condition | Result |
| --- | --- |
| phrase BPM < `bpm_threshold` | Original position kept (pass-through) |
| phrase BPM >= `bpm_threshold` | Position scaled around centre (50) by `amplitude_scale` |
| Action outside all phrases | Overall assessment BPM used for the threshold comparison |

After the per-action pass, a low-pass filter smooths only the
high-BPM regions. Global time scaling (`time_scale`) is applied before
phrase lookup so that timeline boundaries remain consistent.

## Configuration — `TransformerConfig`

| Field | Default | Description |
| --- | --- | --- |
| `bpm_threshold` | `120.0` | BPM at or above which the amplitude transform fires |
| `amplitude_scale` | `2.0` | Scale factor applied around centre (50) |
| `lpf_default` | `0.10` | Low-pass filter strength for high-BPM phrases |
| `time_scale` | `1.0` | Global time multiplier applied before phrase lookup (1.0 = no change) |

Config can be saved and loaded as JSON:

```python
from suggested_updates import TransformerConfig

cfg = TransformerConfig(bpm_threshold=100.0, amplitude_scale=1.8)
cfg.save("transformer_config.json")
cfg2 = TransformerConfig.load("transformer_config.json")
```

Unknown keys in the JSON file are silently ignored, so it is safe to
load configs written by older or newer versions.

## Interaction with assessment output

`FunscriptTransformer` reads an `AssessmentResult` (produced by Stage 1)
to obtain:

- the list of **phrases** and their individual BPM values
- the **overall BPM** used as a fallback for actions that fall outside
  every phrase

Pass the assessment either as an object or from a saved JSON file:

```python
transformer.load_assessment(assessment_result)          # from object
transformer.load_assessment_from_file("assessment.json") # from file
```

## Usage

### Programmatically

```python
from suggested_updates import FunscriptTransformer, TransformerConfig

transformer = FunscriptTransformer(config=TransformerConfig(bpm_threshold=100.0))
transformer.load_funscript("input.funscript")
transformer.load_assessment_from_file("assessment.json")
transformer.transform()
transformer.save("transformed.funscript")

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


## Interactive phrase transforms (`phrase_transforms.py`)

The Streamlit phrase detail panel lets users apply named transforms to
individual phrases before saving.  The catalog lives in `phrase_transforms.py`
and is independent of the bulk pipeline transformer.

### Transform catalog

| Key | Name | Description |
| --- | --- | --- |
| `passthrough` | Passthrough | Keep original positions unchanged |
| `amplitude_scale` | Amplitude Scale | Scale stroke depth around midpoint (50) |
| `normalize` | Normalize Range | Expand positions to fill a target range |
| `smooth` | Smooth | Low-pass filter to reduce jitter |
| `clamp_upper` | Clamp Upper Half | Compress into 50–100 zone |
| `clamp_lower` | Clamp Lower Half | Compress into 0–50 zone |
| `invert` | Invert | Mirror positions around 50 |
| `boost_contrast` | Boost Contrast | Push toward 0 and 100 extremes |

### Programmatic use

```python
from suggested_updates.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

# Apply a named transform to a slice of actions
spec = TRANSFORM_CATALOG["amplitude_scale"]
new_actions = spec.apply(phrase_actions, {"scale": 1.8})

# Get the rule-based suggestion for a phrase dict
key = suggest_transform(phrase_dict, bpm_threshold=120.0)
```

### Suggestion rules

| Condition (checked in order) | Suggested transform |
| --- | --- |
| `pattern_label` contains `"transition"` | `smooth` |
| `bpm < bpm_threshold` | `passthrough` |
| `bpm >= bpm_threshold` and `amplitude_span < 40` | `normalize` |
| `bpm >= bpm_threshold` | `amplitude_scale` |
