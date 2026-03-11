# plugins

> **Python plugins are a planned SaaS / cloud tier feature.**
>
> The code infrastructure exists and is tested, but Python plugins are
> **disabled by default** on the local app because they run with full system
> access (file system, network, subprocesses) and cannot be safely sandboxed
> on a user's machine.
>
> **For local use: add JSON recipe files to `user_transforms/` instead.**
> JSON recipes can chain any built-in transform and cover the vast majority
> of real-world use cases with no security exposure.
>
> See `internal/SECURITY.md` → *Python Plugin Roadmap Decision* for the full
> rationale, and `pattern_catalog/EXTENDING_TRANSFORMS.md` for the security
> model and troubleshooting guide.

---

## Enabling plugins locally (advanced / developer use only)

If you are developing or testing plugins on your own machine and understand
the risk, set the environment variable before starting the app:

```bash
FUNSCRIPT_PLUGINS_ENABLED=1 streamlit run ui/streamlit/app.py
# or
FUNSCRIPT_PLUGINS_ENABLED=1 python cli.py list-transforms --user-only
```

Verify your plugin loaded:

```bash
python cli.py validate-plugins --verbose
```

**Only enable this flag for plugins you wrote yourself or have reviewed.**
A malicious `.py` file in this directory would execute with your full user
permissions at app startup.

---

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
- Files named `example_*.py` are committed as templates and are **always
  skipped**, even when `FUNSCRIPT_PLUGINS_ENABLED=1`.  Your own files are
  gitignored.

## See also

- `user_transforms/README.md` — JSON recipe transforms (safe, no flag needed)
- `pattern_catalog/EXTENDING_TRANSFORMS.md` — full security model and troubleshooting
- `internal/SECURITY.md` — threat analysis and Python plugin roadmap decision

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).  Written by human and Claude AI (Claude Sonnet).*
