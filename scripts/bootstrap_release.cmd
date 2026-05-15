@echo off
setlocal

set "ROOT=%~dp0.."
pushd "%ROOT%" >nul

set "PY_INSTALLER=%ROOT%\downloads\python-3.13.13-amd64.exe"
set "PY_DIR=%ROOT%\tools\python"
set "PY_EXE=%PY_DIR%\python.exe"
set "VENV_EXE=%ROOT%\.surveyCatalyst_venv\Scripts\python.exe"
set "FALLBACK_PY_EXE="

if not exist "%PY_INSTALLER%" (
  echo [ERROR] Missing bundled Python installer: "%PY_INSTALLER%"
  popd >nul
  exit /b 1
)

if not exist "%PY_EXE%" (
  echo [INFO] Installing bundled Python runtime...
  start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0 Include_pip=1 TargetDir="%PY_DIR%"
)

if not exist "%PY_EXE%" (
  for /f "delims=" %%I in ('dir /b /s "%LocalAppData%\Programs\Python\Python3*\python.exe" 2^>nul') do (
    set "FALLBACK_PY_EXE=%%I"
    goto :found_fallback_python
  )
  echo [ERROR] Bundled Python runtime was not created at "%PY_EXE%"
  echo [ERROR] No fallback Python runtime detected under "%%LocalAppData%%\Programs\Python".
  popd >nul
  exit /b 1
)

goto :python_ready

:found_fallback_python
echo [WARN] Bundled Python path was not created. Using existing local Python:
echo        "%FALLBACK_PY_EXE%"
set "PY_EXE=%FALLBACK_PY_EXE%"

:python_ready
if not exist "%VENV_EXE%" (
  echo [INFO] Creating local virtual environment...
  "%PY_EXE%" -m venv "%ROOT%\.surveyCatalyst_venv"
)

if not exist "%VENV_EXE%" (
  echo [ERROR] Virtual environment was not created at "%VENV_EXE%"
  popd >nul
  exit /b 1
)

echo [INFO] Bootstrapping Python dependencies...
"%VENV_EXE%" "%ROOT%\scripts\bootstrap_python_env.py"
if errorlevel 1 (
  echo [ERROR] bootstrap_python_env.py failed
  popd >nul
  exit /b 1
)

echo [INFO] Running release installer...
"%VENV_EXE%" "%ROOT%\scripts\install_release.py"
if errorlevel 1 (
  echo [ERROR] install_release.py failed
  popd >nul
  exit /b 1
)

echo [DONE] Release runtime installed.
echo Next: "%VENV_EXE%" "%ROOT%\scripts\system_control.py" start

popd >nul
exit /b 0
