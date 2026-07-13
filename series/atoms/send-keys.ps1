<# Activate one window, then type text or send a SendKeys shortcut. #>
[CmdletBinding(DefaultParameterSetName = "Text")]
param(
    [string]$WindowTitle,

    [switch]$CurrentWindow,

    [Parameter(Mandatory, ParameterSetName = "Text")]
    [string]$Text,

    [Parameter(Mandatory, ParameterSetName = "Keys")]
    [string]$Keys,

    [ValidateRange(0, 5000)]
    [int]$AfterActivateMilliseconds = 200,

    [ValidateRange(0, 1000)]
    [int]$CharacterDelayMilliseconds = 20
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$shell = New-Object -ComObject WScript.Shell
$targetCount = [int](-not [string]::IsNullOrWhiteSpace($WindowTitle)) + [int]$CurrentWindow.IsPresent
if ($targetCount -ne 1) {
    throw "specify exactly one keyboard target: -WindowTitle or -CurrentWindow"
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

if ($PSCmdlet.ParameterSetName -eq "Keys") {
    $shell.SendKeys($Keys)
    Write-Host "[series] keyboard shortcut sent to: $targetLabel"
    return
}

$specialCharacters = @{
    '+' = '{+}'; '^' = '{^}'; '%' = '{%}'; '~' = '{~}'
    '(' = '{(}'; ')' = '{)}'; '[' = '{[}'; ']' = '{]}'
    '{' = '{{}'; '}' = '{}}'
}
foreach ($character in $Text.ToCharArray()) {
    if ($character -eq "`r") { continue }
    $sendValue = [string]$character
    if ($character -eq "`n") {
        $sendValue = '{ENTER}'
    } elseif ($character -eq "`t") {
        $sendValue = '{TAB}'
    } elseif ($specialCharacters.ContainsKey([string]$character)) {
        $sendValue = $specialCharacters[[string]$character]
    }
    $shell.SendKeys($sendValue)
    if ($CharacterDelayMilliseconds -gt 0) {
        Start-Sleep -Milliseconds $CharacterDelayMilliseconds
    }
}
Write-Host "[series] keyboard text sent to: $targetLabel"
