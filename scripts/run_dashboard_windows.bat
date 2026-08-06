@echo off
REM Usage: scripts\run_dashboard_windows.bat COM11
setlocal
set PORT=%~1
if "%PORT%"=="" set PORT=COM11
set BAUD=115200

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher ^(py^) was not found.
  echo Install Python 3.10+ from python.org, then run:
  echo   py -m pip install -r requirements.txt
  exit /b 1
)

py -3 pc\bno085_rvc_dashboard.py --port %PORT% --baud %BAUD%
