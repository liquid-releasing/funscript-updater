# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Phrase-restricted media player Streamlit component.

Supports both audio and video playback scoped to a single phrase window.

Controls: Play/Pause, Stop, ±1 s seek, frame step (◀fr / fr▶), volume,
speed (0.25× / 0.5× / 1× / 2×), 📌 Set split here.

Displays a Plotly waveform chart with animated red playhead, plus a
position readout (``⏸ MM:SS.mmm  pos NN``) shown in green below the
controls.

Position readout update triggers
---------------------------------
The readout is **intentionally blank during playback** — it updates only on:

* **Pause** (click ▶ again, or playback reaches phrase end)
* **Stop** — readout is cleared (position resets to phrase start)
* **±1 s seek** buttons
* **◀fr / fr▶** frame-step buttons

This is by design: showing a rapidly changing position during playback
would be distracting and hard to read.  Pause at the moment of interest
to capture the exact timestamp and funscript position (0–100) of the
action currently at the playhead.

Python usage::

    from ui.streamlit.components.audio_player import phrase_audio_player

    result = phrase_audio_player(
        audio_b64=encoded_bytes,
        audio_mime="audio/mpeg",
        audio_hash="myfile.mp3:1234567890.0",
        start_ms=phrase["start_ms"],
        end_ms=phrase["end_ms"],
        actions=actions_in_phrase,
        split_points=[],
        key="ap_frantic_0",
    )
    if result and "split_ms" in result:
        # user pinned a split point
        _add_split_point(label, inst_idx, cycle, result["split_ms"])
        st.rerun(scope="app")

Video (new)::

    result = phrase_audio_player(
        media_type="video",
        media_url=url,          # local-mode HTTP stream
        media_mime="video/mp4",
        media_hash="file.mp4:1234567890.0",
        start_ms=phrase["start_ms"],
        end_ms=phrase["end_ms"],
        actions=actions_in_phrase,
        split_points=[],
        key="vp_phrase_0",
    )
"""

from __future__ import annotations

import os

import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

_component_func = components.declare_component(
    "phrase_audio_player",
    path=_FRONTEND_DIR,
)


def phrase_audio_player(
    *,
    # Legacy audio_* params — kept for backward compatibility.
    audio_hash: str = "",
    # Phrase window
    start_ms: int,
    end_ms: int,
    actions: list,
    split_points: list,
    # Generic media params (preferred over audio_* when provided).
    media_type: str = "audio",          # "audio" | "video"
    media_hash: str | None = None,
    media_url: str | None = None,       # local-mode HTTP stream
    media_b64: str | None = None,       # web-mode base64 bytes
    media_mime: str | None = None,
    # Legacy audio_* aliases (still accepted for backward compat).
    audio_url: str | None = None,
    audio_b64: str | None = None,
    audio_mime: str | None = None,
    key: str | None = None,
) -> dict | None:
    """Render the phrase-restricted media player component.

    Pass exactly one of *media_url* (local/desktop mode) or
    *media_b64* + *media_mime* (web mode).  The legacy ``audio_*``
    parameters are accepted for backward compatibility and are used
    when the corresponding ``media_*`` params are not provided.

    Parameters
    ----------
    media_type:
        ``"audio"`` (default) or ``"video"``.  Controls whether the
        video display area is shown above the waveform chart.
    media_hash:
        Short string that changes only when the file changes (e.g.
        ``f"{path}:{mtime}"``).  Used to avoid reloading on re-renders.
    start_ms / end_ms:
        Phrase window in milliseconds.
    actions:
        ``[{"at": int, "pos": int}]`` list for the waveform chart.
    split_points:
        Existing split-point timestamps (ms) shown as dashed lines.
    media_url / audio_url:
        HTTP URL from the local media server.
    media_b64 / audio_b64:
        Base64-encoded file bytes (web mode).
    media_mime / audio_mime:
        MIME type string.
    key:
        Streamlit widget key.

    Returns
    -------
    dict or None
        ``{"split_ms": <int>}`` when 📌 is clicked; ``None`` otherwise.
    """
    return _component_func(
        # Generic media params (JS reads these first, falls back to audio_*)
        media_type=media_type,
        media_hash=media_hash or audio_hash,
        media_url=media_url or audio_url,
        media_b64=media_b64 or audio_b64,
        media_mime=media_mime or audio_mime,
        # Legacy audio_* pass-through so old JS callers still work
        audio_hash=audio_hash,
        audio_url=audio_url,
        audio_b64=audio_b64,
        audio_mime=audio_mime,
        # Phrase window + chart data
        start_ms=start_ms,
        end_ms=end_ms,
        actions=actions,
        split_points=split_points,
        key=key,
        default=None,
    )
