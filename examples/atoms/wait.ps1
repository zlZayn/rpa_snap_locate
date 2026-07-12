<# Wait a fixed time between Series steps. Prefer a real readiness check when available. #>
param(
    [ValidateRange(0, 86400)]
    [int]$Seconds = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "[series] waiting $Seconds second(s)"
Start-Sleep -Seconds $Seconds
