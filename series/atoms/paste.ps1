<# Paste text into a window via clipboard (supports Unicode). #>
[CmdletBinding(DefaultParameterSetName = "CurrentWindow")]
param(
    [Parameter(Mandatory)]
    [string]$Text,

    [Parameter(ParameterSetName = "WindowTitle")]
    [string]$WindowTitle,

    [Parameter(ParameterSetName = "CurrentWindow")]
    [switch]$CurrentWindow,

    [ValidateRange(0, 5000)]
    [int]$AfterActivateMilliseconds = 200,

    [switch]$ShiftControlV
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$shell = New-Object -ComObject WScript.Shell
$targetCount = [int](-not [string]::IsNullOrWhiteSpace($WindowTitle)) + [int]$CurrentWindow.IsPresent
if ($targetCount -ne 1) {
    throw "specify exactly one target: -WindowTitle or -CurrentWindow"
}

$targetLabel = "current foreground window"
if (-not $CurrentWindow) {
    if (-not $shell.AppActivate($WindowTitle)) {
        throw "target window not found or could not be activated: $WindowTitle"
    }
    $targetLabel = $WindowTitle
    if ($AfterActivateMilliseconds -gt 0) {
        Start-Sleep -Milliseconds $AfterActivateMilliseconds
    }
}

Set-Clipboard -Value $Text
Start-Sleep -Milliseconds 200

$pasteKey = if ($ShiftControlV) { "+^v" } else { "^v" }
$shell.SendKeys($pasteKey)
Start-Sleep -Milliseconds 100

Write-Host "[series] pasted text to: $targetLabel"
