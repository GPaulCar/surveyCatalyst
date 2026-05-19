param(
    [string]$TransferRoot = "D:\SURVEYCATALYST_TRANSFER",
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$Path) {
    if (!(Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Get-FileHashSafe([string]$Path) {
    if (!(Test-Path -LiteralPath $Path)) { return $null }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

if (!(Test-Path -LiteralPath $TransferRoot)) {
    throw "Transfer root not found: $TransferRoot"
}

if (!(Test-Path -LiteralPath $RepoRoot)) {
    throw "Repo root not found: $RepoRoot"
}

$rules = @(
    @{
        Source = "downloads\raw\master_registry"
        Target = "workspace\downloads\raw\master_registry"
        Pattern = "*.geojson"
    },
    @{
        Source = "downloads\raw\osm"
        Target = "workspace\downloads\raw\osm"
        Pattern = "*.json"
    },
    @{
        Source = "downloads\curated\itinere"
        Target = "workspace\downloads\curated\itinere"
        Pattern = "*.geojson"
    },
    @{
        Source = "downloads\curated\protection_buffers"
        Target = "workspace\downloads\curated\protection_buffers"
        Pattern = "*.geojson"
    },
    @{
        Source = "data_gaps_field_names_geonames\raw"
        Target = "workspace\downloads\raw\osm\bavaria_repair"
        Pattern = "*.json"
    },
    @{
        Source = "osm_ingest_engine\raw"
        Target = "workspace\osm_ingest_engine\raw"
        Pattern = "*.json"
    }
)

$report = New-Object System.Collections.Generic.List[object]

foreach ($rule in $rules) {
    $src = Join-Path $TransferRoot $rule.Source
    $dst = Join-Path $RepoRoot $rule.Target
    if (!(Test-Path -LiteralPath $src)) {
        continue
    }
    Ensure-Dir $dst

    Get-ChildItem -LiteralPath $src -File -Filter $rule.Pattern | ForEach-Object {
        $sourcePath = $_.FullName
        $targetPath = Join-Path $dst $_.Name
        $sourceHash = Get-FileHashSafe $sourcePath
        $targetHash = Get-FileHashSafe $targetPath

        $action = if ($null -eq $targetHash) { "missing_in_repo" }
        elseif ($sourceHash -ne $targetHash) { "different" }
        else { "identical" }

        if ($Apply -and $action -ne "identical") {
            Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        }

        $report.Add([pscustomobject]@{
            source_rel = (Join-Path $rule.Source $_.Name)
            target_rel = (Join-Path $rule.Target $_.Name)
            status = $action
            copied = [bool]($Apply -and $action -ne "identical")
            source_sha256 = $sourceHash
            target_sha256_before = $targetHash
        })
    }
}

$reportDir = Join-Path $RepoRoot "workspace\reports"
Ensure-Dir $reportDir

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$csvPath = Join-Path $reportDir ("transfer_sync_report_" + $timestamp + ".csv")
$jsonPath = Join-Path $reportDir ("transfer_sync_report_" + $timestamp + ".json")

$report | Sort-Object status, source_rel | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $csvPath
$report | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path $jsonPath

$summary = $report | Group-Object status | Sort-Object Name | ForEach-Object {
    "{0}: {1}" -f $_.Name, $_.Count
}

Write-Host ("Mode: " + ($(if ($Apply) { "APPLY" } else { "PLAN" })))
Write-Host ("RepoRoot: " + $RepoRoot)
Write-Host ("TransferRoot: " + $TransferRoot)
Write-Host ("Report CSV: " + $csvPath)
Write-Host ("Report JSON: " + $jsonPath)
Write-Host ("Summary: " + ($summary -join ", "))
