<#
.SYNOPSIS
Runs external commands, applications, and RPA workflows in sequence.

.NOTES
Scope: Runs only the commands, applications, and workflow files configured in the script.
Permissions: Run with the same privileges required by this project; no elevation is performed.
Risk: Configured commands may change local state, and RPA steps control the active desktop.
Rollback: Stop the script with Ctrl+C. This template does not modify project configuration.
Logging: Writes Series progress to the console; invoked tools keep their own normal logs.
#>

param(
    [string]$FirstApp = "<FIRST_APP_PATH>",
    [string]$FirstWorkflow = "<FIRST_WORKFLOW_JSON>",
    [string]$SecondApp = "<SECOND_APP_PATH>",
    [string]$SecondWorkflow = "<SECOND_WORKFLOW_JSON>"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Invoke-SeriesCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Name,

        [Parameter(Mandatory)]
        [string]$FilePath,

        [string[]]$ArgumentList = @()
    )

    if (-not (Get-Command -Name $FilePath -ErrorAction SilentlyContinue)) {
        throw "command not found: $FilePath"
    }

    Write-Host "[series] running: $Name"
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "command failed with exit code ${LASTEXITCODE}: $Name"
    }
}

function Start-SeriesApp {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,

        [string[]]$ArgumentList = @(),

        [switch]$Maximized
    )

    Write-Host "[series] starting: $FilePath"
    $options = @{
        FilePath = $FilePath
        PassThru = $true
    }
    if ($ArgumentList.Count -gt 0) {
        $options.ArgumentList = $ArgumentList
    }
    if ($Maximized) {
        $options.WindowStyle = "Maximized"
    }

    Start-Process @options
}

function Wait-SeriesReady {
    param(
        [int]$Seconds = 2
    )

    Write-Host "[series] waiting $Seconds second(s) for UI readiness"
    Start-Sleep -Seconds $Seconds
}

function Invoke-SeriesRpa {
    param(
        [Parameter(Mandatory)]
        [string]$Workflow
    )

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
}

Push-Location $ProjectRoot
try {
    # Add any foreground CLI or script with Invoke-SeriesCommand.
    # Invoke-SeriesCommand -Name "prepare input" -FilePath "python" -ArgumentList @("scripts/prepare.py")

    Start-SeriesApp -FilePath $FirstApp -Maximized
    Wait-SeriesReady -Seconds 2
    Invoke-SeriesRpa -Workflow $FirstWorkflow

    Start-SeriesApp -FilePath $SecondApp
    Wait-SeriesReady -Seconds 2
    Invoke-SeriesRpa -Workflow $SecondWorkflow

    Write-Host "[series] complete"
} finally {
    Pop-Location
}
