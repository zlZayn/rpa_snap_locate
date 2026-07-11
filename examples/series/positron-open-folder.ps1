<#
.SYNOPSIS
Opens Positron maximized and replays the open-folder workflow.

.NOTES
Scope: Runs only the Positron application and the configured RPA workflow.
Permissions: Requests elevation once so Positron and replay match the recorded
"Positron [Administrator]" target's integrity level.
Risk: RPA steps control the active desktop — do not use keyboard/mouse while the script runs.
Rollback: Stop the script with Ctrl+C.
Logging: Writes Series progress to the console; Positron and RPA maintain their own logs.
#>

param(
    [string]$AppPath = "E:\positron\Positron\Positron.exe",
    [string]$Workflow = "data\workflows\positron_open_folder-20260711_140950_125779-2steps.json"
)

# The recorded target is "Positron [Administrator]". UIPI blocks mouse input
# from a non-elevated replay process, so elevate the whole series before either
# Positron or Python is started.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$isAdministrator = $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdministrator) {
    Write-Host "[series] requesting elevation for target and replay"
    $quote = {
        param([string]$Value)
        '"' + $Value.Replace('"', '\"') + '"'
    }
    $arguments = @(
        "-NoProfile"
        "-ExecutionPolicy", "Bypass"
        "-File", (& $quote $PSCommandPath)
        "-AppPath", (& $quote $AppPath)
        "-Workflow", (& $quote $Workflow)
    )
    $elevated = Start-Process `
        -FilePath "powershell.exe" `
        -Verb RunAs `
        -ArgumentList $arguments `
        -Wait `
        -PassThru
    exit $elevated.ExitCode
}

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Start-SeriesApp {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,
        [string[]]$ArgumentList = @(),
        [switch]$Maximized
    )
    Write-Host "[series] starting: $FilePath"
    $options = @{ FilePath = $FilePath; PassThru = $true }
    if ($ArgumentList.Count -gt 0) { $options.ArgumentList = $ArgumentList }
    $extension = [System.IO.Path]::GetExtension($FilePath)
    $isCommandScript = $extension -in @(".cmd", ".bat")
    if ($isCommandScript) {
        # A command script is hosted by cmd.exe and may wait for the GUI app's
        # entire lifetime. Keep that host invisible.
        $options.WindowStyle = "Hidden"
    } elseif ($Maximized) {
        $options.WindowStyle = "Maximized"
    }
    Start-Process @options
}

function Wait-SeriesReady {
    param([int]$Seconds = 3)
    Write-Host "[series] waiting $Seconds second(s) for UI readiness"
    Start-Sleep -Seconds $Seconds
}

function Invoke-SeriesRpa {
    param([Parameter(Mandatory)][string]$Workflow)
    $workflowPath = if ([System.IO.Path]::IsPathRooted($Workflow)) { $Workflow }
    else { Join-Path $ProjectRoot $Workflow }
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
    Start-SeriesApp -FilePath $AppPath -Maximized
    Wait-SeriesReady -Seconds 4

    Invoke-SeriesRpa -Workflow $Workflow
    Write-Host "[series] complete"
} finally {
    Pop-Location
}
