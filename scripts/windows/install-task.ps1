#Requires -RunAsAdministrator
# Registers a Windows scheduled task that starts the bot at boot (no login needed) and keeps it running.
# Run once from an *elevated* PowerShell:  powershell -ExecutionPolicy Bypass -File scripts\windows\install-task.ps1
param([string]$TaskName = 'NlaBot')

$Root   = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Runner = Join-Path $PSScriptRoot 'run-bot.ps1'

if (-not (Test-Path (Join-Path $Root '.env'))) {
    Write-Error "No .env in $Root. Copy .env.example to .env and set DISCORD_TOKEN first."
    exit 1
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Runner`"" `
    -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -AtStartup
# SYSTEM = runs without anyone logged in. See README for running it as a less privileged account.
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Host "Task '$TaskName' installed and started. Log: $Root\logs\bot.log"
