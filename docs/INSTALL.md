# Installing FunscriptForge

**FunscriptForge™** is a trademark of Liquid Releasing.

---

## System requirements

| | Minimum | Recommended |
| --- | --- | --- |
| OS | Windows 10 (64-bit) | Windows 10/11 (64-bit) |
| RAM | 4 GB | 8 GB or more |
| Display | 1920 × 1080 (some panels require scrolling) | 2560 × 1440 QHD |
| Browser | Any modern browser (Chrome, Edge, Firefox) | Chrome or Edge |
| Python | Not required — standalone installer | — |

> **macOS support** — a macOS build is planned. See [BUILD.md](../internal/BUILD.md) for developer build instructions.

---

## Windows — Quick install

### 1. Download

> **TODO: insert download link / GitHub Releases URL here**

Download **FunscriptForge-windows.zip** from the link above.

### 2. Extract

Right-click the zip → **Extract All…** → choose a destination folder, e.g.:

```
C:\Program Files\FunscriptForge\
```

or your Documents / Desktop — anywhere you have write access.

### 3. Run

Double-click **FunscriptForge.exe** inside the extracted folder.

- A terminal window may flash briefly while the app starts.
- Your default browser opens automatically to the app (usually within 5 seconds).
- The app runs locally — no internet connection is required after install.

### 4. Load a funscript

Paste or type the full path to a `.funscript` file in the sidebar, or select a recent file.
Click **📂 Open folder** in the sidebar at any time to open the file's folder in Explorer.

---

## Uninstall

Delete the extracted folder. FunscriptForge writes no files outside that folder and no registry entries.

---

## Antivirus false positives

PyInstaller-packaged executables are sometimes flagged by antivirus software as suspicious.
FunscriptForge is open-source — you can inspect the full source code on GitHub.

If your antivirus flags the exe, add an exception or submit the file to your vendor as a false positive.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Browser opens but shows "refused to connect" | Wait a few more seconds — click the browser tab to refresh |
| App is slow on first load | Normal — Streamlit compiles templates once on startup |
| Funscript file not loading | Use the full absolute path, e.g. `C:\Videos\myscript.funscript` |
| Antivirus blocks the exe | See [Antivirus false positives](#antivirus-false-positives) above |
| App crashes on startup | Check that you have at least 4 GB RAM free; close other heavy apps |

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).*
