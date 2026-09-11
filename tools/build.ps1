# Empaqueta DiagnosQui como ejecutables de Windows (PyInstaller onefile).
# Uso (en PowerShell, desde la raíz del proyecto):
#   .\tools\build.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"

if (-Not (Test-Path $Python)) {
    $Python = (Get-Command python).Source
}

$PyInstaller = Join-Path $Venv "Scripts\pyinstaller.exe"
if (-Not (Test-Path $PyInstaller)) {
    Write-Host "Instalando PyInstaller..."
    & $Python -m pip install pyinstaller
}

& $Python (Join-Path $PSScriptRoot "make_icon.py")
& $Python -m PyInstaller --clean --noconfirm (Join-Path $Root "build_exe.spec")

Write-Host "Ejecutables generados en dist/:"
Get-ChildItem (Join-Path $Root "dist") | Select-Object -ExpandProperty Name