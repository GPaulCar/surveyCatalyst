@echo off
setlocal

set "ROOT=%~dp0.."
set "PY=%ROOT%\.surveyCatalyst_venv\Scripts\python.exe"
set "RUNNER=%ROOT%\scripts\update_and_apply.py"

if not exist "%PY%" (
  echo [ERROR] Python runtime not found: "%PY%"
  exit /b 1
)
if not exist "%RUNNER%" (
  echo [ERROR] Runner not found: "%RUNNER%"
  exit /b 1
)

if /I "%~1"=="tag" (
  if "%~2"=="" (
    echo Usage: update_and_apply.cmd tag ^<tag-name^>
    exit /b 2
  )
  "%PY%" "%RUNNER%" --tag "%~2"
) else (
  "%PY%" "%RUNNER%"
)

set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [DONE] update_and_apply completed.
) else (
  echo [FAIL] update_and_apply failed with exit code %RC%.
)
echo Press any key to close...
pause >nul
exit /b %RC%

