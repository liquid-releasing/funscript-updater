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

# Local desktop mode: launcher sets these so we can stream media via HTTP
# instead of encoding the whole file as base64.
_IS_LOCAL   = os.environ.get("FUNSCRIPT_FORGE_LOCAL") == "1"
_MEDIA_PORT = os.environ.get("FUNSCRIPT_FORGE_MEDIA_PORT", "")


def _local_media_url(file_path: str) -> str:
    """Build the URL for serving *file_path* via the local media server."""
    from urllib.parse import quote
    return f"http://127.0.0.1:{_MEDIA_PORT}/media?path={quote(file_path)}"


@st.cache_data(show_spinner=False)
def _read_media_bytes(path: str, _mtime: float) -> bytes:
    """Read a media file into bytes.  Cached per (path, mtime) so changes invalidate."""
    with open(path, "rb") as f:
        return f.read()


def render_player(
    start_ms: int,
    end_ms: int | None = None,
    actions: list | None = None,
    key_suffix: str = "",
) -> dict | None:
    """Render an audio player cued to the phrase [start_ms, end_ms].

    For audio files, renders the interactive phrase-restricted player with
    playhead chart, play/stop/back/forward controls, and a 📌 split-pin button.
    For video files, falls back to ``st.video()`` cued to start_ms.

    Returns the component return value (``{"split_ms": int}`` when pinned) or
    ``None``.  The return value is only meaningful for audio.

    Parameters
    ----------
    start_ms:
        Phrase start in milliseconds.
    end_ms:
        Phrase end in milliseconds.  Required for the interactive player;
        if omitted, the audio plays from start_ms with no enforced end.
    actions:
        List of ``{"at": int, "pos": int}`` for the phrase chart.  If
        omitted, the chart renders empty.
    key_suffix:
        Unique suffix for Streamlit widget keys.
    """
    import base64

    media_path: str | None = st.session_state.get("media_path")
    if not media_path or not os.path.exists(media_path):
        return None

    ext = os.path.splitext(media_path)[1].lower()
    if ext not in MEDIA_EXTS:
        return None

    corrupt_msg = validate_media_file(media_path)
    if corrupt_msg:
        st.warning(f"Media file may be corrupt — {corrupt_msg}  ({os.path.basename(media_path)})")
        return None

    if ext in AUDIO_EXTS and end_ms is not None:
        # Interactive phrase-restricted player
        from ui.streamlit.components.audio_player import phrase_audio_player

        _mime_map = {
            ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
            ".wav": "audio/wav",  ".ogg": "audio/ogg", ".aac": "audio/aac",
        }
        mime       = _mime_map.get(ext, "audio/mpeg")
        audio_hash = f"{media_path}:{os.path.getmtime(media_path)}"

        if _IS_LOCAL and _MEDIA_PORT:
            # Local mode: browser streams directly from the media server —
            # no base64 encoding, no large file in Python memory.
            return phrase_audio_player(
                audio_url=_local_media_url(media_path),
                audio_mime=mime,
                audio_hash=audio_hash,
                start_ms=start_ms,
                end_ms=end_ms,
                actions=actions or [],
                split_points=[],
                key=f"player_{key_suffix}",
            )

        # Web mode: encode to base64 and embed in the component.
        raw = _read_media_bytes(media_path, os.path.getmtime(media_path))
        b64 = base64.b64encode(raw).decode()
        return phrase_audio_player(
            audio_b64=b64,
            audio_mime=mime,
            audio_hash=audio_hash,
            start_ms=start_ms,
            end_ms=end_ms,
            actions=actions or [],
            split_points=[],
            key=f"player_{key_suffix}",
        )

    # Fallback: simple st.audio / st.video cued to start
    start_s = int(start_ms / 1000)
    file_size_mb = os.path.getsize(media_path) / 1_000_000
    label = f"▶ Media — {os.path.basename(media_path)} (cued to {_fmt_s(start_s)})"

    with st.expander(label, expanded=False):
        if file_size_mb > 200:
            st.caption(f"File is {file_size_mb:.0f} MB — loading may take a moment.")
        try:
            media_bytes = _read_media_bytes(media_path, os.path.getmtime(media_path))
            if ext in AUDIO_EXTS:
                st.audio(media_bytes, start_time=start_s)
            else:
                st.video(media_bytes, start_time=start_s)
        except Exception as exc:
            st.warning(f"Could not load media: {exc}")

    return None


def validate_media_file(path: str) -> str | None:
    """Check a media file for obvious corruption using magic-byte signatures.

    Reads only the first 12 bytes — fast enough to run on every load.

    Returns ``None`` if the file looks intact, or a short human-readable
    error string if it appears corrupt or unreadable.

    Supported containers: MP3, MP4/M4A/MOV, WAV, OGG, WebM/MKV.
    Files with unrecognised headers (e.g. AAC raw, AVI) are passed through
    without a corruption verdict rather than generating false positives.
    """
    if not os.path.isfile(path):
        return "File not found."
    size = os.path.getsize(path)
    if size == 0:
        return "File is empty (0 bytes)."
    if size < 12:
        return f"File is too small ({size} bytes) — likely truncated."

    try:
        with open(path, "rb") as fh:
            header = fh.read(12)
    except OSError as exc:
        return f"Cannot read file: {exc}"

    ext = os.path.splitext(path)[1].lower()

    # MP3: starts with ID3 tag or sync bytes (0xFF followed by 0xE0–0xFF)
    if ext == ".mp3":
        if header[:3] == b"ID3":
            return None
        if header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
            return None
        return "Not a valid MP3 file (missing ID3 tag or sync bytes)."

    # MP4 / M4A / MOV: 'ftyp' box at byte offset 4
    if ext in {".mp4", ".m4a", ".mov"}:
        if header[4:8] == b"ftyp":
            return None
        # Some MP4s start with 'moov' or 'mdat' directly (no ftyp)
        if header[4:8] in {b"moov", b"mdat", b"free", b"wide"}:
            return None
        return "Not a valid MP4/M4A/MOV file (missing ftyp/moov box)."

    # WAV: RIFF….WAVE
    if ext == ".wav":
        if header[:4] == b"RIFF" and header[8:12] == b"WAVE":
            return None
        return "Not a valid WAV file (missing RIFF/WAVE header)."

    # OGG (covers .ogg and .oga)
    if ext in {".ogg", ".oga"}:
        if header[:4] == b"OggS":
            return None
        return "Not a valid OGG file (missing OggS capture pattern)."

    # WebM / MKV: EBML magic bytes 0x1A 0x45 0xDF 0xA3
    if ext in {".webm", ".mkv"}:
        if header[:4] == b"\x1a\x45\xdf\xa3":
            return None
        return "Not a valid WebM/MKV file (missing EBML header)."

    # Unknown extension — no verdict, let the browser decide.
    return None


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
