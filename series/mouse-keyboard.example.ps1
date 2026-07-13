<# Example Series: start an app, replay mouse actions, paste text, then replay again. #>
param(
    [string]$App = "<APP_EXE>",
    [string]$WindowTitle = "<WINDOW_TITLE>",
    [string]$OpenWorkflow = "<OPEN_WORKFLOW_JSON>",
    [string]$SubmitWorkflow = "<SUBMIT_WORKFLOW_JSON>",
    [string]$Text = "<TEXT>"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Atoms = Join-Path $PSScriptRoot "atoms"

& (Join-Path $Atoms "start-app.ps1") -FilePath $App -Maximized
& (Join-Path $Atoms "wait.ps1") -Seconds 2
& (Join-Path $Atoms "run-rpa.ps1") -Workflow $OpenWorkflow
& (Join-Path $Atoms "paste.ps1") -WindowTitle $WindowTitle -Text $Text
& (Join-Path $Atoms "run-rpa.ps1") -Workflow $SubmitWorkflow

Write-Host "[series] complete"
