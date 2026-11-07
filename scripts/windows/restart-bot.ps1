# Restarts just the bot process; run-bot.ps1 starts it again within seconds with the current code.
# Use after `git pull` or editing .env. Run from an elevated PowerShell (the bot runs as SYSTEM).
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$PidFile = Join-Path $Root 'bot.pid'

if (-not (Test-Path $PidFile)) { Write-Host 'No bot.pid - bot not running?'; exit 0 }
$botPid = [int](Get-Content $PidFile)
$proc = Get-Process -Id $botPid -ErrorAction SilentlyContinue
if ($proc -and $proc.ProcessName -like 'python*') {
    Stop-Process -Id $botPid -Force
    Write-Host "Stopped bot (PID $botPid); it will restart automatically."
} else {
    Write-Host "PID $botPid is not a running bot process."
}
