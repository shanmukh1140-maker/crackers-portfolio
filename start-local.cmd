@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%LOCALAPPDATA%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PYTHON%" goto launch
where py.exe >nul 2>nul
if not errorlevel 1 (
  set "PYTHON=py.exe"
  set "PYTHON_ARGS=-3"
  goto launch
)
where python.exe >nul 2>nul
if not errorlevel 1 (
  set "PYTHON=python.exe"
  goto launch
)
echo Python 3.10 or newer is required. Install Python, then double-click this file again.
pause
exit /b 1
:launch
"%PYTHON%" %PYTHON_ARGS% start_local.py
if errorlevel 1 pause
