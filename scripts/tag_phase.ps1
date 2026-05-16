param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("code","assess","validate")]
  [string]$Phase,

  [Parameter(Mandatory=$false)]
  [string]$PreviousTag = "",

  [Parameter(Mandatory=$false)]
  [string]$Number = "1",

  [Parameter(Mandatory=$false)]
  [string]$Host = "",

  [Parameter(Mandatory=$false)]
  [string]$Timestamp = "",

  [Parameter(Mandatory=$false)]
  [string]$Message = ""
)

$ErrorActionPreference = "Stop"

function Run-Git([string[]]$Args) {
  & git @Args
  if ($LASTEXITCODE -ne 0) {
    throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
  }
}

function Get-GitOutput([string[]]$Args) {
  $out = & git @Args
  if ($LASTEXITCODE -ne 0) {
    throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
  }
  return ($out -join "`n").Trim()
}

function Ensure-CleanTree {
  $status = Get-GitOutput @("status","--porcelain")
  if ($status) {
    throw "Working tree is not clean. Commit/stash changes before tagging."
  }
}

function Ensure-TagExists([string]$TagName) {
  $match = Get-GitOutput @("tag","-l",$TagName)
  if (-not $match) {
    throw "Tag not found: $TagName"
  }
}

function Ensure-TagNotExists([string]$TagName) {
  $match = Get-GitOutput @("tag","-l",$TagName)
  if ($match) {
    throw "Tag already exists: $TagName"
  }
}

if (-not $Host) {
  $Host = $env:COMPUTERNAME.ToLower()
}
if (-not $Timestamp) {
  $Timestamp = Get-Date -Format "yyyyMMdd-HHmm"
}

Ensure-CleanTree

$today = Get-Date -Format "yyyyMMdd"
$tagName = ""
$tagMessage = ""

switch ($Phase) {
  "code" {
    if (-not $PreviousTag) {
      throw "Phase=code requires -PreviousTag"
    }
    Ensure-TagExists $PreviousTag
    $tagName = "sc-refine-$today.$Number"
    Ensure-TagNotExists $tagName
    if (-not $Message) {
      $Message = "Refinement from $PreviousTag"
    }
    $tagMessage = $Message
  }
  "assess" {
    $tagName = "sc-assess-$Host-$Timestamp"
    Ensure-TagNotExists $tagName
    if (-not $Message) {
      $Message = "Assessment results for $Host at $Timestamp"
    }
    $tagMessage = $Message
  }
  "validate" {
    $tagName = "sc-validate-$Host-$Timestamp"
    Ensure-TagNotExists $tagName
    if (-not $Message) {
      $Message = "Validation results for $Host at $Timestamp"
    }
    $tagMessage = $Message
  }
}

Run-Git @("tag","-a",$tagName,"-m",$tagMessage)
Write-Host "[OK] Created tag: $tagName"
Write-Host "[OK] Message: $tagMessage"
Write-Host ""
Write-Host "Push it with:"
Write-Host "  git push origin $tagName"
