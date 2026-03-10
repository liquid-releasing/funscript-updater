# user_transforms

Drop JSON recipe files here to add custom transforms to the catalog without
editing any project code.  Each file is loaded automatically when the app
starts.

## Format

A file may contain a single object or a JSON array of objects.

```json
{
  "key":         "my_recenter_amplify",
  "name":        "Recenter + Amplify",
  "description": "Shift midpoint to 50, then scale amplitude up.",
  "structural":  false,
  "steps": [
    { "transform": "recenter",        "params": { "target_center": 50  } },
    { "transform": "amplitude_scale", "params": { "scale": 2.5         } },
    { "transform": "smooth",          "params": { "strength": 0.12     } }
  ]
}
```

| Field | Required | Description |
| --- | --- | --- |
| `key` | Yes | Machine-readable identifier.  Must be unique and not clash with a built-in key. |
| `name` | Yes | Human-readable display name shown in the UI and CLI. |
| `description` | No | One-sentence explanation. |
| `structural` | No | `true` if any step changes the number of actions (e.g. `halve_tempo`).  Default `false`. |
| `steps` | Yes | Ordered list of transform steps.  Each step is `{"transform": <key>, "params": {...}}`. |

### Available step keys

Any key from `TRANSFORM_CATALOG`.  To see all available keys with parameter
names and defaults, run:

```bash
python cli.py list-transforms
python cli.py list-transforms --verbose    # also shows each param's range and default
python cli.py list-transforms --user-only  # your recipes + plugins only
```

Or open the **Transform Catalog** tab in the UI.

### Notes

- Steps are applied left-to-right; the output of each step feeds into the next.
- An unknown step key is skipped with a warning printed to stderr.
- A key that clashes with a built-in transform is ignored entirely.
- Files in this directory named `example_*.json` are committed as templates;
  your own files are gitignored.

## Example

See `example_recipe.json` in this directory.
