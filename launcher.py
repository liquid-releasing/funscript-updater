# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""FunscriptForge launcher.

Entry point for both development (`python launcher.py`) and the PyInstaller
packaged executable.  Starts the Streamlit web server on a free local port
and opens the default browser automatically.
"""

from __future__ import annotations

import http.server
import os
import re
import socket
import sys
import threading
import time
import webbrowser


def _find_free_port() -> int:
    """Return an OS-assigned free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _open_browser(url: str, delay: float = 3.0) -> None:
    """Wait *delay* seconds then open *url* in the default browser."""
    time.sleep(delay)
    webbrowser.open(url)


def _base_dir() -> str:
    """Return the *read-only* bundle root (PyInstaller) or project root (dev)."""
    if getattr(sys, "frozen", False):
        # PyInstaller extracts read-only assets under sys._MEIPASS.
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    """Return the *writable* root for user data (output/, catalog, logs).

    G32: sys._MEIPASS is read-only; writable files must live beside the exe.
    In development this is identical to _base_dir() (the project root).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


class _MediaHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP handler that serves local media files by absolute path.

    URL format: GET /media?path=<url-encoded-absolute-path>

    Supports HTTP Range requests so browsers can seek large audio/video files
    without downloading the whole file first.
    """

    _MIME = {
        ".mp3": "audio/mpeg",  ".m4a": "audio/mp4",
        ".wav": "audio/wav",   ".ogg": "audio/ogg",  ".aac": "audio/aac",
        ".mp4": "video/mp4",   ".mkv": "video/x-matroska",
        ".mov": "video/quicktime", ".webm": "video/webm",
    }

    def do_GET(self) -> None:  # noqa: N802
        from urllib.parse import urlparse, parse_qs, unquote
        qs = parse_qs(urlparse(self.path).query)
        file_path = unquote(qs.get("path", [""])[0])

        if not file_path or not os.path.isabs(file_path):
            self.send_response(400)
            self.end_headers()
            return

        # Resolve symlinks before any further checks.  A symlink whose name
        # ends in ".mp4" could otherwise point at an arbitrary file (e.g. a
        # shell config or SSH key).
        try:
            real_path = os.path.realpath(file_path)
        except OSError:
            self.send_response(400)
            self.end_headers()
            return

        if not os.path.isfile(real_path):
            self.send_response(404)
            self.end_headers()
            return

        # Check the extension of the *resolved* path, not the original name,
        # so a symlink named "trick.mp4" → "sensitive.txt" is refused.
        ext = os.path.splitext(real_path)[1].lower()

        # Allowlist: only serve known media extensions — refuse everything else.
        if ext not in self._MIME:
            self.send_response(403)
            self.end_headers()
            return

        file_path = real_path  # use resolved path for all subsequent I/O

        content_type = self._MIME[ext]
        file_size    = os.path.getsize(file_path)
        range_header = self.headers.get("Range", "")

        if range_header:
            m = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                start  = int(m.group(1))
                end    = int(m.group(2)) if m.group(2) else file_size - 1
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(length))
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(file_path, "rb") as fh:
                    fh.seek(start)
                    self.wfile.write(fh.read(length))
                return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with open(file_path, "rb") as fh:
            self.wfile.write(fh.read())

    def log_message(self, *_args) -> None:  # noqa: D401
        pass  # suppress console noise


def _start_media_server(port: int) -> None:
    """Run the media file server (blocking — call in a daemon thread)."""
    server = http.server.HTTPServer(("127.0.0.1", port), _MediaHandler)
    server.serve_forever()


def main() -> None:
    base = _base_dir()
    app_path = os.path.join(base, "ui", "streamlit", "app.py")

    if not os.path.exists(app_path):
        sys.exit(f"[FunscriptForge] Cannot find app.py at: {app_path}")

    port       = _find_free_port()
    media_port = _find_free_port()
    url        = f"http://localhost:{port}"

    # Mark this as a local desktop session so the UI can skip file-upload widgets.
    os.environ["FUNSCRIPT_FORGE_LOCAL"]      = "1"
    os.environ["FUNSCRIPT_FORGE_MEDIA_PORT"] = str(media_port)
    # G32: tell the UI where to write user data (output/, catalog) — the
    # writable root differs from sys._MEIPASS in a frozen executable.
    os.environ["FUNSCRIPT_FORGE_DATA_DIR"]   = _data_dir()

    # Streamlit config passed directly via flag_options — env vars are not
    # reliably read in a frozen (PyInstaller) context because Streamlit may
    # have already initialised its config singleton before the env vars are set.
    _st_flags: dict = {
        "global.developmentMode": False,
        "server.port": port,
        "server.headless": True,
        "server.enableCORS": False,
        "server.enableXsrfProtection": False,
        "browser.gatherUsageStats": False,
        "theme.base": "dark",
    }

    # Add project root to sys.path so all package imports resolve.
    if base not in sys.path:
        sys.path.insert(0, base)

    # Start the local media file server (serves audio/video by absolute path).
    threading.Thread(target=_start_media_server, args=(media_port,), daemon=True).start()
    print(f"[FunscriptForge] Media server on port {media_port}")

    print(f"[FunscriptForge] Starting on {url}")

    # Open the browser after a short delay so Streamlit has time to start.
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    # Run Streamlit in-process (blocking until the window is closed).
    from streamlit.web import bootstrap  # noqa: PLC0415
    from streamlit.web.bootstrap import load_config_options  # noqa: PLC0415

    # Apply config options BEFORE bootstrap.run — the flag_options dict passed
    # to bootstrap.run only sets up file-change watchers, not the initial config.
    load_config_options(_st_flags)
    bootstrap.run(app_path, False, [], _st_flags)


if __name__ == "__main__":
    main()
