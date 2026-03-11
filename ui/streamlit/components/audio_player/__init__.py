# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Phrase-restricted audio player Streamlit component.

Renders an HTML5 audio player scoped to a single phrase window, with:
- Play / Pause, Stop, Back 5 s, Forward 5 s controls
- A live Plotly.js chart of the phrase's actions with an animated playhead
- A 📌 "Set split here" button that returns the current time to Python

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
    audio_hash: str,
    start_ms: int,
    end_ms: int,
    actions: list,
    split_points: list,
    # Local mode: stream directly from the media server.
    audio_url: str | None = None,
    # Web mode: base64-encoded audio embedded in the component.
    audio_b64: str | None = None,
    audio_mime: str | None = None,
    key: str | None = None,
) -> dict | None:
    """Render the phrase-restricted audio player component.

    Exactly one of *audio_url* (local/desktop mode) or *audio_b64* + *audio_mime*
    (web mode) must be supplied.

    Parameters
    ----------
    audio_hash:
        Short string that changes only when the audio file changes (e.g.
        ``f"{path}:{mtime}"``).  Used by the component to decide whether to
        reload the audio source without comparing the full base64 blob.
    start_ms:
        Phrase start in milliseconds — audio playback begins here.
    end_ms:
        Phrase end in milliseconds — audio playback stops here.
    actions:
        List of ``{"at": int, "pos": int}`` dicts for the phrase chart.
    split_points:
        Existing split ms values shown as dashed vertical lines on the chart.
    audio_url:
        HTTP URL served by the local media server.  When set, ``audio_b64``
        and ``audio_mime`` are ignored.
    audio_b64:
        Base64-encoded audio bytes (web mode only).
    audio_mime:
        MIME type, e.g. ``"audio/mpeg"`` or ``"audio/wav"`` (web mode only).
    key:
        Streamlit widget key.  Change when switching phrase instances to
        reset the component state.

    Returns
    -------
    dict or None
        ``{"split_ms": <int>}`` when the user clicks 📌 Set split here,
        ``None`` otherwise.
    """
    return _component_func(
        audio_url=audio_url,
        audio_b64=audio_b64,
        audio_mime=audio_mime,
        audio_hash=audio_hash,
        start_ms=start_ms,
        end_ms=end_ms,
        actions=actions,
        split_points=split_points,
        key=key,
        default=None,
    )
