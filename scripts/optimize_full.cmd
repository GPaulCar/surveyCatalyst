@echo off
setlocal

set "ROOT=%~dp0.."
set "PY=%ROOT%\.surveyCatalyst_venv\Scripts\python.exe"
set "RUNNER=%ROOT%\scripts\optimize_db_full_cycle.py"

if not exist "%PY%" (
  echo [ERROR] Python runtime not found: "%PY%"
  exit /b 1
)

if not exist "%RUNNER%" (
  echo [ERROR] Optimization runner not found: "%RUNNER%"
  exit /b 1
)

"%PY%" "%RUNNER%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [DONE] Full optimization cycle completed.
) else (
  echo [FAIL] Full optimization cycle failed with exit code %RC%.
)
echo Press any key to close...
pause >nul
exit /b %RC%

