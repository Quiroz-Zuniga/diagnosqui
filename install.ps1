# Instalador de DiagnosQui para Windows 10 y 11.
$ErrorActionPreference = "Stop"
$VenvPath = if ($env:DIAGNOSQUI_VENV) { $env:DIAGNOSQUI_VENV } else { Join-Path $env:USERPROFILE ".diagnosqui-venv" }
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "Instalando DiagnosQui: escritorio y terminal" -ForegroundColor Cyan
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 'Se requiere Python 3.9 o posterior')"
if ($LASTEXITCODE -ne 0) { throw "Python 3.9 o posterior debe estar disponible en PATH." }
python -m venv $VenvPath
if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual." }
& $PythonExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar pip." }
& $PythonExe -m pip install -e "${PSScriptRoot}[windows]"
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }

$ScriptsDir = Join-Path $VenvPath "Scripts"
Write-Host "Instalación completada." -ForegroundColor Green
Write-Host "Escritorio (sin consola):"
Write-Host "  Start-Process `"$ScriptsDir\DiagnosQui-Escritorio.exe`""
Write-Host "Terminal:"
Write-Host "  & `"$ScriptsDir\diagnosqui.exe`""
Write-Host "También puedes agregar $ScriptsDir a PATH."
