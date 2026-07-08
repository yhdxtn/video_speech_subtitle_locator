@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo ========================================
echo Video Speech Subtitle Locator - Install
echo ========================================
echo.

where py > nul 2> nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

%PY% --version
if errorlevel 1 (
    echo [ERROR] Python was not found. Install Python 3.10+ and enable the py launcher.
    pause
    exit /b 1
)

if not exist .venv (
    echo [1/4] Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 goto :fail
)

echo [2/4] Installing Python dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :fail

where npm.cmd > nul 2> nul
if errorlevel 1 (
    echo [ERROR] npm.cmd was not found. Install Node.js 20+ first.
    pause
    exit /b 1
)

echo [3/4] Installing open-source Whisper JS dependencies...
npm.cmd install
if errorlevel 1 goto :fail

echo [4/4] Done.
echo.
echo Start the app with run.bat.
echo The first recognition run downloads the selected open-source Whisper ONNX model.
pause
exit /b 0

:fail
echo.
echo [ERROR] Installation failed. Please copy the full console output.
pause
exit /b 1
