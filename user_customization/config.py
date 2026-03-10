# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""CustomizerConfig: tunable parameters for user-defined window customization."""

import dataclasses
import json
from dataclasses import dataclass


@dataclass
class CustomizerConfig:
    # Performance window transform (Task 2)
    max_velocity: float = 0.32
    reversal_soften: float = 0.62
    height_blend: float = 0.75
    compress_bottom: int = 15
    compress_top: int = 92
    lpf_performance: float = 0.16
    timing_jitter_ms: int = 3

    # Break window transform (Task 3)
    break_amplitude_reduce: float = 0.40
    lpf_break: float = 0.30

    # Cycle-aware dynamics (Task 5)
    cycle_dynamics_strength: float = 0.10
    cycle_dynamics_center: int = 50

    # Beat-synced accents (Task 6)
    beat_accent_radius_ms: int = 40
    beat_accent_amount: int = 4

    def __post_init__(self) -> None:
        if self.max_velocity <= 0:
            raise ValueError(f"max_velocity must be > 0, got {self.max_velocity}")
        if not 0.0 <= self.reversal_soften <= 1.0:
            raise ValueError(f"reversal_soften must be in [0, 1], got {self.reversal_soften}")
        if not 0.0 <= self.height_blend <= 1.0:
            raise ValueError(f"height_blend must be in [0, 1], got {self.height_blend}")
        if self.compress_bottom >= self.compress_top:
            raise ValueError(
                f"compress_bottom ({self.compress_bottom}) must be < compress_top ({self.compress_top})"
            )
        if not 0.0 <= self.lpf_performance <= 1.0:
            raise ValueError(f"lpf_performance must be in [0, 1], got {self.lpf_performance}")
        if not 0.0 <= self.lpf_break <= 1.0:
            raise ValueError(f"lpf_break must be in [0, 1], got {self.lpf_break}")
        if self.beat_accent_radius_ms < 0:
            raise ValueError(f"beat_accent_radius_ms must be >= 0, got {self.beat_accent_radius_ms}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CustomizerConfig":
        valid = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "CustomizerConfig":
        with open(path) as f:
            return cls.from_dict(json.load(f))
