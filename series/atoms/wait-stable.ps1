<# Atom: wait for screen to stabilize by comparing consecutive screenshots. #>
param(
    [int]$IntervalSecond = 1,
    [double]$Threshold = 0.99,
    [int]$TimeoutSecond = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$totalPixels = 100 * 56
$maxDiffPixels = [int]($totalPixels * (1 - $Threshold))

function Get-Screenshot {
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

function Compare-Bitmaps($a, $b) {
    $diff = 0
    for ($y = 0; $y -lt $a.Height; $y++) {
        for ($x = 0; $x -lt $a.Width; $x++) {
            if ($a.GetPixel($x, $y) -ne $b.GetPixel($x, $y)) {
                $diff++
                if ($diff -gt $maxDiffPixels) { return $diff }
            }
        }
    }
    return $diff
}

$elapsed = 0
$prev = $null

while ($elapsed -lt $TimeoutSecond) {
    $current = Get-Screenshot

    if ($prev -ne $null) {
        $t0 = Shrink-Bitmap $current 100 56
        $t1 = Shrink-Bitmap $prev 100 56
        $diff = Compare-Bitmaps $t0 $t1

        $t0.Dispose()
        $t1.Dispose()
        $prev.Dispose()

        if ($diff -le $maxDiffPixels) {
            $current.Dispose()
            Write-Host "[series] screen stable (diff=$diff/$totalPixels, threshold=$Threshold)"
            return $true
        }
    }

    $prev = $current
    Start-Sleep -Seconds $IntervalSecond
    $elapsed += $IntervalSecond
}

if ($prev) { $prev.Dispose() }
Write-Host "[series] screen did NOT stabilize within ${TimeoutSecond}s"
return $false
