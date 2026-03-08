"""phrase_transforms.py — Catalog of per-phrase funscript transforms.

Each PhraseTransform describes one named transform that can be applied to
the actions within a phrase window.  The catalog is used by both the CLI
pipeline and the Streamlit UI phrase-detail panel.

Usage::

    from suggested_updates.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

    spec = TRANSFORM_CATALOG["amplitude_scale"]
    new_actions = spec.apply(phrase_actions)

    key = suggest_transform(phrase_dict, bpm_threshold=120.0)
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils import low_pass_filter


# ------------------------------------------------------------------
# Parameter descriptor
# ------------------------------------------------------------------

@dataclass
class TransformParam:
    """Metadata for one tuneable parameter of a transform."""
    label: str
    type: str           # "float" | "int" | "bool"
    default: Any
    min_val: Any = None
    max_val: Any = None
    step: Any = None
    help: str = ""


# ------------------------------------------------------------------
# Transform base
# ------------------------------------------------------------------

@dataclass
class PhraseTransform:
    """A named, parameterised transform that modifies a slice of actions.

    Attributes
    ----------
    key:         Short machine-readable identifier.
    name:        Human-readable display name.
    description: One-sentence explanation of what the transform does.
    params:      Dict of parameter name → TransformParam descriptor.
    """
    key: str
    name: str
    description: str
    params: Dict[str, TransformParam] = field(default_factory=dict)

    def apply(self, actions: list, param_values: Optional[Dict[str, Any]] = None) -> list:
        """Return a new action list with the transform applied.

        Parameters
        ----------
        actions:
            Slice of funscript actions (``[{"at": ms, "pos": 0-100}, …]``).
            The originals are not mutated.
        param_values:
            Override values for any parameter keys.  Missing keys fall back
            to the param's default.
        """
        p = {k: v.default for k, v in self.params.items()}
        if param_values:
            p.update({k: v for k, v in param_values.items() if k in p})
        result = copy.deepcopy(actions)
        return self._transform(result, p)

    def _transform(self, actions: list, p: dict) -> list:
        raise NotImplementedError


# ------------------------------------------------------------------
# Concrete transforms
# ------------------------------------------------------------------

class _Passthrough(PhraseTransform):
    def _transform(self, actions, p):
        return actions


class _AmplitudeScale(PhraseTransform):
    """Scale positions around the midpoint (50)."""
    def _transform(self, actions, p):
        scale = p["scale"]
        for a in actions:
            centered = a["pos"] - 50
            a["pos"] = max(0, min(100, int(50 + centered * scale)))
        return actions


class _Normalize(PhraseTransform):
    """Expand positions to fill the full 0-100 range."""
    def _transform(self, actions, p):
        if not actions:
            return actions
        lo = min(a["pos"] for a in actions)
        hi = max(a["pos"] for a in actions)
        span = hi - lo
        if span == 0:
            return actions
        target_lo = p["target_lo"]
        target_hi = p["target_hi"]
        target_span = target_hi - target_lo
        for a in actions:
            a["pos"] = max(0, min(100, int(target_lo + (a["pos"] - lo) / span * target_span)))
        return actions


class _Smooth(PhraseTransform):
    """Apply a low-pass filter to reduce rapid position changes."""
    def _transform(self, actions, p):
        strength = p["strength"]
        positions = [a["pos"] for a in actions]
        smoothed = low_pass_filter(positions, [strength] * len(positions))
        for a, pos in zip(actions, smoothed):
            a["pos"] = int(pos)
        return actions


class _ClampRange(PhraseTransform):
    """Compress positions into a sub-range (e.g. upper or lower half)."""
    def _transform(self, actions, p):
        lo = p["range_lo"]
        hi = p["range_hi"]
        span = hi - lo
        for a in actions:
            a["pos"] = max(0, min(100, int(lo + a["pos"] / 100.0 * span)))
        return actions


class _Invert(PhraseTransform):
    """Mirror positions around 50 (pos = 100 - pos)."""
    def _transform(self, actions, p):
        for a in actions:
            a["pos"] = 100 - a["pos"]
        return actions


class _BoostEnds(PhraseTransform):
    """Push positions toward the extremes (0 or 100), increasing contrast."""
    def _transform(self, actions, p):
        strength = p["strength"]   # 0.0 = no change, 1.0 = full push to 0/100
        for a in actions:
            pos = a["pos"] / 100.0
            # Sigmoid-like push: values > 0.5 go toward 1, values < 0.5 go toward 0
            if pos >= 0.5:
                pushed = 0.5 + (pos - 0.5) * (1.0 + strength)
            else:
                pushed = 0.5 - (0.5 - pos) * (1.0 + strength)
            a["pos"] = max(0, min(100, int(pushed * 100)))
        return actions


# ------------------------------------------------------------------
# Catalog
# ------------------------------------------------------------------

TRANSFORM_CATALOG: Dict[str, PhraseTransform] = {
    t.key: t for t in [
        _Passthrough(
            key="passthrough",
            name="Passthrough",
            description="Keep original positions unchanged.",
        ),
        _AmplitudeScale(
            key="amplitude_scale",
            name="Amplitude Scale",
            description="Scale stroke depth around the midpoint — use >1 to amplify, <1 to reduce.",
            params={
                "scale": TransformParam(
                    label="Scale factor", type="float", default=2.0,
                    min_val=0.1, max_val=5.0, step=0.1,
                    help="1.0 = no change. 2.0 = double stroke depth.",
                ),
            },
        ),
        _Normalize(
            key="normalize",
            name="Normalize Range",
            description="Expand positions to fill a target range (default: full 0–100).",
            params={
                "target_lo": TransformParam(
                    label="Target low", type="int", default=0,
                    min_val=0, max_val=49, step=5,
                ),
                "target_hi": TransformParam(
                    label="Target high", type="int", default=100,
                    min_val=51, max_val=100, step=5,
                ),
            },
        ),
        _Smooth(
            key="smooth",
            name="Smooth",
            description="Apply a low-pass filter to reduce jitter and rapid micro-movements.",
            params={
                "strength": TransformParam(
                    label="Smoothing strength", type="float", default=0.15,
                    min_val=0.01, max_val=0.5, step=0.01,
                    help="Higher = more smoothing. 0.15 is a light touch.",
                ),
            },
        ),
        _ClampRange(
            key="clamp_upper",
            name="Clamp Upper Half",
            description="Compress positions into the upper half (50–100) — keeps motion in the intense zone.",
            params={
                "range_lo": TransformParam(label="Range low",  type="int", default=50, min_val=0,  max_val=60),
                "range_hi": TransformParam(label="Range high", type="int", default=100, min_val=70, max_val=100),
            },
        ),
        _ClampRange(
            key="clamp_lower",
            name="Clamp Lower Half",
            description="Compress positions into the lower half (0–50) — for gentler or break-style sections.",
            params={
                "range_lo": TransformParam(label="Range low",  type="int", default=0, min_val=0,  max_val=30),
                "range_hi": TransformParam(label="Range high", type="int", default=50, min_val=40, max_val=70),
            },
        ),
        _Invert(
            key="invert",
            name="Invert",
            description="Mirror positions around 50 — flips the stroke direction.",
        ),
        _BoostEnds(
            key="boost_contrast",
            name="Boost Contrast",
            description="Push positions toward 0 and 100 to increase the dynamic range.",
            params={
                "strength": TransformParam(
                    label="Strength", type="float", default=0.5,
                    min_val=0.1, max_val=2.0, step=0.1,
                    help="How hard positions are pushed toward the extremes.",
                ),
            },
        ),
    ]
}


# ------------------------------------------------------------------
# Suggestion logic
# ------------------------------------------------------------------

def suggest_transform(phrase: dict, bpm_threshold: float = 120.0) -> str:
    """Return the catalog key of the most appropriate transform for *phrase*.

    Rules (in priority order):
    1. pattern_label contains "transition" → smooth
    2. bpm < bpm_threshold               → passthrough (already slow / gentle)
    3. bpm >= bpm_threshold, amplitude
       span < 40 (compressed waveform)   → normalize (open it up first)
    4. bpm >= bpm_threshold              → amplitude_scale (standard boost)
    """
    bpm = phrase.get("bpm", 0.0)
    label = (phrase.get("pattern_label") or "").lower()

    if "transition" in label:
        return "smooth"

    if bpm < bpm_threshold:
        return "passthrough"

    # Estimate amplitude span from the phrase dict if available
    amp_span = phrase.get("amplitude_span", 100)  # 0-100; default assumes full range
    if amp_span < 40:
        return "normalize"

    return "amplitude_scale"
