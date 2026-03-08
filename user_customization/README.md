# user_customization

User-defined window customization of funscripts (Pipeline Stage 3).

The customizer layers on top of the transformer output.  The user defines
time windows using human-readable `HH:MM:SS.mmm` timestamps in JSON files
and calls `customize()` to apply per-window processing.

## Window types and priority

| Priority | Type | Effect |
| --- | --- | --- |
| 1 (highest) | **Raw** | Original actions copied verbatim — no changes |
| 2 | **Performance** | Velocity limiting, reversal softening, position compression |
| 3 | **Break** | Positions pulled toward centre (50), amplitude reduced |
| — | (everywhere) | Cycle-aware dynamics and beat accents outside raw windows |

## Window JSON format

Each window file is a JSON array.  The `"config"` key is optional; omit it
to use the global `CustomizerConfig` values for that window.

```json
[
  {
    "start": "00:01:10.000",
    "end":   "00:01:25.000",
    "label": "chorus",
    "config": { "max_velocity": 0.28, "reversal_soften": 0.50 }
  }
]
```

Keys allowed in `"config"` match the `CustomizerConfig` field names for the
relevant window type (see table below).

## Configuration — `CustomizerConfig`

### Performance window fields

| Field | Default | Description |
| --- | --- | --- |
| `max_velocity` | `0.32` | Maximum allowed velocity (pos/ms) |
| `reversal_soften` | `0.62` | Fraction of reversal magnitude to soften |
| `height_blend` | `0.75` | Blend weight toward original after softening |
| `compress_bottom` | `15` | Minimum position after compression |
| `compress_top` | `92` | Maximum position after compression |
| `lpf_performance` | `0.16` | Low-pass filter strength for perf windows |
| `timing_jitter_ms` | `3` | Minimum ms between consecutive actions |

### Break window fields

| Field | Default | Description |
| --- | --- | --- |
| `break_amplitude_reduce` | `0.40` | Fraction of distance to centre applied |
| `lpf_break` | `0.30` | Low-pass filter strength for break windows |

### Global dynamics fields

| Field | Default | Description |
| --- | --- | --- |
| `cycle_dynamics_strength` | `0.10` | Amplitude of cycle-phase modulation |
| `cycle_dynamics_center` | `50` | Centre position for cycle dynamics |
| `beat_accent_radius_ms` | `40` | Radius around beat times for accent |
| `beat_accent_amount` | `4` | Position nudge applied at beat accents |

Config can be saved/loaded as JSON:

```python
from user_customization import CustomizerConfig

cfg = CustomizerConfig(max_velocity=0.25)
cfg.save("customizer_config.json")
cfg2 = CustomizerConfig.load("customizer_config.json")
```

## Usage

### Programmatically

```python
from user_customization import WindowCustomizer

customizer = WindowCustomizer()
customizer.load_funscript("transformed.funscript")
customizer.load_assessment_from_file("assessment.json")   # for cycle dynamics
customizer.load_manual_overrides(
    perf_path="performance.json",
    break_path="break.json",
    raw_path="raw.json",
)
customizer.load_beats_from_file("beats.json")  # optional
customizer.customize()
customizer.save("customized.funscript")
```

### Via the UI

The Streamlit app exports window JSON files automatically from the user's
work items.  Use `Project.export_windows()` or `ui/common/pipeline.py` to
run the full chain in one call.

### Via CLI

```bash
python cli.py customize transformed.funscript \
    --assessment assessment.json \
    --perf performance.json \
    --break break.json \
    --raw raw.json \
    --output customized.funscript
```

## Modules

| File | Contents |
| --- | --- |
| `customizer.py` | `WindowCustomizer` class |
| `config.py` | `CustomizerConfig` dataclass |
| `__init__.py` | Re-exports `WindowCustomizer`, `CustomizerConfig` |

## Tests

```bash
python -m unittest tests.test_customizer -v
```

12 tests covering: load funscript + assessment, customize output shape,
positions in `[0, 100]`, save → valid JSON, performance window loaded
correctly (3-tuple with config dict), missing window file treated as empty,
log output, and config round-trip / save-load / unknown-key handling.
