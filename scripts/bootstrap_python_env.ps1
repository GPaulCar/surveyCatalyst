param(
    [string]$VenvPath = ".\.surveyCatalyst_venv"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path ".").Path
$srcPath = (Resolve-Path ".\src").Path
$venvPathResolved = (Resolve-Path $VenvPath).Path

$pythonExe = Join-Path $venvPathResolved "Scripts\python.exe"
$sitePackages = Join-Path $venvPathResolved "Lib\site-packages"
$pthFile = Join-Path $sitePackages "surveyCatalyst_src.pth"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe"
}
if (-not (Test-Path $sitePackages)) {
    throw "site-packages not found at $sitePackages"
}

Set-Content -Path $pthFile -Value $srcPath -Encoding ascii

& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $repoRoot "requirements.txt")

Write-Host ""
Write-Host "Wrote .pth file to: $pthFile"
Write-Host "src path registered: $srcPath"
Write-Host ""
Write-Host "Verification command:"
Write-Host ('& "{0}" -c "from orchestration.pipeline_orchestrator import PipelineOrchestrator as P; print(P)"' -f $pythonExe)
