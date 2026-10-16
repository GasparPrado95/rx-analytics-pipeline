<#
.SYNOPSIS
    Runs the full pipeline (EL -> dbt build -> freshness) with the repo's virtual environment.
    This is the action Windows Task Scheduler calls; it can also be run by hand.

.EXAMPLE
    .\scripts\run_pipeline.ps1
    .\scripts\run_pipeline.ps1 -Simulate          # write a new source batch first (demo)
    .\scripts\run_pipeline.ps1 -FullRefresh
#>
[CmdletBinding()]
param(
    [switch]$Simulate,
    [switch]$FullRefresh
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found at $python. See README > Run it from a clean machine."
    exit 2
}

$pipelineArgs = @('-m', 'orchestration.run')
if ($Simulate) { $pipelineArgs += '--simulate' }
if ($FullRefresh) { $pipelineArgs += '--full-refresh' }

Push-Location $repo
try {
    & $python @pipelineArgs
    $code = $LASTEXITCODE
}
finally {
    Pop-Location
}

# Task Scheduler shows this as "Last Run Result": 0 = success, 1 = a step failed.
exit $code
