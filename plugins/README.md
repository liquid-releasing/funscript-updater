# plugins

Drop Python files here to add custom transforms that require logic beyond
what JSON recipes can express.  Each file is imported automatically when the
app starts.

## Interface

A plugin file must expose one of:

- `TRANSFORM` — a single `PhraseTransform` instance
- `TRANSFORMS` — a list of `PhraseTransform` instances

```python
from dataclasses import dataclass, field
from pattern_catalog.phrase_transforms import PhraseTransform, TransformParam

@dataclass
class _MyTransform(PhraseTransform):
    def _transform(self, actions: list, p: dict) -> list:
        # actions is a deep copy — mutate freely.
        # p is a dict of {param_key: resolved_value} built from self.params defaults
        # plus any caller-supplied overrides.
        for a in actions:
            a["pos"] = max(0, min(100, int(a["pos"] * p["scale"])))
        return actions

TRANSFORM = _MyTransform(
    key         = "my_scale",
    name        = "My Scale",
    description = "Multiply every position by a scale factor.",
    structural  = False,
    params      = {
        "scale": TransformParam(
            label   = "Scale",
            type    = "float",
            default = 0.8,
            min_val = 0.0,
            max_val = 2.0,
            step    = 0.05,
            help    = "Multiplier applied to every position value.",
        ),
    },
)
```

## Rules

- `key` must be unique and must **not** clash with any built-in catalog key.
  Clashing keys are skipped with a warning.
- `structural = True` if your transform returns a different number of actions
  or changes their timestamps (e.g. tempo changes).  Callers use this flag to
  decide whether to do an in-place position update or a full slice replacement.
- A broken plugin (import error, exception during load) is skipped with a
  stderr message; it does not abort the app.
- Files named `example_*.py` are committed as templates; your own files are
  gitignored.

## See also

`user_transforms/README.md` — for simpler, no-code JSON recipe transforms.

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).  Written by human and Claude AI (Claude Sonnet).*
