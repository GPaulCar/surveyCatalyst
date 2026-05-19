@echo off
setlocal

set "ROOT=%~dp0.."
set "PY=%ROOT%\.surveyCatalyst_venv\Scripts\python.exe"
set "CTRL=%ROOT%\scripts\system_control.py"

if not exist "%PY%" (
  echo [ERROR] Python runtime not found: "%PY%"
  exit /b 1
)

if not exist "%CTRL%" (
  echo [ERROR] Control script not found: "%CTRL%"
  exit /b 1
)

if "%~1"=="" goto :usage

set "CMD=%~1"
if /I "%CMD%"=="start" goto :run
if /I "%CMD%"=="stop" goto :run
if /I "%CMD%"=="restart" goto :run
if /I "%CMD%"=="status" goto :run
if /I "%CMD%"=="logs" goto :run

goto :usage

:run
"%PY%" "%CTRL%" %CMD%
set "RC=%ERRORLEVEL%"
if /I "%CMD%"=="status" goto :hold
if /I "%CMD%"=="logs" goto :hold
exit /b %RC%

:hold
echo.
echo Press any key to close...
pause >nul
exit /b %RC%

:usage
echo Usage: services.cmd ^<start^|stop^|restart^|status^|logs^>
exit /b 2
