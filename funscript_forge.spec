# -*- mode: python ; coding: utf-8 -*-
# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# PyInstaller spec for Funscript Forge — cross-platform package.
#
# Build with:
#   pyinstaller funscript_forge.spec
# Or use build.bat (Windows) / build.sh (macOS) for a clean build.

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

_IS_MAC = sys.platform == "darwin"

# ---------------------------------------------------------------------------
# Data files — source code packages and assets bundled into _MEIPASS
# ---------------------------------------------------------------------------

datas = []

# Project source packages (needed at runtime by Streamlit's app.py)
_src_packages = [
    "assessment",
    "pattern_catalog",
    "user_customization",
    "catalog",
    "visualizations",
    "ui",
    "tests",
    "user_transforms",
    "plugins",
    "media",
]
for pkg in _src_packages:
    if os.path.isdir(pkg):
        datas.append((pkg, pkg))

# Top-level Python modules
for mod in ["models.py", "utils.py", "cli.py"]:
    if os.path.isfile(mod):
        datas.append((mod, "."))

# Streamlit's own static web assets (HTML, JS, CSS)
datas += collect_data_files("streamlit")

# Plotly static assets
datas += collect_data_files("plotly")

# Altair / Vega data (Streamlit uses altair internally)
try:
    datas += collect_data_files("altair")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Hidden imports — packages that PyInstaller cannot auto-detect
# ---------------------------------------------------------------------------

hiddenimports = []

# Streamlit internals
hiddenimports += collect_submodules("streamlit")

# Pandas / NumPy / Matplotlib
hiddenimports += [
    "pandas",
    "pandas._libs",
    "pandas._libs.tslibs.np_datetime",
    "pandas._libs.tslibs.nattype",
    "numpy",
    "numpy.core._methods",
    "numpy.lib.format",
    "matplotlib",
    "matplotlib.backends.backend_agg",
]

# Plotly
hiddenimports += collect_submodules("plotly")

# Project packages
hiddenimports += [
    "assessment",
    "assessment.analyzer",
    "assessment.classifier",
    "pattern_catalog",
    "pattern_catalog.transformer",
    "pattern_catalog.phrase_transforms",
    "pattern_catalog.config",
    "user_customization",
    "user_customization.customizer",
    "user_customization.config",
    "catalog.pattern_catalog",
    "ui.common.project",
    "ui.common.pipeline",
    "ui.common.work_items",
    "ui.streamlit.app",
]

# ---------------------------------------------------------------------------
# Build configuration
# ---------------------------------------------------------------------------

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused packages
        "tkinter",
        "scipy",
        "sklearn",
        "tensorflow",
        "torch",
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific icon
if _IS_MAC:
    _icon = "media/funscriptforge.icns" if os.path.isfile("media/funscriptforge.icns") else None
else:
    _icon = "media/funscriptforge.ico" if os.path.isfile("media/funscriptforge.ico") else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FunscriptForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No console window for end users
    disable_windowed_traceback=False,
    argv_emulation=False,   # Only meaningful on macOS; set via BUNDLE below
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FunscriptForge",
)

# macOS .app bundle
if _IS_MAC:
    app = BUNDLE(
        coll,
        name="FunscriptForge.app",
        icon=_icon,
        bundle_identifier="com.liquidreleasing.funscriptforge",
        info_plist={
            "NSPrincipalClass": "NSApplication",
            "NSAppleScriptEnabled": False,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "LSMinimumSystemVersion": "10.15",
            "NSHighResolutionCapable": True,
        },
    )
