# visualizations

Reusable matplotlib-based visualization components for funscript analysis.

## Requirements

```
pip install matplotlib
```

## Modules

### `motion.py` — MotionVisualizer

Renders a motion curve with phase boundary markers from a funscript and its assessment.

**Output:** A PNG file showing:
- Motion curve (position 0–100 over time)
- Phase boundary tick marks (vertical gray lines)
- X-axis formatted as `MM:SS`
- Title includes source filename and average BPM

## Usage

### Via CLI

```bash
python cli.py visualize path/to/input.funscript \
    --assessment path/to/assessment.json \
    --output path/to/output.png
```

If `--output` is omitted, the PNG is saved alongside the input file with a `_visualization.png` suffix.

### Programmatically

```python
import json
from models import AssessmentResult
from visualizations.motion import MotionVisualizer

with open("input.funscript") as f:
    data = json.load(f)

assessment = AssessmentResult.load("assessment.json")

viz = MotionVisualizer(assessment, data["actions"])
viz.plot("output.png")
```

### Check matplotlib availability

```python
from visualizations.motion import HAS_MATPLOTLIB
print(HAS_MATPLOTLIB)  # True if matplotlib is installed
```

## Extending

Add new visualizers as separate modules in this directory (e.g., `heatmap.py`, `phases.py`) and export them from `__init__.py`. Each visualizer should:

1. Guard against missing matplotlib with a `HAS_MATPLOTLIB` flag
2. Accept an `AssessmentResult` and/or raw actions list
3. Expose a `plot(output_path: str) -> None` method

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).  Written by human and Claude AI (Claude Sonnet).*
