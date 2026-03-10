# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""TransformerConfig: tunable parameters for the BPM-threshold transformer."""

import dataclasses
import json
from dataclasses import dataclass


@dataclass
class TransformerConfig:
    # BPM threshold: phrases below this are passed through unchanged;
    # phrases at or above this receive the default amplitude transform.
    bpm_threshold: float = 120.0

    # Default transform (applied to high-BPM phrases)
    amplitude_scale: float = 2.0   # position scaled around center (50)
    lpf_default: float = 0.10      # low-pass filter strength for high-BPM phrases

    # Time scaling is applied globally (not per-phrase) to avoid timeline collisions.
    # Set to 1.0 to disable.
    time_scale: float = 1.0

    def __post_init__(self) -> None:
        if self.bpm_threshold <= 0:
            raise ValueError(f"bpm_threshold must be > 0, got {self.bpm_threshold}")
        if self.amplitude_scale <= 0:
            raise ValueError(f"amplitude_scale must be > 0, got {self.amplitude_scale}")
        if not 0.0 <= self.lpf_default <= 1.0:
            raise ValueError(f"lpf_default must be in [0, 1], got {self.lpf_default}")
        if self.time_scale <= 0:
            raise ValueError(f"time_scale must be > 0, got {self.time_scale}")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TransformerConfig":
        valid = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "TransformerConfig":
        with open(path) as f:
            return cls.from_dict(json.load(f))
