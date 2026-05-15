@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE="

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PYTHON_EXE=py -3"
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PYTHON_EXE=python"
  )
)

if "%PYTHON_EXE%"=="" (
  echo [ERROR] Python 3 was not found in PATH.
  echo Install Python 3, then run:
  echo   python "%SCRIPT_DIR%bootstrap_portable.py" --auto-handoff
  exit /b 1
)

%PYTHON_EXE% "%SCRIPT_DIR%bootstrap_portable.py" --auto-handoff %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo [FAIL] bootstrap failed with exit code %EXIT_CODE%.
  echo Manual handoff:
  echo   python "%SCRIPT_DIR%bootstrap_portable.py"
)
exit /b %EXIT_CODE%
