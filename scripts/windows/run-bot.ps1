# Keeps the bot running: starts it, and restarts it whenever it exits or crashes.
# Started automatically by the scheduled task from install-task.ps1; you can also run it by hand.
$ErrorActionPreference = 'Continue'

$Root   = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$LogDir = Join-Path $Root 'logs'
$Log    = Join-Path $LogDir 'bot.log'

Set-Location $Root
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$env:PYTHONUTF8 = '1'          # Finnish characters in logs/messages
$env:PYTHONUNBUFFERED = '1'    # write log lines immediately

function Write-Log([string]$msg) {
    Add-Content -Path $Log -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg" -Encoding UTF8
}

if (-not (Test-Path $Python)) {
    Write-Log "ERROR: $Python not found. Run: py -m venv .venv ; .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

$delay = 5
while ($true) {
    # Simple rotation so the log can't fill the disk.
    if ((Test-Path $Log) -and ((Get-Item $Log).Length -gt 10MB)) {
        Move-Item -Force $Log "$Log.1"
    }

    Write-Log 'Starting bot'
    $started = Get-Date
    # cmd.exe does the redirection: PowerShell 5.1's own '>>' would write UTF-16 and mangle the log.
    cmd.exe /c "`"$Python`" main.py >> `"$Log`" 2>&1"
    $code = $LASTEXITCODE
    $ranFor = (Get-Date) - $started
    Write-Log "Bot exited with code $code after $([int]$ranFor.TotalSeconds)s"

    # Back off if it keeps crashing right away (bad token, no network), reset after a healthy run.
    if ($ranFor.TotalMinutes -ge 10) { $delay = 5 } else { $delay = [Math]::Min($delay * 2, 300) }
    Write-Log "Restarting in $delay s"
    Start-Sleep -Seconds $delay
}
