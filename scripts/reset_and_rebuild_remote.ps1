param(
  [string]$Root = "C:\Users\klenk\Desktop\surveyCatalyst",
  [string]$RepoUrl = "https://github.com/GPaulCar/surveyCatalyst.git",
  [string]$Tag = "sc-refine-20260516.1"
)

$ErrorActionPreference = "Stop"

function Run-Step([string]$Cmd, [string[]]$Args) {
  & $Cmd @Args
  if ($LASTEXITCODE -ne 0) {
    throw "Failed: $Cmd $($Args -join ' ')"
  }
}

$RepoSibling = "${Root}_repo"

if (Test-Path "$Root\.surveyCatalyst_venv\Scripts\python.exe") {
  & "$Root\.surveyCatalyst_venv\Scripts\python.exe" "$Root\scripts\system_control.py" stop | Out-Null
}

Remove-Item -Recurse -Force $Root -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $RepoSibling -ErrorAction SilentlyContinue

Run-Step git @("clone", $RepoUrl, $Root)
Set-Location $Root
Run-Step git @("fetch", "--tags", "origin")
Run-Step git @("checkout", "--detach", "tags/$Tag")
Run-Step git @("reset", "--hard", "tags/$Tag")
Run-Step git @("clean", "-fdx")

Run-Step python @("assessment\scripts\run_assessment_block.py", "--dotenv", "assessment\.env.example")
Run-Step python @("assessment\scripts\apply_approved_fixes.py", "--dry-run")
Run-Step python @("assessment\scripts\validate_and_monitor.py")

Run-Step git @("add", "assessment")
& git commit -m "assessment: $env:COMPUTERNAME clean baseline"
if ($LASTEXITCODE -ne 0) {
  Write-Host "[WARN] Nothing to commit for assessment artifacts."
}
Run-Step git @("push", "origin", "HEAD:main")

Write-Host "[DONE] Single-root rebuild complete at $Root"
