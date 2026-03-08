# user_customization

User-defined window customization of funscripts (Pipeline Stage 3).

The customizer layers on top of the transformer output. The user defines
time windows using human-readable `HH:MM:SS.mmm` timestamps in JSON files
and calls `customize()` to apply per-window processing.

## Window types and priority

| Priority | Type | Effect |
| --- | --- | --- |
| 1 (highest) | **Raw** | Original actions copied verbatim — no changes |
| 2 | **Performance** | Velocity limiting, reversal softening, position compression |
| 3 | **Break** | Positions pulled toward centre (50), amplitude reduced |
| — | (everywhere) | Cycle-aware dynamics and beat accents outside raw windows |

Raw windows take absolute priority: any action inside a raw window is
restored from the original funscript and no other processing is applied to it.

## Window JSON format

Each window file is a JSON array. The `"label"` and `"config"` keys are
optional; omit `"config"` to use the global `CustomizerConfig` values for
that window.

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
relevant window type (see tables below). Per-window overrides are merged
on top of the global config, so you only need to specify the fields you
want to change.

## Configuration — `CustomizerConfig`

### Performance window fields

| Field | Default | Description |
| --- | --- | --- |
| `max_velocity` | `0.32` | Maximum allowed velocity (position units per ms) |
| `reversal_soften` | `0.62` | Fraction of reversal magnitude to soften at direction changes |
| `height_blend` | `0.75` | Blend weight toward original position after softening |
| `compress_bottom` | `15` | Minimum position after compression (0–100) |
| `compress_top` | `92` | Maximum position after compression (0–100) |
| `lpf_performance` | `0.16` | Low-pass filter strength applied after performance transform |
| `timing_jitter_ms` | `3` | Minimum milliseconds enforced between consecutive actions |

### Break window fields

| Field | Default | Description |
| --- | --- | --- |
| `break_amplitude_reduce` | `0.40` | Fraction of the distance to centre (50) pulled per action |
| `lpf_break` | `0.30` | Low-pass filter strength applied after break transform |

### Global dynamics fields (applied outside raw windows)

| Field | Default | Description |
| --- | --- | --- |
| `cycle_dynamics_strength` | `0.10` | Amplitude of sinusoidal cycle-phase modulation |
| `cycle_dynamics_center` | `50` | Centre position for cycle-phase modulation |
| `beat_accent_radius_ms` | `40` | Half-width of the window around beat times for accents |
| `beat_accent_amount` | `4` | Position nudge applied at beat accent points |

**Beat accents** are only active when a beats JSON file is loaded via
`load_beats_from_file()`. Actions within `beat_accent_radius_ms` of a
beat time are nudged away from centre by `beat_accent_amount` positions.

Config can be saved and loaded as JSON:

```python
from user_customization import CustomizerConfig

cfg = CustomizerConfig(max_velocity=0.25)
cfg.save("customizer_config.json")
cfg2 = CustomizerConfig.load("customizer_config.json")
```

Unknown keys in the JSON file are silently ignored.

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
customizer.load_beats_from_file("beats.json")  # optional — enables beat accents
customizer.customize()
customizer.save("customized.funscript")
```

If a window file path does not exist, that window type is treated as
empty (no error is raised).

### Via the UI

The Streamlit app exports window JSON files automatically from the user's
tagged work items. Use the **Export** tab or the sidebar **Export window JSONs**
button to write the files, then run the pipeline from CLI or call
`Project.export_windows()` / `ui/common/pipeline.py` to execute the full chain.

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
