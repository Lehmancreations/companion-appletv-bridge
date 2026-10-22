# Install the Apple TV bridge on Windows: Python environment, pairing, and a scheduled task
# so the bridge starts when you log in.
# Run in PowerShell from the repo folder:
#   powershell -ExecutionPolicy Bypass -File install\windows\install.ps1
$ErrorActionPreference = "Stop"

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Venv = Join-Path $Repo ".venv"
$TaskName = "Apple TV Bridge for Companion"

$Python = Get-Command py -ErrorAction SilentlyContinue
if ($Python) { $PyArgs = @("-3") } else {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    $PyArgs = @()
}
if (-not $Python) {
    Write-Host "Python not found. Install it from https://www.python.org/downloads/windows/ (tick 'Add python.exe to PATH')."
    exit 1
}

Write-Host "==> Creating Python environment in $Venv"
& $Python.Source @PyArgs -m venv $Venv
& "$Venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
& "$Venv\Scripts\python.exe" -m pip install --quiet -r (Join-Path $Repo "requirements.txt")

if (-not (Test-Path (Join-Path $Repo "config.json"))) {
    Write-Host "==> Pairing with your Apple TV"
    & "$Venv\Scripts\python.exe" (Join-Path $Repo "pair.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "==> config.json found, skipping pairing (delete it and re-run to pair again)"
}

Write-Host "==> Registering scheduled task '$TaskName' (starts at log on)"
$Action = New-ScheduledTaskAction -Execute "$Venv\Scripts\pythonw.exe" `
    -Argument "`"$(Join-Path $Repo 'bridge.py')`"" -WorkingDirectory $Repo
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Host "==> Checking the bridge"
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    try { Invoke-RestMethod "http://127.0.0.1:8765/" -TimeoutSec 2 | Out-Null; $ok = $true; break } catch { Start-Sleep -Milliseconds 500 }
}
if ($ok) {
    Write-Host "Bridge is running at http://127.0.0.1:8765"
    Write-Host "If Windows Firewall asks about Python, allow it on Private networks."
} else {
    Write-Host "The bridge didn't answer yet. Run it by hand to see errors:"
    Write-Host "  `"$Venv\Scripts\python.exe`" `"$(Join-Path $Repo 'bridge.py')`""
}
