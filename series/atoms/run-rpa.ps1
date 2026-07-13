<# Replay one existing RPA workflow and wait for completion. #>
param(
    [Parameter(Mandatory)]
    [string]$Workflow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$workflowPath = if ([System.IO.Path]::IsPathRooted($Workflow)) {
    $Workflow
} else {
    Join-Path $ProjectRoot $Workflow
}

if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
    throw "workflow not found: $workflowPath"
}

Write-Host "[series] replaying: $workflowPath"
uv run python (Join-Path $ProjectRoot "main.py") run $workflowPath
if ($LASTEXITCODE -ne 0) {
    throw "RPA workflow failed with exit code ${LASTEXITCODE}: $workflowPath"
}
