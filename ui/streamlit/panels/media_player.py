# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Media player helper for the FunscriptForge UI.

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
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".webm"}
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS

_AUDIO_MIME: dict[str, str] = {
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
    ".wav": "audio/wav",  ".ogg": "audio/ogg", ".aac": "audio/aac",
}
_VIDEO_MIME: dict[str, str] = {
    ".mp4": "video/mp4",      ".mkv": "video/x-matroska",
    ".mov": "video/quicktime", ".webm": "video/webm",
}

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
    split_points: list | None = None,
) -> dict | None:
    """Render a phrase-restricted media player for audio or video.

    Uses the interactive phrase-restricted component (waveform chart,
    animated playhead, ±1 s / frame-step controls, volume, speed) for
    both audio and video when *end_ms* is supplied.  Falls back to
    ``st.audio()`` / ``st.video()`` when *end_ms* is not given.

    Returns ``{"split_ms": int}`` when the 📌 pin is clicked, ``None``
    otherwise.

    Parameters
    ----------
    start_ms:
        Phrase start in milliseconds.
    end_ms:
        Phrase end in milliseconds.  Required for the interactive player.
    actions:
        List of ``{"at": int, "pos": int}`` for the waveform chart.
    key_suffix:
        Unique suffix for Streamlit widget keys.
    split_points:
        Existing split ms values shown as dashed lines (Pattern Editor).
    """
    import base64

    media_path: str | None = st.session_state.get("media_path")
    if not media_path or not os.path.exists(media_path):
        return None

    ext = os.path.splitext(media_path)[1].lower()
    if ext not in MEDIA_EXTS:
        return None

    corrupt_msg = validate_media_file_deep(media_path)
    if corrupt_msg:
        st.warning(
            f"Media file may be corrupt — {corrupt_msg}  ({os.path.basename(media_path)})"
        )
        return None

    if end_ms is not None:
        # Interactive phrase-restricted component (audio + video)
        from ui.streamlit.components.audio_player import phrase_audio_player

        is_video   = ext in VIDEO_EXTS
        media_type = "video" if is_video else "audio"
        mime       = (_VIDEO_MIME if is_video else _AUDIO_MIME).get(
            ext, "video/mp4" if is_video else "audio/mpeg"
        )
        media_hash = f"{media_path}:{os.path.getmtime(media_path)}"

        if _IS_LOCAL and _MEDIA_PORT:
            return phrase_audio_player(
                media_type=media_type,
                media_url=_local_media_url(media_path),
                media_mime=mime,
                media_hash=media_hash,
                start_ms=start_ms,
                end_ms=end_ms,
                actions=actions or [],
                split_points=split_points or [],
                key=f"player_{key_suffix}",
            )

        # Web mode: base64-encode the file.
        # Refuse files over the size cap to prevent OOM on the server.
        file_bytes = os.path.getsize(media_path)
        if file_bytes > _WEB_MODE_MAX_BYTES:
            size_mb = file_bytes / 1_000_000
            st.warning(
                f"Media file is {size_mb:.0f} MB — too large to load in web mode "
                f"(limit {_WEB_MODE_MAX_BYTES // 1_000_000} MB).  "
                "Use the desktop launcher to stream large files without size limits."
            )
            return None

        raw = _read_media_bytes(media_path, os.path.getmtime(media_path))
        b64 = base64.b64encode(raw).decode()
        return phrase_audio_player(
            media_type=media_type,
            media_b64=b64,
            media_mime=mime,
            media_hash=media_hash,
            start_ms=start_ms,
            end_ms=end_ms,
            actions=actions or [],
            split_points=split_points or [],
            key=f"player_{key_suffix}",
        )

    # Fallback: simple st.audio / st.video without phrase restriction
    start_s      = int(start_ms / 1000)
    file_size_mb = os.path.getsize(media_path) / 1_000_000
    label        = f"▶ {os.path.basename(media_path)} (cued to {_fmt_s(start_s)})"

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


# Per-process validation cache: (realpath, mtime) → error_string | None.
# Avoids re-running ffprobe on every Streamlit re-render for the same file.
_VALIDATION_CACHE: dict[tuple, str | None] = {}
_VALIDATION_CACHE_MAX = 64   # trim when it grows too large

# Hard cap for base64 web-mode uploads (bytes).  Files larger than this are
# refused in web mode to prevent OOM; local mode streams from disk instead.
_WEB_MODE_MAX_BYTES = 500 * 1024 * 1024  # 500 MB

# ffprobe subprocess time-out (seconds).  Short enough that a corrupt or
# unresponsive file doesn't freeze the render thread for long.
_FFPROBE_TIMEOUT = 5


def _ffprobe_available() -> bool:
    """Return True if ffprobe is on PATH (cached at import time)."""
    import shutil
    return shutil.which("ffprobe") is not None


def validate_media_file_deep(path: str) -> str | None:
    """Validate a media file using ffprobe (if available) then magic bytes.

    Results are cached per ``(realpath, mtime)`` pair so ffprobe is only
    invoked once per file change — subsequent Streamlit re-renders are instant.

    Returns ``None`` if the file appears valid, or a short error string.
    """
    import subprocess

    # Resolve symlinks — prevents a symlink with an allowed extension (e.g.
    # ``evil.mp4``) from pointing at an arbitrary file.
    try:
        real = os.path.realpath(path)
    except OSError:
        return "Cannot resolve file path."

    if not os.path.isfile(real):
        return "File not found."

    # Re-validate when mtime changes; serve from cache otherwise.
    try:
        mtime = os.path.getmtime(real)
    except OSError:
        return "Cannot read file."

    cache_key = (real, mtime)
    if cache_key in _VALIDATION_CACHE:
        return _VALIDATION_CACHE[cache_key]

    # 1. Magic-byte check (fast, no subprocess).
    result: str | None = validate_media_file(real)

    # 2. ffprobe deep check (only if magic bytes passed).
    if result is None and _ffprobe_available():
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-i", real],
                capture_output=True, text=True, timeout=_FFPROBE_TIMEOUT,
            )
            stderr = proc.stderr.strip()
            if proc.returncode != 0 or stderr:
                msg = stderr[:200] if stderr else f"exit code {proc.returncode}"
                result = f"ffprobe: {msg}"
        except FileNotFoundError:
            pass  # ffprobe vanished between the which() check and now
        except subprocess.TimeoutExpired:
            result = f"ffprobe timed out after {_FFPROBE_TIMEOUT} s — file may be corrupt"
        except Exception as exc:
            result = f"ffprobe check failed: {exc}"

    # Trim cache before inserting to keep memory bounded.
    if len(_VALIDATION_CACHE) >= _VALIDATION_CACHE_MAX:
        _VALIDATION_CACHE.clear()
    _VALIDATION_CACHE[cache_key] = result
    return result


def validate_media_file(path: str) -> str | None:
    """Check a media file for obvious corruption using magic-byte signatures.

    Reads only the first 12 bytes — fast enough to run on every load.

    Returns ``None`` if the file looks intact, or a short human-readable
    error string if it appears corrupt, unreadable, or has an unsupported
    extension.  Uses an allowlist — any extension not explicitly recognised
    is rejected rather than passed through.

    Supported containers: MP3, MP4/M4A/MOV, WAV, OGG, WebM/MKV, AAC.
    AVI is not supported (browsers cannot decode it natively); a helpful
    ffmpeg conversion hint is returned instead.
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

    # MP3: ID3 tag or ADTS sync bytes (0xFF 0xEx/0xFx)
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

    # OGG
    if ext == ".ogg":
        if header[:4] == b"OggS":
            return None
        return "Not a valid OGG file (missing OggS capture pattern)."

    # WebM / MKV: EBML magic bytes 0x1A 0x45 0xDF 0xA3
    if ext in {".webm", ".mkv"}:
        if header[:4] == b"\x1a\x45\xdf\xa3":
            return None
        return "Not a valid WebM/MKV file (missing EBML header)."

    # AAC (ADTS): sync bytes 0xFF 0xF1 (MPEG-4) or 0xFF 0xF9 (MPEG-2)
    if ext == ".aac":
        if header[0] == 0xFF and header[1] in (0xF1, 0xF9):
            return None
        return "Not a valid AAC file (missing ADTS sync bytes)."

    # Reject everything else — unknown extensions are not allowed.
    # Note: .avi is not supported in local mode because most browsers cannot
    # decode it natively.  Convert to MP4 first:
    #   ffmpeg -i input.avi -c:v libx264 -c:a aac output.mp4
    # AVI transcoding is planned for the paid SaaS tier.
    if ext == ".avi":
        return (
            ".avi files are not supported — browsers cannot play AVI natively.\n"
            "Convert to MP4 with: ffmpeg -i input.avi -c:v libx264 -c:a aac output.mp4"
        )
    return f"Unsupported file type '{ext}'. Allowed: mp3, m4a, mp4, mov, wav, ogg, webm, mkv, aac."


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
