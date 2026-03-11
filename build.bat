@echo off
REM Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
REM Build script for Funscript Forge packaged executable.
REM
REM Usage:
REM   build.bat            — clean build into dist\FunscriptForge\
REM   build.bat --no-clean — skip cleaning dist\ and build\ first

setlocal

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo ==========================================================
echo  Funscript Forge — Windows Package Build
echo ==========================================================
echo.

REM -------------------------------------------------------
REM Check Python
REM -------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH.  Install Python 3.10+ and try again.
    exit /b 1
)

REM -------------------------------------------------------
REM Install / upgrade build dependencies
REM -------------------------------------------------------
echo [1/4] Installing build dependencies...
pip install --quiet --upgrade pyinstaller
pip install --quiet -r requirements.txt
pip install --quiet -r ui\streamlit\requirements.txt
echo       Done.
echo.

REM -------------------------------------------------------
REM Clean previous build artifacts
REM -------------------------------------------------------
if /i not "%1"=="--no-clean" (
    echo [2/4] Cleaning dist\ and build\...
    if exist dist\FunscriptForge  rmdir /s /q dist\FunscriptForge
    if exist build\FunscriptForge rmdir /s /q build\FunscriptForge
    echo       Done.
    echo.
) else (
    echo [2/4] Skipping clean (--no-clean).
    echo.
)

REM -------------------------------------------------------
REM Run PyInstaller
REM -------------------------------------------------------
echo [3/4] Running PyInstaller...
pyinstaller funscript_forge.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed.  See output above.
    exit /b 1
)
echo       Done.
echo.

REM -------------------------------------------------------
REM Verify output
REM -------------------------------------------------------
echo [4/4] Verifying output...
if exist dist\FunscriptForge\FunscriptForge.exe (
    echo       SUCCESS — dist\FunscriptForge\FunscriptForge.exe created.
    echo.
    echo  To run:  dist\FunscriptForge\FunscriptForge.exe
    echo  To share: zip the entire dist\FunscriptForge\ folder.
) else (
    echo [ERROR] Expected exe not found at dist\FunscriptForge\FunscriptForge.exe
    exit /b 1
)

echo.
echo ==========================================================
echo  Build complete.
echo ==========================================================

endlocal
