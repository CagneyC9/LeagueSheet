<#
Simple build script for Windows that runs PyInstaller to produce the single-file exe.
Usage:
  .\build.ps1            # builds in-place
  .\build.ps1 -Clean     # cleans previous build artifacts, then builds
#>
param(
    [switch]$Clean
)

if ($Clean) {
    Write-Host "Cleaning previous build artifacts..."
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist,build,LeagueSheet.spec
}

Write-Host "Building LeagueSheet.exe with PyInstaller (bundling champions.txt at bundle root)..."

# Ensure pip packages are available (doesn't reinstall if already present)
python -m pip install --upgrade pip; pip install -r requirements.txt pyinstaller

# Build: bundle `champions.txt` from repo root into the bundle root so the app can find it.
pyinstaller --noconfirm --onefile --windowed --add-data "champions.txt;." --name LeagueSheet LeagueSheet.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build complete. Artifact in: dist\LeagueSheet.exe (or dist\LeagueSheet\LeagueSheet.exe for one-dir)." -ForegroundColor Green
} else {
    Write-Host "PyInstaller failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
