<# Atom: Inject JavaScript into Chrome via DevTools Protocol. #>
param(
    [Parameter(Mandatory)]
    [string]$Script,

    [int]$Port = 9222,

    [int]$TimeoutSeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ─── 1. Get WebSocket debug URL ───
$jsonUrl = "http://localhost:$Port/json"
try {
    $tabs = Invoke-RestMethod -Uri $jsonUrl -TimeoutSec 5
} catch {
    throw "Cannot connect to Chrome DevTools on port $Port. Is Chrome running with --remote-debugging-port=$Port ?"
}

# Find the best page target: only real http/https pages
$page = $tabs | Where-Object {
    $_.type -eq "page" -and
    ($_.url -like "http://*" -or $_.url -like "https://*") -and
    $_.url -notmatch "^https?://data/?$"
} | Select-Object -First 1

# Fallback: about:blank is fine too (will navigate later)
if (-not $page) {
    $page = $tabs | Where-Object { $_.type -eq "page" -and $_.url -eq "about:blank" } | Select-Object -First 1
}
if (-not $page) {
    $page = $tabs | Where-Object { $_.type -eq "page" } | Select-Object -First 1
}
if (-not $page) {
    throw "No active page found in Edge on port $Port"
}

$wsUrl = $page.webSocketDebuggerUrl
if (-not $wsUrl) {
    throw "No WebSocket URL available for target: $($page.title)"
}

Write-Host "[eval-browser] target: $($page.title) ($($page.url))"

# ─── 2. Connect WebSocket and evaluate ───
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$cts = [System.Threading.CancellationTokenSource]::new()
$cts.CancelAfter([TimeSpan]::FromSeconds($TimeoutSeconds))

try {
    $ws.ConnectAsync([Uri]$wsUrl, $cts.Token).GetAwaiter().GetResult() | Out-Null

    # Build CDP Runtime.evaluate message
    $msg = @{
        id     = 1
        method = "Runtime.evaluate"
        params = @{
            expression  = $Script
            awaitPromise = $true
            returnByValue = $true
        }
    } | ConvertTo-Json -Depth 10 -Compress

    $msgBytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $seg = [System.ArraySegment[byte]]::new($msgBytes)

    $ws.SendAsync($seg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).GetAwaiter().GetResult() | Out-Null

    # ─── 3. Read response ───
    $recvBuffer = New-Object byte[] 1048576  # 1 MB
    $result = New-Object System.Text.StringBuilder

    do {
        $segRecv = [System.ArraySegment[byte]]::new($recvBuffer)
        $recvResult = $ws.ReceiveAsync($segRecv, $cts.Token).GetAwaiter().GetResult()
        $chunk = [System.Text.Encoding]::UTF8.GetString($recvBuffer, 0, $recvResult.Count)
        [void]$result.Append($chunk)
    } while (-not $recvResult.EndOfMessage)

    $raw = $result.ToString()
    $response = $raw | ConvertFrom-Json

    # Check for CDP error (StrictMode-safe)
    $hasException = $response.result.PSObject.Properties['exceptionDetails']
    if ($hasException) {
        $ed = $response.result.exceptionDetails
        $errMsg = if ($ed.PSObject.Properties['exception']) { $ed.exception.description } else { $ed.text }
        throw "JS execution error: $errMsg"
    }

    $value = $response.result.result.value
    Write-Host "[eval-browser] result: $value"
    return $value

} finally {
    if ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).GetAwaiter().GetResult() | Out-Null
    }
    $ws.Dispose()
    $cts.Dispose()
}
