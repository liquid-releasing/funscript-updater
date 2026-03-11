# Building FunscriptForge

This document covers how to build a standalone packaged application on Windows
and macOS. The result is a self-contained executable that end users can run
without installing Python.

---

## Prerequisites (both platforms)

| Requirement | Version | Notes |
| --- | --- | --- |
| Python | 3.10 – 3.12 | 3.11 recommended |
| pip | latest | `pip install --upgrade pip` |
| Git | any | to clone the repo |

Clone the repository and enter it:

```bash
git clone https://github.com/liquid-releasing/funscript-forge.git
cd funscript-forge
```

---

## Windows

### Quick build

```bat
build.bat
```

The script will:

1. Install / upgrade `pyinstaller` and all project dependencies
2. Clean any previous `dist\FunscriptForge\` and `build\FunscriptForge\` folders
3. Run PyInstaller using `funscript_forge.spec`
4. Report the path to the finished executable

**Output:** `dist\FunscriptForge\FunscriptForge.exe`

### Skip the clean step

```bat
build.bat --no-clean
```

Useful when iterating to avoid a full rebuild.

### Distribute

Zip the entire `dist\FunscriptForge\` folder and share it. Users double-click
`FunscriptForge.exe` — no Python or pip required.

### App icon

The build uses `media/funscriptforge.ico` (a multi-resolution `.ico` already
checked in to the repository). No extra steps needed.

### Manual PyInstaller command

If you prefer to run PyInstaller directly:

```bat
pip install --upgrade pyinstaller
pip install -r requirements.txt
pip install -r ui\streamlit\requirements.txt
pyinstaller funscript_forge.spec --noconfirm
```

---

## macOS

### Quick build

```bash
chmod +x build.sh
./build.sh
```

The script will:

1. Install / upgrade `pyinstaller` and all project dependencies
2. Generate `media/funscriptforge.icns` automatically (using the built-in
   `sips` and `iconutil` tools — no extra software needed)
3. Clean any previous `dist/FunscriptForge.app` and `dist/FunscriptForge/`
4. Run PyInstaller using `funscript_forge.spec`
5. Report the path to the finished `.app` bundle

**Output:** `dist/FunscriptForge.app`

### Skip the clean step

```bash
./build.sh --no-clean
```

### Create a DMG for distribution

```bash
./build.sh --dmg
```

This adds a step after the build that calls `hdiutil` to produce
`dist/FunscriptForge.dmg` — a standard macOS disk image that users can
double-click to open, drag the app to their Applications folder, and eject.

You can combine flags:

```bash
./build.sh --no-clean --dmg
```

### App icon

On the first run, `build.sh` generates `media/funscriptforge.icns` from
`media/anvil.png` using macOS's built-in `sips` and `iconutil`. The `.icns`
file is **not** checked in to the repository because it can only be created on
macOS — it is regenerated automatically by both `build.sh` and the GitHub
Actions workflow.

### Manual PyInstaller command

```bash
pip3 install --upgrade pyinstaller
pip3 install -r requirements.txt
pip3 install -r ui/streamlit/requirements.txt
pyinstaller funscript_forge.spec --noconfirm
```

### Running the built app

```bash
open dist/FunscriptForge.app
```

Or double-click it in Finder.

> **Gatekeeper note** — because the app is not code-signed with an Apple
> Developer certificate, macOS will block it on first launch. Right-click
> (or Control-click) the app, choose **Open**, then confirm. This is a
> one-time step per machine.

---

## GitHub Actions — automated release builds

The workflow at [`.github/workflows/release.yml`](.github/workflows/release.yml)
builds both platforms automatically and publishes a GitHub Release.

### Trigger a release

Push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow will:

1. Build on `windows-latest` — produces `FunscriptForge-windows.zip`
2. Build on `macos-latest` — produces `FunscriptForge-macos.zip`
3. Create a GitHub Release with both zips attached and auto-generated release notes

### Artifacts without a release tag

Each build job also uploads its zip as a workflow artifact (visible under the
**Actions** tab in GitHub), so you can download test builds from any branch
without creating a tag.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `pyinstaller: command not found` | Run `pip install pyinstaller` and ensure `~/.local/bin` (Linux/Mac) or `%APPDATA%\Python\Scripts` (Windows) is on `PATH` |
| Missing module at runtime | Add it to `hiddenimports` in `funscript_forge.spec` |
| Streamlit can't find its static files | `collect_data_files("streamlit")` in the spec handles this; re-run a clean build |
| macOS — "app is damaged" | Run `xattr -cr dist/FunscriptForge.app` to strip quarantine flag |
| macOS — `.icns` not generated | Ensure you are running on macOS (not Windows/Linux); `sips` and `iconutil` are macOS-only |
| Windows — antivirus flags the exe | Common false positive with PyInstaller; submit the file to your AV vendor as a false positive |

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](LICENSE).*
