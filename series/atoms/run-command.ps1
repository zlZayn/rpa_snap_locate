<# Run one foreground CLI command and fail the Series on a non-zero exit code. #>
param(
    [Parameter(Mandatory)]
    [string]$Name,

    [Parameter(Mandatory)]
    [string]$FilePath,

    [string[]]$ArgumentList = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command -Name $FilePath -ErrorAction SilentlyContinue)) {
    throw "command not found: $FilePath"
}

Write-Host "[series] running command: $Name"
& $FilePath @ArgumentList
if ($LASTEXITCODE -ne 0) {
    throw "command failed with exit code ${LASTEXITCODE}: $Name"
}
