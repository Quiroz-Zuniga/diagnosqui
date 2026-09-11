# Informe académico (plantilla APA 7)

> Plantilla en Markdown lista para convertir a PDF. Sustituye los campos entre
> `⟨…⟩` por los datos reales del autor/institucion y elimina las notas entre
> corchetes.

---

## Portada

**Título:** DiagnosQui: herramienta multiplataforma de diagnóstico y monitoreo
de hardware con terminal interactiva, escritorio nativo y análisis orientado a
reglas

**Autor(es):** ⟨Nombre del estudiante⟩

**Institución:** ⟨Universidad / Facultad⟩

**Curso / Asignatura:** ⟨Asignatura⟩

**Docente:** ⟨Nombre del docente⟩

**Fecha:** ⟨Mes, año⟩

---

## Resumen

⟨100 a 250 palabras. Resumen estructurado: qué se construyó, cómo, y qué
resultados se verificaron.⟩ Este trabajo presenta **DiagnosQui**, un sistema
que diagnostica el hardware del equipo (CPU, memoria, almacenamiento, red,
USB, PCI/PCIe, GPU y controladores) en Windows y Linux mediante dos
interfaces independientes: un escritorio nativo en PySide6 con proveedores
reales y una terminal interactiva con menus Rich, monitor Textual y cohorte de
datos de prueba. El diagnóstico aplica un motor de reglas (umbrales 70/90 y
regla PnP) que produce estados y recomendaciones; un modulo de optimización de
Windows limpia temporales y revierte la telemetria con confirmacion y registro
auditable. La herramienta se empaqueta como ejecutable autocontenido con
PyInstaller.

**Palabras clave:** diagnóstico de hardware, PySide6, Rich, Textual,
telemetría, optimización, reglas.

---

## 1. Introducción

⟨Contexto, problema y motivación.⟩ Los equipos presentan fallas de hardware
que muchas veces pasan desapercibidas hasta volverse críticas. Diagnosticar
manualmente componentes, controladores y conectividad es lento y propenso a
error. Este proyecto propone una herramienta que centraliza lectura de
sistema, análisis por reglas y recomendaciones, en dos interfaces según el
contexto de uso: escritorio y terminal.

**Objetivo general:** ⟨...⟩

**Objetivos específicos:**
- Recolectar métricas reales de hardware mediante `psutil`, comandos del
  sistema y WMI/`wmi` en Windows.
- Clasificar cada componente (normal / advertencia / crítico) con un motor de
  reglas y generar recomendaciones por dominio.
- Ofrecer monitorización en vivo tipo administrador de tareas.
- Optimizar Windows de forma segura y reversible con confirmación y log.

---

## 2. Marco teórico y revisión de bibliotecas

| Biblioteca | Función en el proyecto | Fuente de consulta |
|---|---|---|
| `psutil` | CPU, RAM, discos, red y procesos | ⟨cita sitio oficial / docs⟩ |
| `subprocess` (stdlib) | Comandos del sistema: `driverquery`, `wmic`, `lsusb`, `lspci` | ⟨documentación de Python⟩ |
| `platform` | Identidad del sistema operativo | ⟨…⟩ |
| `PySide6` | Escritorio nativo, gráficas QPainter | ⟨…⟩ |
| `rich` | Tablas y menús de la terminal | ⟨…⟩ |
| `prompt_toolkit` | Historial y autocompletado del prompt | ⟨…⟩ |
| `textual` | Monitor tipo Task Manager en la terminal | ⟨…⟩ |
| `pywin32` / `wmi` | Proveedores reales de Windows (WMI/registro) | ⟨…⟩ |
| `PyInstaller` | Empaquetado como ejecutable | ⟨…⟩ |

---

## 3. Metodología

- **Lenguaje:** Python ≥ 3.9 (compatible Windows 10/11 y Linux).
- **Estrategia:** desarrollo por fases con integración continua (pruebas
  `unittest` por módulo y regresión). Ver `docs/PLAN_FASES_PENDIENTES.md` y
  los documentos `docs/avance-fase-{1,2,3,4}.md`.
- **Contrato de datos:** todo resultado conserva las claves
  `componente, evidencia, valor_numerico, estado, detalle, recomendacion`;
  estados `NORMAL | ADVERTENCIA | CRITICO`.
- **Reglas de análisis:** umbrales de porcentaje 70 (advertencia) y 90
  (crítico) y regla PnP (OK/Warning/Unknown/Error); certeza baja cuando hay
  síntoma reportado pero los indicadores medibles están bien.
- **Seguridad de la optimización:** nada automático, requiere Administrador,
  confirmación `s/n` por acción, modo `--dry-run`, reversión implementada y
  log auditable en `logs/optimizacion.log`.

---

## 4. Desarrollo e implementación

| Módulo | Responsabilidad |
|---|---|
| `core/` | Recolección real de cada componente (backends Windows/Linux) |
| `gui/` | Escritorio PySide6: páginas, navegación, gráficas, reportes |
| `cli.py` + `ui/` | Terminal: menús, fixtures, monitor Textual |
| `analisis/` | Motor de reglas (`reglas.py`), recomendaciones por dominio (`recomendaciones.py`) y semáforo (`general.py`) |
| `optimizacion/` | Temporales y telemetría reversibles, con confirmación y log |
| `build_*.spec` | Empaquetado PyInstaller (terminal y escritorio, Windows/Linux) |

**Importante (módulo de optimización):** el módulo **no elimina toda la
telemetría de Windows** (algunos componentes de seguridad no son configurables
por este medio). Debe utilizarse únicamente en equipos propios o con
autorización expresa del dueño del equipo, igual que el resto de las
funcionalidades del programa.

---

## 5. Resultados

- Suite de 99 pruebas automáticas en verde
  (`QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests`),
  incluyendo los 5 casos integradores del enunciado.
- Los cinco casos integradores resueltos: APIPA/red (1), PCIe con dispositivo
  error (2), USB no reconocido (3), alto consumo de CPU/RAM (4) y síntoma sin
  indicadores medibles (5, certeza baja).
- Monitorización en vivo de procesos y rendimiento en ambas interfaces.
- Optimización de Windows validada por mocks en Linux; recorrido real de
  verificación en Windows pendiente.
- Binarios autocontenidos definidos (`build_exe.spec`, `build_bin.spec`) y
  icono generado con stdlib (`tools/make_icon.py`).

---

## 6. Conclusiones y trabajo futuro

⟨...⟩ Se logra una herramienta modular con contratos estables entre
recolección, análisis, interfaz y reportes. Como trabajo futuro:
- Validar el recorrido real de optimización y empaquetado en un equipo
  Windows 10/11.
- Ampliar el motor de reglas con historial de mediciones y tendencias.
- Agregar pruebas de desempeño del empaquetado onefile.

---

## 7. Referencias (APA 7)

⟨Ejemplos — completar con las fuentes consultadas.⟩

- Psutil. (s. f.). *psutil documentation*. https://psutil.readthedocs.io/
- Qt for Python. (s. f.). *PySide6 documentation*. https://doc.qt.io/qtforpython/
- Rich. (s. f.). *Rich: Python library for rich text and beautiful formatting*. https://rich.readthedocs.io/
- Textual. (s. f.). *Textual documentation*. https://textual.textualize.io/
- PyInstaller. (s. f.). *PyInstaller manual*. https://pyinstaller.org/
- Prompt Toolkit. (s. f.). *prompt_toolkit*. https://python-prompt-toolkit.readthedocs.io/

---

## Anexos

- Anexo A: capturas del escritorio y del monitor — `docs/diagnosqui-desktop.png`, `docs/diagnosqui-monitor.png`.
- Anexo B: plan de fases y avances — `docs/PLAN_FASES_PENDIENTES.md`, `docs/avance-fase-*.md`.
- Anexo C: guía de empaquetado — `docs/empaquetado.md`.