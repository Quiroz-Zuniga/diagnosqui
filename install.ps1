# Instalador de DiagnosQui para Windows PowerShell
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "     Instalador de DiagnosQui (Windows)    " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$VenvPath = Join-Path $env:USERPROFILE ".diagnosqui-venv"
$PipExe = Join-Path $VenvPath "Scripts\pip.exe"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "-> Creando entorno virtual en $VenvPath..." -ForegroundColor Yellow
python -m venv $VenvPath

Write-Host "-> Actualizando pip e instalando dependencias..." -ForegroundColor Yellow
& $PipExe install --upgrade pip
& $PipExe install -e .[windows]

$ScriptsDir = Join-Path $VenvPath "Scripts"
Write-Host ""
Write-Host "¡Instalación completada exitosamente!" -ForegroundColor Green
Write-Host "Para ejecutar directamente:" -ForegroundColor Cyan
Write-Host "  & `"$ScriptsDir\diagnosqui.exe`"" -ForegroundColor White
Write-Host "O agrega la siguiente ruta a tus Variables de Entorno (PATH):" -ForegroundColor Cyan
Write-Host "  $ScriptsDir" -ForegroundColor White
