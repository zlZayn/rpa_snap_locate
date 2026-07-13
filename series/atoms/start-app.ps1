<# Start one GUI application and return without waiting for it to exit. #>
param(
    [Parameter(Mandatory)]
    [string]$FilePath,

    [string[]]$ArgumentList = @(),

    [switch]$Maximized
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$options = @{
    FilePath = $FilePath
    PassThru = $true
}
if ($ArgumentList.Count -gt 0) {
    $options.ArgumentList = $ArgumentList
}

$extension = [System.IO.Path]::GetExtension($FilePath)
if ($extension -in @(".cmd", ".bat")) {
    $options.WindowStyle = "Hidden"
} elseif ($Maximized) {
    $options.WindowStyle = "Maximized"
}

Write-Host "[series] starting app: $FilePath"
Start-Process @options | Out-Null
