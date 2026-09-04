# Plan de construcción — DiagnosQui
### Administrador/Diagnóstico de Hardware en Python, instalable en Linux y Windows

Este documento es el plan técnico para que se construya el sistema real (no la demo visual). Cubre arquitectura, módulos, la experiencia de terminal tipo bash/npm, y cómo empaquetarlo para instalar en ambos sistemas operativos.

---

## 1. Objetivo del proyecto

Construir un paquete Python llamado **`diagnosqui`** que:

- Se instala como un paquete descargable (`pip install diagnosqui` o `pip install git+<repo>`), mostrando al instalar/iniciar una animación tipo `npm install` (resolución de dependencias, spinners, `added N packages`).
- Al ejecutarse (`diagnosqui`), abre una interfaz de terminal con apariencia bash (prompt `➜`, colores, cursor parpadeante) en lugar del `input()` plano del menú original.
- Funciona en **Windows** (PowerShell/WMI/PnP) y **Linux** (`/proc`, `lspci`, `lsusb`, `psutil`) usando el mismo menú y los mismos comandos, con un backend que se adapta al sistema operativo detectado.
- Cumple la matriz de diagnóstico y el caso final del reto (CPU lento, USB con fallos, GPU con problemas gráficos).

---

## 2. Estructura de carpetas

```
diagnosqui/
├── pyproject.toml
├── README.md
├── requirements.txt
├── install.sh                 # instalador Linux/macOS
├── install.ps1                 # instalador Windows
├── diagnosqui/
│   ├── __init__.py
│   ├── cli.py                  # punto de entrada, arma el menú
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── boot.py             # animación estilo "npm install"
│   │   ├── terminal.py         # prompt, colores, spinners, barras de progreso
│   │   └── theme.py            # paleta de colores y estilos (rich)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── platform_utils.py   # detecta SO, elige backend correcto
│   │   ├── sistema.py
│   │   ├── cpu.py
│   │   ├── memoria.py
│   │   ├── discos.py
│   │   ├── red.py
│   │   ├── usb.py
│   │   ├── pci.py
│   │   ├── controladores.py
│   │   ├── problemas.py
│   │   ├── monitor.py
│   │   ├── io_monitor.py       # "Monitorizar E/S"
│   │   └── reporte.py          # "Generar reporte"
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── linux_backend.py    # lspci, lsusb, /proc, /sys
│   │   └── windows_backend.py  # PowerShell (Get-PnpDevice, Win32_VideoController…)
│   └── diagnostico/
│       ├── __init__.py
│       └── matriz.py           # matriz Componente/Evidencia/Estado/Posible problema
└── tests/
    └── test_core.py
```

---

## 3. La terminal estilo bash + instalación estilo npm

Esto es lo que ya se prototipó como demo HTML; ahora se implementa de verdad en Python usando **`rich`** (colores, tablas, barras de progreso, spinners) y **`pyfiglet`** (banner). No hace falta backend web: todo corre en la terminal real del usuario, así que "parece bash" porque **es** una terminal.

**`ui/boot.py`** — se ejecuta la primera vez que se instala (o con `diagnosqui --setup`):
- Usa `rich.progress` para mostrar una barra estilo "resolviendo dependencias…", "descargando driver-scan@2.1.0…", etc., simulando el log de `npm install`, mientras en paralelo (de verdad) valida que `psutil`, `wmi` (si Windows) y demás estén instalados.
- Al terminar imprime `added N packages in X.Xs` y luego el banner de `pyfiglet` con "DiagnosQui".

**`ui/terminal.py`** — el shell interactivo real:
- Prompt persistente `➜` con `rich.prompt` o `prompt_toolkit` (recomendado `prompt_toolkit` porque da historial con flechas, autocompletado de comandos y edición de línea real, tal como bash).
- Comandos: `sistema`, `cpu`, `memoria`, `discos`, `red`, `usb`, `pci`, `controladores`, `problemas`, `monitor`, `io`, `reporte`, `help`, `clear`, `salir` — mapeando 1 a 1 con el menú numérico original (se puede aceptar ambos: número o nombre).
- Colores: verde/cian para OK, amarillo para advertencia, rojo para crítico (misma lógica que la demo).

**`ui/theme.py`** — paleta única reutilizada en toda la app (para que se vea consistente, no cada módulo con su propio color suelto).

---

## 4. Multiplataforma: cómo se resuelve Windows vs Linux

`core/platform_utils.py` detecta el SO con `platform.system()` y cada módulo de `core/` delega en el backend correcto:

| Módulo (`core/`) | Backend Windows | Backend Linux |
|---|---|---|
| `sistema.py` | `platform`, `systeminfo` | `platform`, `/etc/os-release`, `uname -a` |
| `cpu.py` | `psutil.cpu_percent()`, `platform.processor()` | `psutil.cpu_percent()`, `/proc/cpuinfo` |
| `memoria.py` | `psutil.virtual_memory()` | `psutil.virtual_memory()` |
| `discos.py` | `psutil.disk_usage("C:\\")`, `Get-PhysicalDisk`, `Get-Disk` | `psutil.disk_usage("/")`, `lsblk -o NAME,TYPE,SIZE,MODEL` |
| `red.py` | `Get-NetAdapter`, `psutil.net_if_stats()` | `psutil.net_if_addrs()`, `ip link`, `ethtool` |
| `usb.py` | `Get-PnpDevice -PresentOnly | Where InstanceId -like "USB*"` | `lsusb` |
| `pci.py` | `pnputil /enum-devices /connected /bus` | `lspci -mm` |
| `controladores.py` | `driverquery`, `Get-PnpDevice` | `lsmod`, `modinfo` |
| `problemas.py` | `Get-PnpDevice | Where Status -ne "OK"` | `dmesg --level=err,warn`, `journalctl -p 3` |
| `monitor.py` (GPU) | `Get-CimInstance Win32_VideoController` | `lspci | grep VGA`, `glxinfo` (si existe) |
| `io_monitor.py` | `psutil.disk_io_counters()` | `psutil.disk_io_counters()`, `iostat` |

Los comandos de PowerShell se ejecutan desde Python con:
```python
subprocess.run(["powershell", "-Command", "Get-PnpDevice -PresentOnly"], capture_output=True, text=True)
```
Y los de Linux equivalentes con `subprocess.run(["lspci", "-mm"], ...)`.

Cuando un comando requiere permisos (algunos `Get-PnpDevice` detallados, o `dmesg` en ciertas distros), el programa debe detectarlo, avisar en la terminal ("⚠ ejecuta como administrador/sudo para ver el detalle completo") y continuar con lo que sí pudo obtener — nunca debe romperse silenciosamente.

---

## 5. Empaquetado e instalación

### `pyproject.toml` (resumen)
```toml
[project]
name = "diagnosqui"
version = "2.4.1"
dependencies = [
  "psutil>=5.9",
  "rich>=13.0",
  "prompt_toolkit>=3.0",
  "pyfiglet>=1.0",
]

[project.optional-dependencies]
windows = ["wmi>=1.5"]

[project.scripts]
diagnosqui = "diagnosqui.cli:main"
```
El `entry_point` `diagnosqui = diagnosqui.cli:main` es lo que hace que, tras instalar el paquete, el comando `diagnosqui` quede disponible en la terminal como cualquier binario — igual que ocurre al instalar un paquete global de npm.

### Instalación en Linux (`install.sh`)
```bash
#!/usr/bin/env bash
set -e
echo "Instalando DiagnosQui…"
python3 -m venv ~/.diagnosqui-venv
source ~/.diagnosqui-venv/bin/activate
pip install --upgrade pip
pip install .
ln -sf ~/.diagnosqui-venv/bin/diagnosqui /usr/local/bin/diagnosqui
echo "Listo. Ejecuta: diagnosqui"
```

### Instalación en Windows (`install.ps1`)
```powershell
Write-Host "Instalando DiagnosQui..."
python -m venv $env:USERPROFILE\.diagnosqui-venv
& "$env:USERPROFILE\.diagnosqui-venv\Scripts\pip.exe" install --upgrade pip
& "$env:USERPROFILE\.diagnosqui-venv\Scripts\pip.exe" install .[windows]
Write-Host "Agrega esta ruta a tu PATH si no aparece el comando:"
Write-Host "$env:USERPROFILE\.diagnosqui-venv\Scripts"
Write-Host "Listo. Ejecuta: diagnosqui"
```

Ambos scripts imprimen su propio progreso (`rich`/mensajes) para que la instalación **real** ya se sienta como la demo: se ve igual, pero esta vez sí está instalando algo de verdad.

---

## 6. Módulo `reporte.py` — matriz de diagnóstico y caso final

`reporte.py` recopila lo que devolvieron `cpu.py`, `memoria.py`, `discos.py`, `usb.py`, `problemas.py`, `monitor.py` y arma:

1. **Tabla en terminal** (con `rich.table`) igual a la matriz del enunciado:

| Componente | Evidencia | Estado | Posible problema |
|---|---|---|---|
| CPU | 95% | ⚠ | Carga elevada |
| RAM | 92% | ⚠ | Poca memoria disponible |
| SSD | 45% | OK | — |
| USB | Error | ⚠ | Driver/configuración |
| GPU | Driver antiguo/error | ⚠ | Controlador |

2. **Exportación** a `.csv` y `.html` (opción "Generar reporte" del menú).
3. **Veredicto automático**: una función `diagnostico_final()` en `diagnostico/matriz.py` que, dado el caso del enunciado ("lenta, USB falla, apps gráficas con problemas"), cruza evidencias (CPU alto + USB con error + GPU con advertencia) y redacta la causa más probable con su justificación, para que el estudiante tenga un punto de partida y lo valide/corrija con sus propias pruebas.

---

## 7. Fases de desarrollo sugeridas (para dárselo a opencode en orden)

1. **Base funcional sin estilo**: implementar todos los módulos de `core/` + backends, probhappy con `print()` plano (que funcione en Windows y Linux primero).
2. **Terminal bash-like**: envolver el menú con `prompt_toolkit` + `rich`, prompt `➜`, colores por estado.
3. **Boot / instalación animada**: `ui/boot.py` con el log estilo `npm install`.
4. **Reporte y matriz de diagnóstico**: `reporte.py` + exportación CSV/HTML + `diagnostico_final()`.
5. **Empaquetado**: `pyproject.toml`, `install.sh`, `install.ps1`, probar instalación limpia en una VM de cada SO.
6. **Pulido**: manejo de errores de permisos, mensajes de "ejecuta como admin/sudo", pruebas en `tests/`.

---

## 8. Dependencias por plataforma

`requirements.txt` (comunes):
```
psutil>=5.9
rich>=13.0
prompt_toolkit>=3.0
pyfiglet>=1.0
```

Solo Windows (`requirements-windows.txt` o extra `[windows]` en `pyproject.toml`):
```
wmi>=1.5
pywin32>=306
```

---

## 9. Nota sobre permisos

Varios comandos (`Get-PnpDevice` detallado, `dmesg`, algunos `lspci -v`) requieren privilegios elevados. El plan es que el programa **nunca falle en seco**: si un comando devuelve error de permisos, se captura, se marca esa fila como "sin datos (requiere admin/sudo)" en la matriz, y se sigue con el resto del diagnóstico.
