# User Transforms

Drop JSON files here to add custom transforms to the Transform Catalog dropdown.
They appear under the "── My Transforms ──" separator in the Phrase Editor and Pattern Editor.

## Format

Each file is an array of transform objects:

```json
[
  {
    "key":         "my_key",
    "name":        "My Transform Name",
    "description": "What it does",
    "steps": [
      {"transform": "recenter",        "params": {"target_center": 50}},
      {"transform": "amplitude_scale", "params": {"scale": 2.0}}
    ]
  }
]
```

## Available built-in steps

passthrough, amplitude_scale, normalize, boost_contrast, shift,
recenter, clamp_upper, clamp_lower, invert, smooth, blend_seams,
final_smooth, break, performance, beat_accent, three_one, halve_tempo

## Notes
- Keys must not clash with built-ins (duplicates are skipped with a warning)
- Restart Streamlit after adding or editing files here
