$ErrorActionPreference = 'Stop'
$source = Join-Path $PSScriptRoot 'BlenderFusionBridge'
$target = Join-Path $env:LOCALAPPDATA 'BlenderFusionBridge\AddIns\BlenderFusionBridge'
if (-not (Test-Path (Join-Path $source 'BlenderFusionBridge.py'))) {
    throw 'Extract the complete Windows ZIP before running this installer.'
}
# Test the same byte-range lock held by the Fusion receiver. Never replace live code.
$lockPath = Join-Path $env:LOCALAPPDATA 'BlenderFusionBridge\v2\fusion\receiver.lock'
if (Test-Path $lockPath) {
    $lock = [System.IO.File]::Open($lockPath, 'Open', 'ReadWrite', 'ReadWrite')
    try {
        $lock.Lock(0, 1)
        $lock.Unlock(0, 1)
    } catch {
        throw 'Stop BlenderFusionBridge in Fusion before installing an update.'
    } finally {
        $lock.Dispose()
    }
}
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path $source '*') -Destination $target -Recurse -Force
Write-Host ''
Write-Host 'Fusion receiver installed at:'
Write-Host $target
Write-Host ''
Write-Host 'ONE-TIME SETUP IN FUSION:'
Write-Host 'Utilities > Add-Ins > Scripts and Add-Ins > Add-Ins > +'
Write-Host 'Select this folder (or BlenderFusionBridge.py if the dialog asks for a file).'
Write-Host 'Run BlenderFusionBridge and enable Run on Startup.'
Write-Host 'Then install blender_fusion_bridge-0.2.2.zip in Blender Preferences > Add-ons.'
Start-Process explorer.exe -ArgumentList ('"' + $target + '"')
