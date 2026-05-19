@echo off
setlocal EnableDelayedExpansion

set "ROOT=%~dp0.."
set "PY=%ROOT%\.surveyCatalyst_venv\Scripts\python.exe"
set "ENV_PY=%ROOT%\scripts\envelope.py"

if not exist "%ROOT%\.git" (
  echo [ERROR] Not a git repository: "%ROOT%"
  exit /b 1
)

for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToUniversalTime().ToString(\"yyyyMMdd-HHmmss\")"') do set "STAMP=%%i"
set "TAG=stable-%STAMP%"

pushd "%ROOT%" >nul

git add -A
git diff --cached --quiet
if not errorlevel 1 (
  git commit -m "chore: checkpoint before stable tag %TAG%"
  if errorlevel 1 (
    echo [ERROR] Commit failed.
    popd >nul
    exit /b 1
  )
)

git tag %TAG%
if errorlevel 1 (
  echo [ERROR] Tag creation failed.
  popd >nul
  exit /b 1
)

git push origin main
if errorlevel 1 (
  echo [ERROR] Push main failed.
  popd >nul
  exit /b 1
)

git push origin %TAG%
if errorlevel 1 (
  echo [ERROR] Push tag failed.
  popd >nul
  exit /b 1
)

set "LATEST_REPORT="
for /f "delims=" %%f in ('powershell -NoProfile -Command "$f=Get-ChildItem -Path \"%ROOT%\assessment\output\ops_cycle_*.json\" -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1; if($f){$f.FullName}"') do set "LATEST_REPORT=%%f"

if exist "%PY%" if exist "%ENV_PY%" (
  if defined LATEST_REPORT (
    "%PY%" "%ENV_PY%" set "stable tag %TAG% created; latest ops report: %LATEST_REPORT%" --author release-bot >nul
  ) else (
    "%PY%" "%ENV_PY%" set "stable tag %TAG% created; no ops_cycle report found" --author release-bot >nul
  )
)

echo [DONE] Created and pushed stable tag: %TAG%
if defined LATEST_REPORT echo [INFO] Latest ops report: %LATEST_REPORT%

popd >nul
exit /b 0

