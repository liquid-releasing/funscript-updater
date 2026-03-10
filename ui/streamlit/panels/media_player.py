# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Media player helper for the Funscript Forge UI.

Renders an inline audio or video player cued to a specific phrase start time.
Called from the Phrase Editor and Pattern Editor when a media file is loaded.

Usage::

    from ui.streamlit.panels.media_player import render_player
    render_player(start_ms=phrase["start_ms"], key_suffix="phrase_42")
"""

from __future__ import annotations

import os

import streamlit as st

AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".ogg", ".aac"}
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS


@st.cache_data(show_spinner=False)
def _read_media_bytes(path: str, _mtime: float) -> bytes:
    """Read a media file into bytes.  Cached per (path, mtime) so changes invalidate."""
    with open(path, "rb") as f:
        return f.read()


def render_player(start_ms: int, key_suffix: str = "") -> None:
    """Render an audio/video player cued to *start_ms* if a media file is loaded.

    If no media file is in session state, renders nothing.

    Parameters
    ----------
    start_ms:
        Phrase start time in milliseconds.  The player seeks to this position.
    key_suffix:
        Unique suffix appended to Streamlit widget keys to avoid collisions
        when the player is rendered in multiple locations on the same page.
    """
    media_path: str | None = st.session_state.get("media_path")
    if not media_path or not os.path.exists(media_path):
        return

    ext = os.path.splitext(media_path)[1].lower()
    if ext not in MEDIA_EXTS:
        return

    start_s = int(start_ms / 1000)
    file_size_mb = os.path.getsize(media_path) / 1_000_000
    label = f"▶ Media — {os.path.basename(media_path)} (cued to {_fmt_s(start_s)})"

    with st.expander(label, expanded=False):
        if file_size_mb > 200:
            st.caption(
                f"File is {file_size_mb:.0f} MB — loading may take a moment."
            )

        try:
            media_bytes = _read_media_bytes(media_path, os.path.getmtime(media_path))
            if ext in AUDIO_EXTS:
                st.audio(media_bytes, start_time=start_s)
            else:
                st.video(media_bytes, start_time=start_s)
        except Exception as exc:
            st.warning(f"Could not load media: {exc}")


def find_matching_media(funscript_path: str, uploads_dir: str) -> str | None:
    """Return the first media file in *uploads_dir* whose stem matches the funscript.

    For example, ``MyVideo.funscript`` matches ``MyVideo.mp4`` or ``MyVideo.mp3``.
    """
    if not os.path.isdir(uploads_dir):
        return None
    stem = os.path.splitext(os.path.basename(funscript_path))[0]
    for ext in [".mp4", ".mkv", ".mov", ".mp3", ".m4a", ".wav", ".ogg"]:
        candidate = os.path.join(uploads_dir, stem + ext)
        if os.path.exists(candidate):
            return candidate
    return None


def _fmt_s(seconds: int) -> str:
    """Format seconds as M:SS."""
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"
