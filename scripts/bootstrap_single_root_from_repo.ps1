param(
  [string]$SourceRepo = "C:\Users\klenk\desktop\surveyCatalyst_repo",
  [string]$DestRoot = "C:\Users\klenk\desktop\surveyCatalyst",
  [string]$Tag = "sc-refine-20260516.1",
  [switch]$RemoveSourceRepo
)

$ErrorActionPreference = "Stop"

function Run-Checked($File, $Args) {
  & $File @Args
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $File $($Args -join ' ')"
  }
}

Write-Host "[INFO] Source repo: $SourceRepo"
Write-Host "[INFO] Dest root:   $DestRoot"
Write-Host "[INFO] Tag:         $Tag"

if (!(Test-Path $SourceRepo)) {
  throw "Source repo not found: $SourceRepo"
}

if (!(Test-Path (Join-Path $SourceRepo ".git"))) {
  throw "Source path is not a git repo: $SourceRepo"
}

New-Item -ItemType Directory -Force -Path $DestRoot | Out-Null

Write-Host "[INFO] Copying source repo into destination..."
Run-Checked robocopy @($SourceRepo, $DestRoot, "/E", "/COPY:DAT", "/R:1", "/W:1")

Set-Location $DestRoot

Write-Host "[INFO] Verifying destination git repo..."
Run-Checked git @("rev-parse", "--show-toplevel")
Run-Checked git @("remote", "-v")

Write-Host "[INFO] Syncing destination to tag..."
Run-Checked git @("fetch", "--tags", "origin")
Run-Checked git @("checkout", "--detach", "tags/$Tag")
Run-Checked git @("reset", "--hard", "tags/$Tag")
Run-Checked git @("clean", "-fd")

if ($RemoveSourceRepo -and (Test-Path $SourceRepo)) {
  Write-Host "[INFO] Removing source repo folder..."
  Remove-Item -Recurse -Force $SourceRepo
}

Write-Host "[DONE] Single-root bootstrap complete."
Write-Host "[INFO] Use only: $DestRoot"
