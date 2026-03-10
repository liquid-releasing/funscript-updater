# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""example_plugin.py — Template for a custom PhraseTransform plugin.

Copy this file, rename it (remove the 'example_' prefix), and customise
_MyTransform._transform() with your own logic.

This file is committed as a template and is NOT loaded by the plugin scanner
(files named example_*.py are excluded via .gitignore convention and the
scanner only processes files that match *.py but are not example_*.py — see
load_user_transforms() in phrase_transforms.py for details).

Actually, this example IS loaded — it registers 'example_clamp_center' which
is a harmless demo that clamps positions to the central 20-80 band.
"""

from dataclasses import dataclass, field
from pattern_catalog.phrase_transforms import PhraseTransform, TransformParam


@dataclass
class _ClampCenter(PhraseTransform):
    """Clamp every position to the band [lo, hi] — a simple range limiter."""

    def _transform(self, actions: list, p: dict) -> list:
        lo = p["lo"]
        hi = p["hi"]
        for a in actions:
            a["pos"] = max(lo, min(hi, a["pos"]))
        return actions


TRANSFORM = _ClampCenter(
    key         = "example_clamp_center",
    name        = "Example: Clamp Center",
    description = "Clamp all positions to a configurable band — demo plugin.",
    structural  = False,
    params      = {
        "lo": TransformParam(
            label   = "Low clamp",
            type    = "int",
            default = 20,
            min_val = 0,
            max_val = 49,
            step    = 5,
            help    = "Minimum output position.",
        ),
        "hi": TransformParam(
            label   = "High clamp",
            type    = "int",
            default = 80,
            min_val = 51,
            max_val = 100,
            step    = 5,
            help    = "Maximum output position.",
        ),
    },
)
