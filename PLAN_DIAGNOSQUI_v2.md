# Plan v2 — DiagnosQui / Hardware Diagnostic & Repair Assistant
### Fusión del proyecto integrador IS-321 con lo ya encaminado en DiagnosQui

Este plan **actualiza y reemplaza en alcance** al `PLAN_DIAGNOSQUI.md` inicial. No se empieza de cero: se toma la arquitectura ya definida (terminal estilo bash, instalación estilo npm, backends Windows/Linux) y se le integran los requisitos del proyecto académico IS-321, la referencia visual del **Task Manager de Windows**, y el nuevo módulo de **optimización de Windows**.

---

## 1. Qué se fusiona

| Ya existía (DiagnosQui) | Se agrega ahora (IS-321) |
|---|---|
| Terminal estilo bash, boot tipo `npm install` | Menú y nombres de módulo del enunciado (`Hardware Diagnostic & Repair Assistant`) |
| Backends Windows/Linux (`platform_utils.py`) | Motor de reglas + motor de recomendaciones explícito |
| Módulos: cpu, memoria, discos, red, usb, pci, controladores, problemas, monitor | Casos integradores (5), diagnóstico de conectividad, diagnóstico general con semáforo |
| Reporte CSV/HTML | Reporte `.txt` / `.json` con el formato exacto pedido |
| — | **Módulo de optimización de Windows** (temporales + telemetría) |
| — | Interfaz tipo **Task Manager** (gráficas en vivo, tabla de procesos) |
| — | Empaquetado con **PyInstaller** (.exe / binario Linux) |

El nombre visible del producto sigue siendo **DiagnosQui**; internamente se documenta como implementación del proyecto "Hardware Diagnostic & Repair Assistant" para efectos de la entrega académica.

---

## 2. Referencia de interfaz: Task Manager de Windows

Se toman tres ideas concretas del Administrador de tareas, no un clon completo:

1. **Pestaña de Procesos** → tabla ordenable (por CPU %, memoria, nombre) que se actualiza cada segundo.
2. **Pestaña de Rendimiento** → gráficas en tiempo real tipo sparkline para CPU, memoria, disco y red (una gráfica por recurso, con el valor actual grande arriba, igual que Task Manager).
3. **Código de color por severidad**, igual que Task Manager resalta en amarillo/rojo el uso alto: verde = normal, amarillo = advertencia, rojo = crítico — reutilizando los mismos umbrales del enunciado (CPU 0-70/71-89/90-100, RAM <70/70-89/≥90).

### Cambio de librería recomendado
`rich` + `prompt_toolkit` alcanzan para el menú y los reportes estáticos, pero **no dibujan gráficas en vivo que se actualizan solas**. Para lograr el look de Task Manager real se agrega:

- **`textual`** (mismo autor que `rich`, framework de TUI): da paneles con auto-refresh, tablas interactivas, y widgets de gráfica (`Sparkline`, `PlotextPlot` vía el paquete `textual-plotext`) sin salir de la terminal.

Uso dentro del proyecto:
- `ui/boot.py` y el menú de texto plano → siguen con `rich`/`prompt_toolkit` (rápido, ya funciona).
- **Nueva pantalla `12. Monitorización del sistema`** → se abre como una app `textual` aparte, con tabs "Procesos" y "Rendimiento", actualizándose cada 1s con `psutil`, y se sale con `q` o `Esc` para volver al menú principal.

---

## 3. Estructura de carpetas (fusionada)

```
diagnosqui/
├── pyproject.toml
├── requirements.txt
├── install.sh                     # Linux/macOS
├── install.ps1                    # Windows
├── build_exe.spec                 # PyInstaller (Windows)
├── build_bin.spec                 # PyInstaller (Linux)
├── README.md
├── diagnosqui/
│   ├── cli.py                     # menú principal (rich/prompt_toolkit)
│   ├── ui/
│   │   ├── boot.py                # animación estilo npm install
│   │   ├── terminal.py            # prompt, colores, tablas de reporte
│   │   ├── theme.py
│   │   └── monitor_tui.py         # app Textual (estilo Task Manager)
│   ├── core/                      # un módulo por opción de menú
│   │   ├── platform_utils.py
│   │   ├── general.py             # "Diagnóstico general" (semáforo)
│   │   ├── cpu.py
│   │   ├── memoria.py
│   │   ├── pci.py
│   │   ├── red.py
│   │   ├── conectividad.py        # ping, dns, gateway (caso "sin internet")
│   │   ├── usb.py
│   │   ├── almacenamiento.py
│   │   ├── gpu.py
│   │   ├── controladores.py
│   │   ├── problemas.py
│   │   └── monitor.py             # alimenta a monitor_tui.py
│   ├── backends/
│   │   ├── windows_backend.py     # PowerShell/WMI/PnP
│   │   └── linux_backend.py       # lspci, lsusb, /proc, nmcli
│   ├── optimizacion/              # NUEVO — solo tiene efecto real en Windows
│   │   ├── temporales.py          # limpiar %TEMP%, C:\Windows\Temp, papelera
│   │   ├── telemetria.py          # servicios/tareas/registro de telemetría
│   │   └── safety.py              # confirmaciones, dry-run, backup, logging
│   ├── analisis/
│   │   ├── reglas.py              # analizar_estado(), umbrales
│   │   └── recomendaciones.py     # recomendacion_usb(), recomendacion_pci(), etc.
│   ├── reportes/
│   │   ├── exportador.py          # diagnostico.txt / diagnostico.json
│   │   └── plantillas.py
│   └── logs/
└── tests/
```

---

## 4. Menú principal actualizado (mapea 1 a 1 con el enunciado)

```
====================================================
      DIAGNOSQUI — HARDWARE DIAGNOSTIC & REPAIR
====================================================
 1. Diagnóstico general
 2. Diagnóstico CPU
 3. Diagnóstico memoria RAM
 4. Diagnóstico PCI / PCIe
 5. Diagnóstico de red
 6. Diagnóstico USB
 7. Diagnóstico de almacenamiento
 8. Diagnóstico GPU / vídeo
 9. Diagnóstico de controladores
10. Detectar dispositivos con problemas
11. Pruebas de conectividad
12. Monitorización del sistema (vista tipo Task Manager)
13. Recomendaciones de solución
14. Generar reporte
15. Exportar diagnóstico
16. Optimización de Windows (temporales / telemetría)   ← nuevo, solo visible en Windows
 0. Salir
```

---

## 5. Motor de diagnóstico (reglas + recomendaciones)

`analisis/reglas.py` centraliza la clasificación, igual que pide el enunciado:

```python
def analizar_estado(valor, tipo="porcentaje"):
    if tipo == "porcentaje":
        if valor < 70:
            return "NORMAL"
        elif valor < 90:
            return "ADVERTENCIA"
        return "CRITICO"
    # estado (OK/Warning/Error) para PnP, drivers, etc.
    if valor == "OK":
        return "NORMAL"
    elif valor in ("Warning", "Unknown"):
        return "ADVERTENCIA"
    return "CRITICO"
```

`analisis/recomendaciones.py` — una función por dominio (`recomendacion_cpu`, `recomendacion_usb`, `recomendacion_pci`, `recomendacion_red`, `recomendacion_gpu`, `recomendacion_disco`), cada una devuelve texto + lista de "revisar esto" siguiendo el patrón del enunciado (DETECCIÓN → DIAGNÓSTICO → SOLUCIÓN, nunca certeza absoluta con datos insuficientes).

**Regla obligatoria del enunciado (sección 45)** se implementa como un flag en cada resultado:
```python
resultado = {
  "componente": "GPU",
  "deteccion": "OK",
  "diagnostico": "Sin anomalías en indicadores básicos",
  "certeza": "baja",       # nunca "sistema sin problemas" cuando el reporte del usuario diga lo contrario
  "recomendacion": [...]
}
```
Esto es lo que resuelve directamente el **Caso integrador 5** (diagnóstico ambiguo): si el usuario reporta un síntoma pero los indicadores están OK, el programa no debe declarar "todo bien", sino "sin anomalías en indicadores básicos, se requiere diagnóstico adicional" + sugerencias (temperatura, fuente de poder, drivers, eventos del sistema).

---

## 6. Casos integradores → cómo los resuelve el motor

| Caso | Entrada | Salida esperada del motor |
|---|---|---|
| 1 — Sin red | IP 169.254.x.x, gateway no disponible | `conectividad.py` detecta rango APIPA → "posible fallo de DHCP", recomienda `ipconfig /release` / `/renew` **solo mostrando el comando**, no ejecutándolo sin confirmación |
| 2 — PCIe tarjeta de red | Adaptador PCIe = ERROR, resto OK | `pci.py` aísla el problema a un dispositivo puntual, no reporta falla general del sistema |
| 3 — USB no reconocido | Controlador OK, dispositivo ERROR, disco no aparece | `usb.py` sigue el árbol de decisión del enunciado (conexión → controlador → disco) |
| 4 — Alto consumo | CPU 97%, RAM 91% | `general.py` marca CRÍTICO en ambos y `recomendaciones.py` sugiere revisar procesos activos (usa la tabla del monitor tipo Task Manager para señalar cuáles) |
| 5 — Ambiguo | Todo OK pero hay síntoma reportado por el usuario | Ver regla de "certeza baja" arriba |

En todos los casos donde el enunciado dice explícitamente *"No debe ejecutar comandos de modificación automáticamente sin solicitar autorización"*, el programa **solo imprime el comando sugerido** y pide `s/n` antes de correr cualquier cosa que cambie algo (esto también aplica al módulo de optimización, sección 8).

---

## 7. Multiplataforma (el enunciado pide solo Windows; se extiende a Linux)

Se mantiene la tabla de equivalencias ya definida en el plan v1 (PowerShell ↔ `lspci`/`lsusb`/`/proc`). Lo nuevo:

- **Conectividad** (`conectividad.py`): `ping`, `nslookup`/`Resolve-DnsName`, `arp -a` en Windows ↔ `ping`, `dig`/`getent hosts`, `ip neigh` en Linux.
- **Monitor tipo Task Manager**: `psutil` es igual en ambos SO, así que la pantalla `textual` (sección 2) funciona sin cambios en Windows y Linux; solo la tabla de "procesos con nombre de servicio" difiere un poco en formato.
- **Módulo de optimización (sección 8)**: es **exclusivo de Windows** (temp de Windows y telemetría de Windows no existen igual en Linux). En Linux la opción 16 del menú se reemplaza automáticamente por un aviso: "Optimización disponible solo en Windows" o, si se quiere aprovechar, por un equivalente simple de limpieza (`/tmp`, cache de paquetes) — opcional, no es parte del alcance del enunciado.

---

## 8. Módulo de optimización de Windows (nuevo)

Reglas de seguridad para **todo** este módulo (no negociables en el diseño):

1. Nunca se ejecuta nada automáticamente al iniciar el programa — solo desde el menú `16`, y solo tras una confirmación explícita `s/n` por cada acción.
2. Se requiere ejecutar como Administrador; si no lo está, se avisa y no se intenta la limpieza/cambio.
3. Antes de borrar o cambiar algo, se muestra **qué se va a hacer** (lista de archivos, tamaño total, o claves/servicios afectados) y se ofrece un modo `--dry-run` que solo simula.
4. Se guarda un log (`logs/optimizacion.log`) con fecha, acción y resultado — auditable.
5. Los cambios de telemetría deben ser **reversibles** (documentar cómo revertir cada uno).

### 8.1 Limpieza de temporales (`optimizacion/temporales.py`)

Ubicaciones a limpiar:
- `%TEMP%` del usuario (`C:\Users\<usuario>\AppData\Local\Temp`)
- `C:\Windows\Temp`
- Caché de Windows Update opcional (`C:\Windows\SoftwareDistribution\Download`)
- Papelera de reciclaje (opcional, con confirmación aparte porque borra datos del usuario, no basura del sistema)

Flujo:
```python
def escanear_temporales():
    rutas = [os.environ.get("TEMP"), r"C:\Windows\Temp"]
    archivos = []
    for ruta in rutas:
        for raiz, _, nombres in os.walk(ruta):
            for n in nombres:
                p = os.path.join(raiz, n)
                try:
                    archivos.append((p, os.path.getsize(p)))
                except OSError:
                    pass  # archivo en uso, se omite
    return archivos

def limpiar_temporales(archivos, dry_run=True):
    total = 0
    for ruta, tam in archivos:
        if not dry_run:
            try:
                os.remove(ruta)
            except OSError:
                continue  # en uso o sin permiso: se omite, no se fuerza
        total += tam
    return total  # bytes liberados (o que se liberarían en dry-run)
```
La UI muestra: `Se encontraron 1,204 archivos (2.3 GB). ¿Eliminar? (s/n)` antes de llamar con `dry_run=False`.

### 8.2 Deshabilitar telemetría (`optimizacion/telemetria.py`)

Se documentan y automatizan **solo los mecanismos oficiales/reversibles** de Windows (nada de hacks de terceros ni edición de binarios del sistema):

- **Nivel de telemetría vía directiva/registro** (equivalente a lo que hace el panel de Configuración → Privacidad → Diagnóstico y comentarios):
  ```powershell
  Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -Name "AllowTelemetry" -Value 0
  ```
  (0 = Security/Basic según edición; se documenta la diferencia Home/Pro porque en Home el mínimo suele ser 1).

- **Deshabilitar tareas programadas de telemetría conocidas** (built-in, documentadas por Microsoft), por ejemplo:
  ```powershell
  Disable-ScheduledTask -TaskName "Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser"
  Disable-ScheduledTask -TaskName "Microsoft\Windows\Customer Experience Improvement Program\Consolidator"
  ```

- **Detener/deshabilitar el servicio de telemetría conectada** (`DiagTrack`), reversible con `Set-Service -StartupType Manual`:
  ```powershell
  Stop-Service "DiagTrack" -Force
  Set-Service "DiagTrack" -StartupType Disabled
  ```

Cada función en `telemetria.py` debe tener su contraparte `revertir_*()` que vuelve al valor por defecto, y el programa debe imprimir antes de aplicar cualquier cambio una tabla tipo:

```
ACCIÓN                                   ESTADO ACTUAL   ESTADO PROPUESTO
AllowTelemetry (registro)                1 (Básico)      0 (Seguridad)
Tarea: Compatibility Appraiser           Habilitada      Deshabilitada
Servicio: DiagTrack                      Automático      Deshabilitado
```
y pedir confirmación antes de tocar cada fila (o "aplicar todo" con una sola confirmación explícita).

> Nota para el informe académico: este módulo debe documentarse igual que los demás (qué hace, por qué, limitaciones) y aclarar que **no elimina toda telemetría de Windows** (algunos componentes de seguridad no son configurables) y que debe usarse únicamente en equipos propios o con autorización expresa del dueño del equipo — igual que ya aplica para el resto del programa.

---

## 9. Empaquetado como ejecutable (PyInstaller)

Cumple la sección 29 del enunciado, sobre ambos SO:

```bash
# Windows -> genera HardwareDiagnostic.exe (o diagnosqui.exe)
pyinstaller --onefile --name diagnosqui --icon assets/icon.ico diagnosqui/cli.py

# Linux -> genera binario ELF diagnosqui
pyinstaller --onefile --name diagnosqui diagnosqui/cli.py
```

Esto convive con la instalación estilo npm ya definida: `install.ps1`/`install.sh` pueden, en vez de (o además de) crear un venv con `pip install .`, copiar el `.exe`/binario generado a una carpeta en el `PATH`, manteniendo la misma animación de "instalación" ya prototipada.

En el README se debe explicar (pide el enunciado, sección 29) la diferencia entre correr `python cli.py` (.py, necesita intérprete) y correr el `.exe`/binario generado (ya trae el intérprete y las dependencias empaquetadas).

---

## 10. Reporte automático (`reportes/exportador.py`)

Formato exacto pedido en la sección 30, generado en `.txt` y `.json`:

```json
{
  "fecha": "2026-09-04T10:30:00",
  "equipo": "DESKTOP-XXXX",
  "usuario": "juan",
  "sistema_operativo": "Windows 11 Pro",
  "cpu": {"modelo": "...", "uso_pct": 42, "estado": "NORMAL"},
  "ram": {"total_gb": 16, "uso_pct": 55, "estado": "NORMAL"},
  "pci": [...],
  "usb": [...],
  "red": {...},
  "gpu": {...},
  "almacenamiento": [...],
  "controladores": [...],
  "errores_detectados": [...],
  "recomendaciones": [...],
  "resultado_final": "Se encontraron 2 posibles problemas."
}
```

---

## 11. Fases de desarrollo actualizadas

1. **Consolidar `core/`**: renombrar/ajustar módulos del plan v1 a los nombres del enunciado (`almacenamiento.py`, `gpu.py`, `conectividad.py` nuevos).
2. **Motor de reglas + recomendaciones**: `analisis/reglas.py` y `analisis/recomendaciones.py`, y resolver los 5 casos integradores como pruebas (`tests/test_casos_integradores.py`).
3. **Monitor tipo Task Manager**: pantalla `textual` con tabs Procesos/Rendimiento (sección 2).
4. **Módulo de optimización de Windows**: temporales primero (menos riesgo), telemetría después, ambos con dry-run + confirmación + logging.
5. **Reporte**: exportador `.txt`/`.json` con el formato exacto.
6. **Empaquetado**: PyInstaller en Windows y Linux, integrarlo a los scripts de instalación estilo npm.
7. **Documentación**: README (sección 42) + informe PDF APA 7 (sección 38) — esto es aparte del código, pero se puede generar la plantilla en Markdown primero.

---

## 12. Checklist rápido contra la rúbrica (25 pts)

| Criterio rúbrica | Dónde se cubre en este plan |
|---|---|
| Investigación bibliotecas (2) | `psutil`, `subprocess`, `platform`, `rich`, `textual` — documentar cada una en README |
| Menú (2) | Sección 4 |
| CPU/RAM (2) | `core/cpu.py`, `core/memoria.py` + reglas |
| Almacenamiento (2) | `core/almacenamiento.py` |
| USB/periféricos (3) | `core/usb.py` + caso integrador 3 |
| PCI/PCIe (3) | `core/pci.py` + caso integrador 2 |
| Red (3) | `core/red.py` + `core/conectividad.py` + caso integrador 1 |
| GPU/controladores (2) | `core/gpu.py`, `core/controladores.py` |
| Motor de análisis/recomendaciones (2) | Sección 5 |
| Reportes (1) | Sección 10 |
| Ejecutable (1) | Sección 9 |
| Documentación APA 7 (1) | Fuera del código, plantilla aparte |
| Presentación (1) | Demo en vivo usando el menú + monitor tipo Task Manager |
