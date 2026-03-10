# pattern_catalog

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
from pattern_catalog import TransformerConfig

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
from pattern_catalog import FunscriptTransformer, TransformerConfig

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

The **Save** button in the phrase detail panel includes a collapsed
**⚙ Finalize options** expander.  Both `blend_seams` and `final_smooth` are
enabled by default; their parameters can be tuned via sliders.  The transforms
are applied to the full assembled action list before the `.funscript` file is
downloaded — equivalent to running `python cli.py finalize` on the result.

### Transform catalog

| Key | Name | What it does | When to use |
| --- | --- | --- | --- |
| `passthrough` | Passthrough | No change — positions returned as-is | Phrase is already well-shaped; safe default |
| `amplitude_scale` | Amplitude Scale | Stretches/compresses stroke depth around the midpoint (50). Scale >1 = deeper, <1 = shallower | Fast phrases that need more intensity; default suggestion for high-BPM regular patterns |
| `normalize` | Normalize Range | Expands positions to fill a target range — maps the phrase's actual min/max to 0–100 (or a custom range) | Phrases where the signal is compressed into a narrow band; opens up the full stroke range |
| `smooth` | Smooth | Low-pass filter that reduces rapid micro-movements and jitter | Transition/break phrases with noisy or chaotic data; softens harsh edges |
| `clamp_upper` | Clamp Upper Half | Remaps all positions into the upper half (50–100) | Intense sections where motion should stay in the high-amplitude zone only |
| `clamp_lower` | Clamp Lower Half | Remaps all positions into the lower half (0–50) | Gentle or rest-style sections; reduces overall intensity |
| `invert` | Invert | Flips positions around 50 (pos = 100 − pos) | Corrects a phrase that is phase-inverted relative to the rest of the script |
| `boost_contrast` | Boost Contrast | Pushes positions toward 0 and 100, away from the midpoint | Flat-feeling phrases where peaks/troughs don't reach the extremes |
| `shift` | Shift | Adds a fixed offset to every position (positive = up, negative = down), clamped to 0–100 — amplitude preserved unless a boundary is hit | Nudge the whole phrase up or down without changing stroke depth |
| `recenter` | Recenter | Shifts all positions so the phrase midpoint lands at a target value — amplitude span unchanged | Reposition a phrase oscillating in the wrong zone, e.g. centre at 70 instead of 50 |
| `break` | Break | Pulls all positions toward centre 50 by a `reduce` fraction, then applies LPF smoothing — equivalent to a gentle amplitude_scale + smooth in one step | Rest, recovery, or transition sections; tones down intensity without removing motion entirely |
| `performance` | Performance | Velocity-capped, reversal-softened strokes with range compression and optional LPF — three passes: (1) cap pos-change/ms, (2) blend direction-change reversals, (3) clamp range + smooth | Intense high-BPM phrases that need realistic device shaping; prevents mechanical overshoot at stroke reversals |
| `three_one` | Three-One Pulse | Groups beats into blocks of 4: beats 1–3 are strokes (amplitude-scaled around the group centre), beat 4 is a flat hold at the group centre — timestamps unchanged | Fast up-down patterns where you want a rest beat every 4th; optional `range_lo`/`range_hi` caps limit stroke depth |
| `beat_accent` | Beat Accent | Boosts positions away from centre at every Nth stroke reversal — peaks pushed up, troughs pushed down, by `accent_amount` units within `radius_ms` of each accented beat. Optional `start_at_ms` anchors beat 0; `max_accents` limits repetitions | Add rhythmic emphasis on downbeats, every-other-beat, or sparse 4th-beat accents; hover over a beat in the UI to find its `start_at_ms` |
| `blend_seams` | Blend Seams | Velocity-adaptive bilateral LPF: concentrates smoothing at high-velocity jumps (seams between differently-styled phrases), leaves normal strokes untouched | Applied globally via `finalize` to smooth inter-phrase boundaries; can also be applied phrase-by-phrase for intra-phrase spikes |
| `final_smooth` | Final Smooth | Light global LPF finishing pass (default strength 0.10, matching `LPF_DEFAULT` from six_task_transformer) — removes residual harsh edges after all phrase transforms | Last step before saving; automatically run by `finalize` command |
| `halve_tempo` | Halve Tempo | Keeps every other stroke cycle (temporal decimation), retimed evenly over the same phrase duration — *structural* transform, returns fewer actions | Very fast phrases where you want half the BPM with the same amplitude and duration |

### CLI usage (`phrase-transform` command)

Apply a transform to specific phrases, all phrases, or let the suggestion rules
choose automatically.

```bash
# Apply smooth to phrases 4 and 5 only
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform smooth --phrase 4 --phrase 5 \
    --param strength=0.25

# Normalize all phrases (open up compressed signal)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform normalize --all

# Boost contrast on a single phrase, custom range
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform boost_contrast --phrase 2 \
    --param strength=0.8

# Scale amplitude down across all phrases (gentler output)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform amplitude_scale --all \
    --param scale=0.7

# Invert phrase 1 (fix phase-inverted section)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform invert --phrase 1

# Shift phrase 2 upward by 20 (more intense zone, same amplitude)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform shift --phrase 2 \
    --param offset=20

# Recenter phrase 3 so its midpoint lands at 70 (upper-zone repositioning)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform recenter --phrase 3 \
    --param target_center=70

# Break mode on a rest phrase (default: 40% amplitude reduction + 0.30 LPF smoothing)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform break --phrase 2

# Break with stronger reduction and heavier smoothing
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform break --phrase 2 \
    --param reduce=0.60 --param lpf_strength=0.40

# Performance shaping on a fast phrase (default settings from six_task_transformer)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform performance --phrase 1

# Performance with tighter velocity cap and wider range
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform performance --phrase 1 \
    --param max_velocity=0.20 --param range_lo=10 --param range_hi=95

# Three-one pulse on a fast phrase (every 4th beat becomes a flat hold)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform three_one --phrase 1

# Three-one pulse with amplitude boost and range cap (20–80)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform three_one --phrase 1 \
    --param amplitude_scale=1.5 --param range_lo=20 --param range_hi=80

# Beat accent on every beat (default: accent_amount=4, radius_ms=40)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform beat_accent --phrase 1

# Accent every 4th beat with a stronger boost (e.g. downbeat emphasis)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform beat_accent --phrase 1 \
    --param every_nth=4 --param accent_amount=10

# Anchor to a specific beat timestamp (hover in UI to find it) and cap at 8 accents
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform beat_accent --phrase 2 \
    --param every_nth=2 --param start_at_ms=45200 --param max_accents=8

# Halve the tempo of a very fast phrase (keeps same duration and amplitude)
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform halve_tempo --phrase 3

# Halve tempo across all phrases, also compress amplitude slightly
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --transform halve_tempo --all \
    --param amplitude_scale=0.8

# Let suggest_transform() pick the best transform per phrase automatically
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --suggest --bpm-threshold 120

# Preview the plan without writing any file
python cli.py phrase-transform input.funscript \
    --assessment assessment.json \
    --suggest --dry-run
```

### Finalize command — auto blend + smooth before saving

After applying all phrase transforms, run `finalize` to smooth inter-phrase seams
and apply a light global finishing pass.  The UI calls this automatically on Save.

```bash
# Standard finalize (blend_seams + final_smooth at defaults)
python cli.py finalize transformed.funscript

# Custom seam threshold and smoother finishing pass
python cli.py finalize transformed.funscript \
    --param seam_max_velocity=0.30 \
    --param seam_max_strength=0.80 \
    --param smooth_strength=0.05

# Skip seam blending, run only the final smooth pass
python cli.py finalize transformed.funscript --skip-seams

# Write to a specific output path
python cli.py finalize transformed.funscript --output finalized.funscript
```

### Programmatic use

```python
from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

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

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).  Written by human and Claude AI (Claude Sonnet).*
