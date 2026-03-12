# Installing FunscriptForge

**FunscriptForge™** is a trademark of Liquid Releasing.

---

## System requirements

| | Minimum | Recommended |
| --- | --- | --- |
| OS | Windows 10 (64-bit), macOS 10.15 Catalina, or Linux (x86-64) | Windows 10/11 · macOS 12+ · Ubuntu 22.04+ |
| RAM | 4 GB | 8 GB or more |
| Display | 1920 × 1080 (some panels require scrolling) | 2560 × 1440 QHD |
| Browser | Any modern browser (Chrome, Edge, Firefox, Safari) | Chrome or Edge |
| Python | Not required — standalone installer | — |

---

## Windows — Quick install

### 1. Download

> **TODO: insert download link / GitHub Releases URL here**

Download **FunscriptForge-windows.zip** from the link above.

### 2. Extract

Right-click the zip → **Extract All…** → choose a destination folder, e.g.:

```text
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

### Uninstall (Windows)

Delete the extracted folder. FunscriptForge writes no files outside that folder and no registry entries.

---

## macOS — Quick install

### 1. Download the macOS build

> **TODO: insert download link / GitHub Releases URL here**

Download **FunscriptForge-macos.zip** from the link above.

### 2. Extract the app

Double-click the zip to expand it. You will get **FunscriptForge.app**.

Drag it to your **Applications** folder (optional but recommended).

### 3. First launch — Gatekeeper approval

Because the app is not signed with an Apple Developer certificate, macOS will block it on first launch.

**Right-click** (or Control-click) **FunscriptForge.app** → **Open** → click **Open** in the dialog.

This is a one-time step per machine. After the first open, you can double-click normally.

> If macOS says the app is "damaged", run this in Terminal to strip the quarantine flag:
>
> ```bash
> xattr -cr /Applications/FunscriptForge.app
> ```

### 4. Launch the app

After the first-launch approval:

- Double-click **FunscriptForge.app**.
- Your default browser opens automatically to the app (usually within 5 seconds).
- The app runs locally — no internet connection is required after install.

### 5. Load a funscript file

Paste or type the full path to a `.funscript` file in the sidebar, or select a recent file.
Click **📂 Open folder** in the sidebar at any time to open the file's folder in Finder.

### Uninstall (macOS)

Drag **FunscriptForge.app** to the Trash.

---

## Linux — Quick install

### 1. Download the Linux build

> **TODO: insert download link / GitHub Releases URL here**

Download **FunscriptForge-linux.tar.gz** from the link above.

### 2. Extract the archive

```bash
tar -xzf FunscriptForge-linux.tar.gz
cd FunscriptForge
```

### 3. Run the app

```bash
./FunscriptForge
```

- Your default browser opens automatically to the app (usually within 5 seconds).
- If the browser does not open, navigate to `http://localhost:6789` manually.
- The app runs locally — no internet connection is required after install.

### 4. Load a funscript file

Paste or type the full path to a `.funscript` file in the sidebar, or select a recent file.

### Uninstall (Linux)

Delete the extracted `FunscriptForge/` folder. No files are written outside it.

### Running in WSL2 (Windows Subsystem for Linux)

FunscriptForge can be tested and run inside WSL2 on Windows 11 with WSLg.

```bash
# In your WSL2 terminal — extract and run exactly as above
tar -xzf FunscriptForge-linux.tar.gz
cd FunscriptForge
./FunscriptForge
```

- On Windows 11 with WSLg, `xdg-open` routes to the Windows browser automatically.
- If the browser does not open, go to `http://localhost:6789` in any Windows browser.
- WSL2 on Windows 10 does not include WSLg — open the URL manually.

> **Note:** For everyday use on Windows, the native Windows build is recommended.
> WSL2 is primarily useful for development and testing the Linux build.

---

## Antivirus / Gatekeeper false positives

PyInstaller-packaged executables are sometimes flagged by security software.
FunscriptForge is open-source — you can inspect the full source code on GitHub.

- **Windows**: add an antivirus exception or submit the file to your vendor as a false positive.
- **macOS**: use the right-click → Open method described above. Run `xattr -cr` if the app is flagged as damaged.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Browser opens but shows "refused to connect" | Wait a few more seconds — click the browser tab to refresh |
| App is slow on first load | Normal — Streamlit compiles templates once on startup |
| Funscript file not loading | Use the full absolute path, e.g. `C:\Videos\myscript.funscript` or `/Users/you/Videos/myscript.funscript` |
| Antivirus blocks the exe (Windows) | See Antivirus section above |
| macOS — "app is damaged" | Run `xattr -cr /Applications/FunscriptForge.app` in Terminal |
| macOS — blocked on first launch | Right-click → Open → Open (one-time Gatekeeper approval) |
| App crashes on startup | Check that you have at least 4 GB RAM free; close other heavy apps |

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).*
