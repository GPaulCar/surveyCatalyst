@echo off
setlocal

set "ROOT=%~dp0.."
set "PY=%ROOT%\.surveyCatalyst_venv\Scripts\python.exe"
set "RUNNER=%ROOT%\scripts\migrate_external_features_partitioned.py"

if not exist "%PY%" (
  echo [ERROR] Python runtime not found: "%PY%"
  exit /b 1
)
if not exist "%RUNNER%" (
  echo [ERROR] Runner not found: "%RUNNER%"
  exit /b 1
)

if /I "%~1"=="apply" (
  "%PY%" "%RUNNER%" --apply
) else (
  "%PY%" "%RUNNER%"
)

set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [DONE] external_features partition migration command completed.
) else (
  echo [FAIL] partition migration command failed with exit code %RC%.
)
echo Press any key to close...
pause >nul
exit /b %RC%

