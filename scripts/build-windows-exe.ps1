$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $root ".venv\Scripts\python.exe"

if (!(Test-Path $python)) {
  Write-Host "Creating local Python environment..."
  py -3 -m venv (Join-Path $root ".venv")
}

Write-Host "Installing build tools..."
& $python -m pip install --upgrade pip pyinstaller
& $python -m pip install -e $root

Write-Host "Building docs-for-me.exe..."
& $python -m PyInstaller `
  --onefile `
  --name docs-for-me `
  --clean `
  --distpath (Join-Path $root "prebuilt\win32-x64") `
  --workpath (Join-Path $root "build\pyinstaller") `
  --specpath (Join-Path $root "build\pyinstaller") `
  (Join-Path $root "packaging\pyinstaller_entry.py")

Write-Host ""
Write-Host "Built:"
Write-Host (Join-Path $root "prebuilt\win32-x64\docs-for-me.exe")
