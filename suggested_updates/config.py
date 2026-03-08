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
