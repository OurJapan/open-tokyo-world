# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
# Windows entry point. Uses the Python shipped with the specified Blender.
$ErrorActionPreference = 'Stop'
$otwBlender = $env:OTW_BLENDER
if (-not $otwBlender) {
    $otwCommand = Get-Command blender -ErrorAction SilentlyContinue
    if ($otwCommand) { $otwBlender = $otwCommand.Source }
}
if (-not $otwBlender) {
    $otwBlender = Join-Path $env:ProgramFiles 'Blender Foundation\Blender 4.5\blender.exe'
}
if (-not (Test-Path -LiteralPath $otwBlender -PathType Leaf)) {
    throw 'Blender 4.5.1 is required. Install/extract Blender, then set OTW_BLENDER to blender.exe. See docs/contributor-workspace.md.'
}
$otwPython = Join-Path (Split-Path -Parent $otwBlender) '4.5\python\bin\python.exe'
if (-not (Test-Path -LiteralPath $otwPython -PathType Leaf)) {
    throw 'Bundled Python was not found. Use a full Blender 4.5.1 installation, or Python 3.11/3.12 with scripts/workspace.py.'
}
$otwArguments = @($args)
if ($otwArguments.Count -eq 0) { $otwArguments = @('status') }
$otwOldUtf8 = $env:PYTHONUTF8
try {
    $env:PYTHONUTF8 = '1'
    & $otwPython (Join-Path $PSScriptRoot 'scripts\workspace.py') @otwArguments --blender $otwBlender
    $otwExit = $LASTEXITCODE
} finally {
    $env:PYTHONUTF8 = $otwOldUtf8
}
exit $otwExit
