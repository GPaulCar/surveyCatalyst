param(
  [string]$Root = "C:\Users\klenk\desktop\surveyCatalyst",
  [string]$RepoUrl = "https://github.com/GPaulCar/surveyCatalyst.git",
  [string]$Tag = "sc-refine-20260516.1",
  [switch]$RemoveRepoFolder
)

$ErrorActionPreference = "Stop"

function Run-Checked($File, $Args) {
  & $File @Args
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $File $($Args -join ' ')"
  }
}

Write-Host "[INFO] Root: $Root"
Write-Host "[INFO] Tag:  $Tag"

$repoFolder = "${Root}_repo"
$venvPy = Join-Path $Root ".surveyCatalyst_venv\Scripts\python.exe"

if (Test-Path $venvPy) {
  Write-Host "[INFO] Stopping runtime (if running)"
  & $venvPy (Join-Path $Root "scripts\system_control.py") stop | Out-Null
}

if (!(Test-Path $Root)) {
  New-Item -ItemType Directory -Path $Root | Out-Null
}

Set-Location $Root

if (!(Test-Path (Join-Path $Root ".git"))) {
  Write-Host "[INFO] Initializing git repo in root"
  Run-Checked git @("init")
}

Write-Host "[INFO] Configuring origin"
& git remote remove origin 2>$null
Run-Checked git @("remote", "add", "origin", $RepoUrl)

Write-Host "[INFO] Fetching tags"
Run-Checked git @("fetch", "--tags", "origin")

Write-Host "[INFO] Checking out tag"
Run-Checked git @("checkout", "--detach", "tags/$Tag")
Run-Checked git @("reset", "--hard", "tags/$Tag")
Run-Checked git @("clean", "-fd")

if ($RemoveRepoFolder -and (Test-Path $repoFolder)) {
  Write-Host "[INFO] Removing duplicate folder: $repoFolder"
  Remove-Item -Recurse -Force $repoFolder
}

Write-Host "[DONE] Single-root normalization complete."
Write-Host "[INFO] Repo top-level:"
Run-Checked git @("rev-parse", "--show-toplevel")
