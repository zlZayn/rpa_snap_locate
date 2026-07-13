<# Series: open Edge at target URL, replay mouse workflow, then close. #>
param(
    [string]$App = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    [string]$Workflow = "data\workflows\ds_try-20260712_115059_291619-9events.json",
    [string]$Url = "https://chat.deepseek.com/"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Atoms = Join-Path $PSScriptRoot "..\atoms"

& (Join-Path $Atoms "start-app.ps1") -FilePath $App -ArgumentList @("--start-maximized", $Url)
& (Join-Path $Atoms "wait.ps1") -Seconds 3

& (Join-Path $Atoms "run-rpa.ps1") -Workflow $Workflow

Write-Host "[series] closing Edge"
& (Join-Path $Atoms "send-keys.ps1") -CurrentWindow -Keys "%{F4}"
Start-Sleep -Seconds 1

Write-Host "[series] complete"
# This concrete Series is launched as its own `pwsh -NoProfile -File` process.
# Keep the explicit exit because this environment was verified to retain the
# uv/pwsh process chain otherwise; do not copy it into a dot-sourced Series.
exit 0
