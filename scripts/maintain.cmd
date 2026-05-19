@echo off
setlocal

set "ROOT=%~dp0.."
set "OPT=%ROOT%\scripts\optimize_full.cmd"
set "SVC=%ROOT%\scripts\services.cmd"

if not exist "%OPT%" (
  echo [ERROR] Missing optimizer launcher: "%OPT%"
  exit /b 1
)

if not exist "%SVC%" (
  echo [ERROR] Missing services launcher: "%SVC%"
  exit /b 1
)

call "%OPT%"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [FAIL] optimize_full.cmd failed with exit code %RC%.
  echo Press any key to close...
  pause >nul
  exit /b %RC%
)

call "%SVC%" restart
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [FAIL] services restart failed with exit code %RC%.
  echo Press any key to close...
  pause >nul
  exit /b %RC%
)

call "%SVC%" status
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo [WARN] services status returned exit code %RC%.
)

echo.
echo [DONE] Maintenance cycle completed.
echo Press any key to close...
pause >nul
exit /b 0

