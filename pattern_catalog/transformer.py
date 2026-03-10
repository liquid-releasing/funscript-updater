"""FunscriptTransformer: BPM-threshold based transformation (Part 2).

For each action, the transformer looks up which phrase it belongs to and
compares that phrase's BPM against a configurable threshold:

  phrase.bpm < bpm_threshold  → action is passed through unchanged (original pos)
  phrase.bpm >= bpm_threshold → default amplitude transform applied

Actions that fall outside all phrases use the overall assessment BPM.

Note: time scaling (time_scale) is applied globally — not per-phrase — to
avoid timeline discontinuities at phrase boundaries.

Typical usage::

    transformer = FunscriptTransformer()
    transformer.load_funscript("input.funscript")
    transformer.load_assessment_from_file("assessment.json")
    transformer.transform()
    transformer.save("output.funscript")
"""

import copy
import json
from typing import List, Optional, Tuple

from models import AssessmentResult, Phrase
from utils import LoggingMixin, low_pass_filter, find_phrase_at
from .config import TransformerConfig

_WindowPair = Tuple[int, int]


class FunscriptTransformer(LoggingMixin):
    """Applies BPM-threshold transformation to a funscript.

    Phrases at or above bpm_threshold receive the default amplitude transform.
    Phrases below bpm_threshold are passed through with original positions.
    """

    def __init__(self, config: Optional[TransformerConfig] = None):
        super().__init__()
        self.config = config or TransformerConfig()
        self._data: dict = {}
        self._actions: list = []
        self._original_actions: list = []
        self._phrases: List[Phrase] = []
        self._overall_bpm: float = 0.0

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_funscript(self, path: str) -> None:
        """Load the source funscript to be transformed.

        Raises:
            FileNotFoundError: if the file does not exist.
            ValueError: if the file is not valid JSON or missing the 'actions' list.
        """
        try:
            with open(path) as f:
                self._data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Funscript not found: {path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in funscript '{path}': {e}")
        if "actions" not in self._data or not isinstance(self._data["actions"], list):
            raise ValueError(
                f"Funscript '{path}' is missing a required 'actions' list."
            )
        self._actions = self._data["actions"]
        self._original_actions = copy.deepcopy(self._actions)
        self._log(f"Loaded funscript: {path} ({len(self._actions)} actions)")

    def load_assessment(self, assessment: AssessmentResult) -> None:
        """Load phrase BPM data from an AssessmentResult object."""
        self._phrases = assessment.phrases
        self._overall_bpm = assessment.bpm
        self._log(
            f"Loaded assessment: {len(self._phrases)} phrases, "
            f"overall BPM={self._overall_bpm:.1f}, "
            f"threshold={self.config.bpm_threshold}"
        )

    def load_assessment_from_file(self, path: str) -> None:
        """Load phrase BPM data from a saved assessment JSON file."""
        assessment = AssessmentResult.load(path)
        self.load_assessment(assessment)

    # ------------------------------------------------------------------
    # Transformation
    # ------------------------------------------------------------------

    def transform(self) -> list:
        """Apply BPM-threshold transform and return the transformed actions list."""
        cfg = self.config
        actions = self._actions
        orig = self._original_actions

        passthrough_count = 0
        transform_count = 0

        # --- Optional global time scaling ---
        if cfg.time_scale != 1.0:
            for a in actions:
                a["at"] = int(a["at"] * cfg.time_scale)
            self._log(f"Applied global time_scale={cfg.time_scale}")

        # --- Per-action: pass-through or amplitude transform ---
        for i, action in enumerate(actions):
            t = orig[i]["at"]  # use original timestamp to look up phrase
            phrase = self._phrase_at(t)
            effective_bpm = phrase.bpm if phrase else self._overall_bpm

            if effective_bpm < cfg.bpm_threshold:
                # Pass-through: keep original position
                action["pos"] = orig[i]["pos"]
                passthrough_count += 1
            else:
                # Default amplitude transform: scale position around center (50)
                centered = orig[i]["pos"] - 50
                action["pos"] = max(0, min(100, int(50 + centered * cfg.amplitude_scale)))
                transform_count += 1

        # --- LPF smoothing: only on transformed (high-BPM) actions ---
        positions = [a["pos"] for a in actions]
        strengths = []
        for i, action in enumerate(actions):
            t = orig[i]["at"]
            phrase = self._phrase_at(t)
            effective_bpm = phrase.bpm if phrase else self._overall_bpm
            strengths.append(cfg.lpf_default if effective_bpm >= cfg.bpm_threshold else 0.0)

        smoothed = low_pass_filter(positions, strengths)
        for i, p in enumerate(smoothed):
            actions[i]["pos"] = int(p)

        self._log(
            f"Transform complete: {passthrough_count} actions passed through "
            f"(BPM < {cfg.bpm_threshold}), {transform_count} actions transformed."
        )
        return actions

    def save(self, path: str) -> None:
        """Write the transformed funscript to disk."""
        self._data["actions"] = self._actions
        with open(path, "w") as f:
            json.dump(self._data, f, indent=2)
        self._log(f"Saved output: {path}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _phrase_at(self, t_ms: int) -> Optional[Phrase]:
        """Return the phrase containing timestamp t_ms, or None."""
        return find_phrase_at(self._phrases, t_ms)
