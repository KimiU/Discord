#Requires -RunAsAdministrator
# Stops the bot and removes the scheduled task.
param([string]$TaskName = 'NlaBot')

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskName      # stops the run-bot.ps1 restart loop
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
# The python process can outlive the loop, so stop it explicitly (otherwise you'd get two bots later).
& (Join-Path $PSScriptRoot 'restart-bot.ps1')
Write-Host "Task '$TaskName' removed."
