# Extending the Transform Catalog

There are two ways to add custom transforms without editing project code:

| Method | File type | Best for | Security risk |
| --- | --- | --- | --- |
| **JSON recipe** | `.json` in `user_transforms/` | Chaining existing built-in steps | **None** — data only |
| **Python plugin** | `.py` in `plugins/` | Custom math or logic not covered by built-ins | **High** — see below |

Both are loaded automatically at startup.  Use `python cli.py list-transforms` at any time to
verify your transform is registered.

> **Security note — JSON recipes are recommended.**
> JSON recipes can only chain *existing built-in transforms* and may only pass
> scalar parameter values (numbers, strings, booleans).  They are validated
> before use and cannot execute arbitrary code.
>
> Python plugins run with **full system access** — they can read/write files,
> make network calls, and execute shell commands.  They are **disabled by
> default**.  See [Security Model](#security-model) below before enabling them.

---

## Security Model

### JSON recipes (safe by default)

Every entry in a JSON recipe file is validated against a strict schema before
being registered:

| Check | Detail |
| --- | --- |
| **Key format** | Must match `^[a-z][a-z0-9_]{0,63}$` — lowercase, no spaces, no special chars |
| **Steps are non-empty** | At least one step required |
| **Step transforms are built-ins** | `"transform"` value must be a key in the built-in catalog; user-defined keys are not allowed as steps |
| **Params are scalars** | Each param value must be a number, string, or boolean — nested objects and arrays are rejected |

Entries that fail validation are skipped with a message to stderr; other entries
in the same file are still loaded.  You can validate a file without loading the
app using:

```bash
python cli.py validate-plugins
```

### Python plugins (disabled by default)

Python plugin files in `plugins/` are **not loaded** unless the environment
variable `FUNSCRIPT_PLUGINS_ENABLED` is set to `1`, `true`, or `yes`:

```bash
# Enable (only if you trust the plugin source)
FUNSCRIPT_PLUGINS_ENABLED=1 streamlit run ui/streamlit/app.py

# Or set in your shell profile for persistent use
export FUNSCRIPT_PLUGINS_ENABLED=1
```

**When files are present but the flag is not set**, a warning is printed to
stderr explaining the situation.  No code from the file is executed.

**Why this matters:** A Python file placed in `plugins/` by a malicious actor
(social engineering, a downloaded "transform pack", a shared machine) would
execute with the same permissions as the running process.  The flag makes the
risk explicit and opt-in.

**Files whose name starts with `example_`** are always skipped regardless of
the flag — they are reference templates committed to the repository, not
user-supplied plugins.

#### Recommended approach

Prefer JSON recipes for all custom transforms.  They cover the vast majority of
use cases (recenter, scale, chain transforms) without any security exposure.
Use Python plugins only when you need custom math that cannot be expressed as a
recipe, and only load your own code.

---

## Method 1 — JSON Recipe

A recipe composes existing built-in transforms into a named pipeline.
No Python required.

### Step 1 — Create the file

Drop a `.json` file in `user_transforms/`.  The file name is not significant; use something
descriptive, e.g. `my_transforms.json`.

```bash
user_transforms/
    my_transforms.json    ← your file goes here
    example_recipe.json   ← committed template (read-only reference)
```

> **Note:** your own files are gitignored; only `example_*.json` templates are tracked.

### Step 2 — Write the recipe

A file may be a single object or a JSON array of objects.

```json
[
  {
    "key":         "my_lift_and_scale",
    "name":        "Lift and Scale",
    "description": "Re-center displaced motion then expand amplitude.",
    "structural":  false,
    "steps": [
      { "transform": "recenter",        "params": { "target_center": 50 } },
      { "transform": "amplitude_scale", "params": { "scale": 1.8 } },
      { "transform": "smooth",          "params": { "strength": 0.08 } }
    ]
  }
]
```

**Fields:**

| Field | Required | Description |
| --- | --- | --- |
| `key` | Yes | Machine-readable identifier.  Must be unique; cannot clash with a built-in key. |
| `name` | Yes | Human-readable display name shown in the UI and CLI. |
| `description` | No | One-sentence explanation. |
| `structural` | No | Set `true` if any step returns a different number of actions (e.g. `halve_tempo`).  Default `false`. |
| `steps` | Yes | Ordered list of steps.  Each step: `{"transform": "<key>", "params": {...}}`. |

Steps run left-to-right; the output of each step feeds into the next.
Omitting `params` (or passing `{}`) uses each step's built-in defaults.

### Step 3 — Find available step keys and their params

```bash
python cli.py list-transforms           # all transforms, one-line per entry
python cli.py list-transforms --verbose # also shows every param name, range, and default
```

### Step 4 — Verify your recipe is loaded

```bash
python cli.py list-transforms --user-only
```

You should see your key in the output.  If not, check stderr for a warning
(malformed JSON or a key clash will be reported there).

### Step 5 — Apply it

```bash
# Apply to a specific phrase (1-based index)
python cli.py phrase-transform my.funscript \
    --assessment my_assessment.json \
    --transform my_lift_and_scale \
    --phrase 3

# Dry-run to preview the plan without writing
python cli.py phrase-transform my.funscript \
    --assessment my_assessment.json \
    --transform my_lift_and_scale \
    --all \
    --dry-run
```

### Step 6 — Tune at call time (optional)

Individual step parameters can be overridden when calling
`phrase-transform` with `--param`:

```bash
# scale param inside amplitude_scale step is not directly tuneable via recipe steps
# at call time — to expose a tuneable param, use a Python plugin instead.
```

> If you need a tuneable parameter that the caller can adjust at run time
> (e.g. `--param scale=2.0`), use a **Python plugin** instead (see Method 2).

---

## Method 2 — Python Plugin

> **Planned for the SaaS / cloud paid tier — not a supported local feature.**
>
> Python plugins run with full system access and cannot be safely sandboxed on
> a local machine.  The infrastructure exists and is tested, but plugins are
> disabled by default.  See the [Security Model](#security-model) above for
> the full rationale and the opt-in flag for developer use.
>
> **For local use, write a JSON recipe (Method 1) instead.**  JSON recipes
> cover the vast majority of real-world cases with zero security exposure.

A plugin is a plain Python file that registers one or more `PhraseTransform` instances.
Use this when you need custom math, conditionals, or parameters that callers can tune.

### Plugin Step 1 — Create the file

Drop a `.py` file in `plugins/`.

```bash
plugins/
    my_plugin.py          ← your file goes here
    example_plugin.py     ← committed template (read-only reference)
```

> **Note:** your own files are gitignored; only `example_*.py` templates are tracked.

### Plugin Step 2 — Write the plugin

```python
# plugins/my_plugin.py

from dataclasses import dataclass, field
from pattern_catalog.phrase_transforms import PhraseTransform, TransformParam


@dataclass
class _MyTransform(PhraseTransform):
    """Multiply every position by a configurable scale factor."""

    def _transform(self, actions: list, p: dict) -> list:
        # `actions` is a deep copy — mutate freely.
        # `p` is a dict of {param_key: resolved_value} (defaults + caller overrides).
        for a in actions:
            a["pos"] = max(0, min(100, int(a["pos"] * p["scale"])))
        return actions


TRANSFORM = _MyTransform(
    key         = "my_scale",
    name        = "My Scale",
    description = "Multiply every position by a configurable scale factor.",
    structural  = False,
    params      = {
        "scale": TransformParam(
            label   = "Scale factor",
            type    = "float",
            default = 0.8,
            min_val = 0.0,
            max_val = 2.0,
            step    = 0.05,
            help    = "Values < 1 reduce amplitude; values > 1 expand it.",
        ),
    },
)
```

**Rules:**

- The module must expose `TRANSFORM` (single instance) or `TRANSFORMS` (list of instances).
- `key` must be unique and must not clash with any built-in.
- Set `structural = True` if `_transform` returns a different number of actions or changes
  their timestamps (e.g. a custom tempo change).
- The `actions` argument to `_transform` is already a deep copy — you may mutate it freely.
- `p` contains resolved parameter values: defaults merged with any caller-supplied overrides.
- A plugin that raises an exception during loading is skipped silently (error goes to stderr).

### Plugin Step 3 — Verify the plugin is loaded

```bash
python cli.py list-transforms --user-only
```

### Plugin Step 4 — Apply it

```bash
# Apply with default params
python cli.py phrase-transform my.funscript \
    --assessment my_assessment.json \
    --transform my_scale \
    --all

# Override a param at call time
python cli.py phrase-transform my.funscript \
    --assessment my_assessment.json \
    --transform my_scale \
    --all \
    --param scale=1.5

# Dry-run to preview without writing
python cli.py phrase-transform my.funscript \
    --assessment my_assessment.json \
    --transform my_scale \
    --phrase 2 \
    --dry-run
```

### Plugin Step 5 — Register multiple transforms (optional)

A single plugin file can expose a list:

```python
TRANSFORMS = [_MyScaleTransform(...), _MyClampTransform(...)]
```

---

## Checking for key clashes

Built-in keys are:

```bash
python cli.py list-transforms --format json | python -c "
import json, sys
d = json.load(sys.stdin)
print([k for k, v in d.items() if v['source'] == 'builtin'])
"
```

Or just run `python cli.py list-transforms` and look for entries without `[user]`.

---

## Cookbook

### Tame a frantic phrase (halve tempo + smooth)

```json
{
  "key": "my_tame",
  "name": "Tame",
  "description": "Halve tempo then lightly smooth.",
  "structural": true,
  "steps": [
    { "transform": "halve_tempo",  "params": {} },
    { "transform": "smooth",       "params": { "strength": 0.10 } }
  ]
}
```

### Boost a weak/stingy phrase

```json
{
  "key": "my_boost",
  "name": "Boost",
  "description": "Normalize then amplify to 80% of full range.",
  "structural": false,
  "steps": [
    { "transform": "normalize",      "params": { "target_hi": 90, "target_lo": 10 } },
    { "transform": "amplitude_scale","params": { "scale": 0.8 } }
  ]
}
```

### Clamp to a device-safe window (plugin)

See `plugins/example_plugin.py` for a complete plugin that clamps positions to a
configurable `[lo, hi]` band (the `example_clamp_center` transform).

---

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Transform not listed after adding file | File not in correct directory, or startup not re-run | Run `python cli.py validate-plugins`; restart the app if needed |
| `key clashes with a built-in — skipped` on stderr | Your key matches a built-in name | Choose a different key |
| Unknown step key warning during apply | A step `"transform"` value doesn't match any catalog key | Run `python cli.py list-transforms` to see valid keys |
| Plugin silently skipped at startup | Syntax or import error in the plugin file | Run `python plugins/my_plugin.py` directly to see the traceback |
| `structural` mismatch | Recipe has `structural: false` but uses `halve_tempo` | Set `"structural": true` in the recipe |

### Security-related symptoms

| Symptom | Cause | Fix |
| --- | --- | --- |
| `invalid entry — key … must be …` on stderr | Recipe key contains uppercase, spaces, or special characters | Use only lowercase letters, digits, and underscores; must start with a letter |
| `steps[N].transform '…' is not a known built-in key` | A recipe step references a user-defined key or an unknown key | Steps may only use built-in transforms; run `python cli.py list-transforms` to see valid keys |
| `steps[N].params['…'] must be a scalar` | A param value is a nested object or array | Use only numbers, strings, or booleans as param values |
| Python plugin not loaded, no error message | `FUNSCRIPT_PLUGINS_ENABLED` not set | Check stderr for the "found but NOT loaded" warning; set the env var only if you trust the plugin source |
| Plugin ignored even with `FUNSCRIPT_PLUGINS_ENABLED=1` | File name starts with `example_` | Rename the file to something that does not start with `example_` |
| `validate-plugins` reports errors on a file you trust | Schema violation in the JSON | Run `python cli.py validate-plugins --verbose` for the full error message per entry |

---

## See also

- `user_transforms/README.md` — JSON recipe format reference
- `plugins/README.md` — Python plugin interface reference
- `pattern_catalog/README.md` — Built-in transform catalog documentation
- `python cli.py list-transforms --verbose` — Live catalog with full param details

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).  Written by human and Claude AI (Claude Sonnet).*
