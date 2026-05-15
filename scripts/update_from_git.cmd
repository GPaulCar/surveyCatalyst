@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "PYEXE="

if exist "%SCRIPT_DIR%..\.surveyCatalyst_venv\Scripts\python.exe" (
  set "PYEXE=%SCRIPT_DIR%..\.surveyCatalyst_venv\Scripts\python.exe"
)
if not defined PYEXE (
  where py >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PYEXE=py -3"
  ) else (
    set "PYEXE=python"
  )
)

%PYEXE% "%SCRIPT_DIR%update_from_git.py" %*
exit /b %ERRORLEVEL%
