<#
.SYNOPSIS
    Registers a daily Windows Task Scheduler job that runs scripts\run_pipeline.ps1.

.DESCRIPTION
    Runs as the current user (needed for Windows authentication to SQL Server), only when the
    user is logged on, so no password is stored. Re-running the script updates the task.
    Remove it with: Unregister-ScheduledTask -TaskName 'rx-analytics-pipeline' -Confirm:$false

.EXAMPLE
    .\scripts\register_scheduled_task.ps1                 # daily at 06:00
    .\scripts\register_scheduled_task.ps1 -At '07:30'
#>
[CmdletBinding()]
param(
    [string]$TaskName = 'rx-analytics-pipeline',
    [string]$At = '06:00'
)

$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'run_pipeline.ps1'
$repo = Split-Path -Parent $PSScriptRoot

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 15) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Description 'RxSource -> BigQuery (dlt) -> dbt build. Reports in logs\pipeline_*' -Force | Out-Null

Write-Host "Registered '$TaskName': daily at $At as $env:USERNAME."
Write-Host "Run it now:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Last result: (Get-ScheduledTaskInfo -TaskName '$TaskName').LastTaskResult   # 0 = success"
