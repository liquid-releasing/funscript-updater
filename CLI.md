# CLI Reference

All pipeline stages and utilities are available through `cli.py`.

```
python cli.py <command> [options]
```

---

## Quick start — full pipeline in one command

```bash
python cli.py pipeline input.funscript --output-dir output/
```

Runs all three stages (assess -> transform -> customize) and writes:

| File | Description |
| --- | --- |
| `output/<name>.assessment.json` | Structural analysis |
| `output/<name>.transformed.funscript` | BPM-threshold transformed |
| `output/<name>.customized.funscript` | Final output |

Optional flags for the pipeline command:

| Flag | Description |
| --- | --- |
| `--output-dir DIR` | Output directory (default: `./output/`) |
| `--perf FILE` | Performance windows JSON |
| `--break FILE` | Break windows JSON |
| `--raw FILE` | Raw-preserve windows JSON |
| `--beats FILE` | Beats JSON (enables beat accents in Stage 3) |
| `--transformer-config FILE` | Custom transformer settings |
| `--customizer-config FILE` | Custom customizer settings |

---

## Individual stage commands

### Step 1 — Assess

Analyze the funscript structure and produce an assessment JSON.

```bash
python cli.py assess input.funscript
python cli.py assess input.funscript --output assessment.json
python cli.py assess input.funscript --config analyzer_config.json
```

Output includes: duration, BPM, action count, phases, cycles, patterns,
phrases, and BPM transitions.

---

### Step 2 — Review (human step)

Open `assessment.json` and inspect `bpm_transitions` and per-phrase BPMs.
Use this to decide which sections need performance, break, or raw windows.

The Streamlit UI (`streamlit run ui/streamlit/app.py`) provides an
interactive way to review and tag sections.

---

### Step 3 — Transform

Apply BPM-threshold transformation.

```bash
python cli.py transform input.funscript --assessment assessment.json
python cli.py transform input.funscript \
    --assessment assessment.json \
    --output transformed.funscript \
    --config transformer_config.json
```

---

### Step 4 — Customize

Apply user-defined performance, break, and raw windows.

```bash
python cli.py customize transformed.funscript --assessment assessment.json
python cli.py customize transformed.funscript \
    --assessment assessment.json \
    --output customized.funscript \
    --config customizer_config.json \
    --perf performance.json \
    --break break.json \
    --raw raw.json \
    --beats beats.json
```

Window JSON format (the `"config"` key is optional):

```json
[
  {
    "start": "00:01:10.000",
    "end": "00:01:25.000",
    "label": "chorus",
    "config": { "max_velocity": 0.28 }
  }
]
```

---

## Visualization

Requires `matplotlib` (`pip install matplotlib`).

```bash
python cli.py visualize input.funscript --assessment assessment.json
python cli.py visualize input.funscript \
    --assessment assessment.json \
    --output motion.png
```

---

## Config — dump default settings to JSON

```bash
# Transformer config (Stage 3)
python cli.py config --output transformer_config.json

# Customizer config (Stage 4)
python cli.py config --customizer --output customizer_config.json

# Analyzer config (Stage 1)
python cli.py config --analyzer --output analyzer_config.json
```

Edit the generated JSON, then pass it back with `--config` (or
`--transformer-config` / `--customizer-config` for the `pipeline` command).

---

## Tests

Run all 151 tests (core pipeline + CLI + UI common layer):

```bash
python cli.py test
```

Or via unittest directly:

```bash
# Core + CLI tests (106)
python -m unittest discover -s tests -v

# UI common-layer tests only (45)
python -m unittest discover -s ui/common/tests -v
```

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](LICENSE).  Written by human and Claude AI (Claude Sonnet).*
