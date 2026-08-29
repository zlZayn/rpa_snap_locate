<# Atom: wait for stability.
   Modes:
     pixel - wait for screen to stabilize (screenshot comparison)
     file  - wait for directory to stabilize (file list comparison)
   Requires $StableCount consecutive stable polls before returning. #>
param(
    [ValidateSet("pixel","file")]
    [string]$Mode = "pixel",
    [double]$PollSeconds = 1,
    [double]$SimilarityThreshold = 0.99,
    [int]$TimeoutSeconds = 30,
    [int]$StableCount = 3,
    [string]$Path = "",
    [array]$BeforeSnapshot = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- File mode helpers ---
$script:TempExtensions = @('.crdownload', '.part', '.tmp', '.download')

function Get-DirectorySnapshot {
    param([string]$DirPath)
    if (-not (Test-Path -LiteralPath $DirPath)) { return @() }
    @(
        Get-ChildItem -LiteralPath $DirPath -File |
            ForEach-Object { "$($_.Name)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)" } |
            Sort-Object
    )
}

function Test-HasTempFiles {
    param([string]$DirPath)
    if (-not (Test-Path -LiteralPath $DirPath)) { return $false }
    $tempFiles = @(Get-ChildItem -LiteralPath $DirPath -File |
        Where-Object { $script:TempExtensions -contains $_.Extension.ToLower() })
    return $tempFiles.Count -gt 0
}

# --- Pixel mode helpers ---
function Get-Screenshot {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bounds.Size)
    $g.Dispose()
    return $bmp
}

function Shrink-Bitmap($source, $w, $h) {
    $thumb = New-Object System.Drawing.Bitmap $w, $h
    $g = [System.Drawing.Graphics]::FromImage($thumb)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($source, 0, 0, $w, $h)
    $g.Dispose()
    return $thumb
}

function Compare-Bitmaps($a, $b, $maxDiff) {
    $diff = 0
    for ($y = 0; $y -lt $a.Height; $y++) {
        for ($x = 0; $x -lt $a.Width; $x++) {
            if ($a.GetPixel($x, $y) -ne $b.GetPixel($x, $y)) {
                $diff++
                if ($diff -gt $maxDiff) { return $diff }
            }
        }
    }
    return $diff
}

# --- Main ---
$elapsed = 0
$stable = 0

if ($Mode -eq "pixel") {
    Add-Type -AssemblyName System.Drawing
    Add-Type -AssemblyName System.Windows.Forms

    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $totalPixels = 100 * 56
    $maxDiffPixels = [int]($totalPixels * (1 - $SimilarityThreshold))

    $prev = $null
    while ($elapsed -lt $TimeoutSeconds) {
        $current = Get-Screenshot
        if ($prev -ne $null) {
            $t0 = Shrink-Bitmap $current 100 56
            $t1 = Shrink-Bitmap $prev 100 56
            $diff = Compare-Bitmaps $t0 $t1 $maxDiffPixels
            $t0.Dispose(); $t1.Dispose(); $prev.Dispose()

            if ($diff -le $maxDiffPixels) {
                $stable++
                Write-Host "[series] stable $stable/$StableCount (diff=$diff/$totalPixels)"
                if ($stable -ge $StableCount) {
                    $current.Dispose()
                    Write-Host "[series] screen stable after ${elapsed}s"
                    return $true
                }
            } else {
                $stable = 0
                Write-Host "[series] unstable (diff=$diff/$totalPixels), reset"
            }
        }
        $prev = $current
        Start-Sleep -Seconds $PollSeconds
        $elapsed += $PollSeconds
    }
    if ($prev) { $prev.Dispose() }
    Write-Host "[series] screen did NOT stabilize within ${TimeoutSeconds}s"
    return $false

} else {
    # File mode
    if (-not $Path) {
        throw "File mode requires -Path parameter"
    }

    $beforeCount = @($BeforeSnapshot).Count

    # Phase 1: Wait for at least one new file to appear
    $phase1Timeout = [Math]::Max($TimeoutSeconds / 2, 10)
    while ($elapsed -lt $phase1Timeout) {
        Start-Sleep -Seconds $PollSeconds
        $elapsed += $PollSeconds
        $current = @(Get-DirectorySnapshot -DirPath $Path)
        if ($current.Count -gt $beforeCount) {
            Write-Host "[series] download detected ($($current.Count) files, was $beforeCount)"
            break
        }
    }
    if ($elapsed -ge $phase1Timeout) {
        Write-Host "[series] WARNING: no new files appeared within ${phase1Timeout}s"
        return $false
    }

    # Phase 2: Wait for file list to stabilize
    $prev = @(Get-DirectorySnapshot -DirPath $Path)
    while ($elapsed -lt $TimeoutSeconds) {
        Start-Sleep -Seconds $PollSeconds
        $elapsed += $PollSeconds

        $current = @(Get-DirectorySnapshot -DirPath $Path)
        $hasTemp = Test-HasTempFiles -DirPath $Path
        $same = ($current.Count -eq $prev.Count) -and
                ((Compare-Object $prev $current -SyncWindow 0 -ErrorAction SilentlyContinue) -eq $null) -and
                (-not $hasTemp)

        if ($same) {
            $stable++
            Write-Host "[series] file stable $stable/$StableCount (files=$($current.Count))"
            if ($stable -ge $StableCount) {
                Write-Host "[series] files stable after ${elapsed}s"
                return $true
            }
        } else {
            $stable = 0
            $reason = if ($hasTemp) { "temp files present" } else { "files changed" }
            $diff = $current.Count - $beforeCount
            Write-Host "[series] unstable: $reason (files=$($current.Count), delta=$diff), reset"
        }
        $prev = $current
    }
    Write-Host "[series] WARNING: files did NOT stabilize within ${TimeoutSeconds}s"
    return $false
}
