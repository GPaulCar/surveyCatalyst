param(
    [ValidateSet("bootstrap", "update")]
    [string]$Mode = "bootstrap",
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,
    [string]$Branch = "main",
    [string]$InstallRoot = "C:\surveyCatalyst",
    [string]$RepoDirName = "surveyCatalyst",
    [string]$PythonVersion = "3.11"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-GitIfMissing {
    if (Require-Command "git") {
        Write-Host "Git already available."
        return
    }
    if (-not (Require-Command "winget")) {
        throw "Git is missing and winget is not available. Install Git manually, then rerun."
    }
    Write-Step "Installing Git"
    & winget install --id Git.Git --exact --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget failed while installing Git."
    }
    if (-not (Require-Command "git")) {
        throw "Git installation completed but git is not on PATH in this session. Open a new shell and rerun."
    }
}

function Install-PythonIfMissing {
    if (Require-Command "py") {
        Write-Host "Python launcher already available."
        return
    }
    if (-not (Require-Command "winget")) {
        throw "Python is missing and winget is not available. Install Python manually, then rerun."
    }
    Write-Step "Installing Python $PythonVersion"
    $wingetId = if ($PythonVersion -eq "3.11") { "Python.Python.3.11" } else { "Python.Python.3" }
    & winget install --id $wingetId --exact --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget failed while installing Python."
    }
    if (-not (Require-Command "py")) {
        throw "Python installation completed but py launcher is not on PATH in this session. Open a new shell and rerun."
    }
}

function Ensure-Repo {
    param(
        [string]$RepoPath
    )
    if (-not (Test-Path $InstallRoot)) {
        New-Item -ItemType Directory -Path $InstallRoot | Out-Null
    }
    if (-not (Test-Path $RepoPath)) {
        Write-Step "Cloning repository"
        & git clone --branch $Branch --single-branch $RepoUrl $RepoPath
        if ($LASTEXITCODE -ne 0) {
            throw "git clone failed."
        }
    } else {
        Write-Host "Repository already present at $RepoPath"
    }
}

function Set-ReadonlyRemote {
    param([string]$RepoPath)
    Write-Step "Configuring pull-only Git remote"
    & git -C $RepoPath remote set-url origin $RepoUrl
    & git -C $RepoPath remote set-url --push origin DISABLED
    & git -C $RepoPath config advice.pushUpdateRejected true
}

function Sync-Repo {
    param([string]$RepoPath)
    Write-Step "Updating repository"
    & git -C $RepoPath fetch origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed." }
    & git -C $RepoPath checkout $Branch
    if ($LASTEXITCODE -ne 0) { throw "git checkout failed." }
    & git -C $RepoPath reset --hard ("origin/" + $Branch)
    if ($LASTEXITCODE -ne 0) { throw "git reset --hard failed." }
}

function Ensure-VenvAndDeps {
    param([string]$RepoPath)

    $venvPath = Join-Path $RepoPath ".surveyCatalyst_venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"

    if (-not (Test-Path $venvPython)) {
        Write-Step "Creating virtual environment"
        & py "-$PythonVersion" -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            & py -3 -m venv $venvPath
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create virtual environment."
            }
        }
    } else {
        Write-Host "Virtual environment already present."
    }

    Write-Step "Installing Python dependencies"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $RepoPath "scripts\bootstrap_python_env.ps1") -VenvPath $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency bootstrap failed."
    }

    Write-Step "Verifying environment"
    & $venvPython (Join-Path $RepoPath "scripts\verify_python_env.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Environment verification failed."
    }
}

$repoPath = Join-Path $InstallRoot $RepoDirName

Write-Step "Preparing prerequisites"
Install-GitIfMissing
Install-PythonIfMissing

if ($Mode -eq "bootstrap") {
    Ensure-Repo -RepoPath $repoPath
    Set-ReadonlyRemote -RepoPath $repoPath
    Ensure-VenvAndDeps -RepoPath $repoPath
} else {
    if (-not (Test-Path $repoPath)) {
        throw "Repository not found at $repoPath. Run bootstrap mode first."
    }
    Set-ReadonlyRemote -RepoPath $repoPath
    Sync-Repo -RepoPath $repoPath
    Ensure-VenvAndDeps -RepoPath $repoPath
}

Write-Host ""
Write-Host "Completed: $Mode" -ForegroundColor Green
Write-Host "Repo: $repoPath"
Write-Host "Run API stack with:"
Write-Host ("  {0} {1}" -f (Join-Path $repoPath ".surveyCatalyst_venv\Scripts\python.exe"), (Join-Path $repoPath "scripts\system_control.py restart"))
Write-Host ""
Write-Host "Update later with:"
Write-Host ("  .\scripts\deploy_readonly_instance.ps1 -Mode update -RepoUrl `"{0}`" -Branch {1} -InstallRoot `"{2}`" -RepoDirName `"{3}`"" -f $RepoUrl, $Branch, $InstallRoot, $RepoDirName)
