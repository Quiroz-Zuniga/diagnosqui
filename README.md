# DiagnosQui ⚡

**Administrador y Diagnóstico de Hardware Multiplataforma (Windows & Linux)**

DiagnosQui es una herramienta en consola diseñada para inspeccionar, monitorizar y diagnosticar componentes de hardware (CPU, RAM, discos, red, USB, buses PCI/PCIe, controladores y GPU), evaluando anomalías y generando reportes estructurados en CSV y HTML con veredicto automático.
<img width="1588" height="752" alt="image" src="https://github.com/user-attachments/assets/98a1c074-b2c8-4e90-b6d9-ccf5f4c4f3a2" />


---

## 🚀 Características

- **Interfaz estilo Bash / CLI moderno**: Terminal enriquecida con `prompt_toolkit` y `rich` (prompt interactivo `➜`, historial, autocompletado y colores por estado).
- **Animación estilo npm install**: Secuencia visual de arranque y validación de subsistemas de hardware.
- **Soporte Multiplataforma**:
  - **Windows**: PowerShell, WMI/CIM, PnP (`Get-PnpDevice`), driverquery, Win32_VideoController.
  - **Linux**: `/proc`, `/sys`, `lspci`, `lsusb`, `ip link`, `lsmod`, `dmesg`.
- **Matriz de Diagnóstico Inteligente**: Cruce automático de métricas para detectar cuellos de botella (CPU saturada, memoria insuficiente, puertos USB fallando, drivers de GPU incompatibles).
- **Exportación de Reportes**: Generación automática de reportes ejecutivos en CSV y HTML moderno.

---

## 📦 Instalación

### Instalación Rápida

#### En Windows (PowerShell):
```powershell
.\install.ps1
```

#### En Linux (Bash):
```bash
chmod +x install.sh
./install.sh
```

### Instalación Manual con Pip

```bash
pip install -r requirements.txt
pip install -e .
```
En Windows, instala las dependencias adicionales:
```bash
pip install -r requirements-windows.txt
```

---

## 💻 Uso

Ejecuta el comando en tu terminal:
```bash
diagnosqui
```

Opciones disponibles:
- `diagnosqui --setup` : Ejecuta la animación estilo npm de inicialización y verificación de módulos.
- `diagnosqui --report` : Genera y muestra la matriz de diagnóstico de forma directa.
- `diagnosqui --export-html` : Genera el reporte HTML y CSV de inmediato.

### Comandos interactivos de la terminal

| Comando | Equivalente | Descripción |
|---|---|---|
| `sistema` | `1` | Información del SO, arquitectura, uptime |
| `cpu` | `2` | Frecuencia, uso por núcleo y carga total |
| `memoria` | `3` | RAM física, disponible, usada y swap |
| `discos` | `4` | Particiones, espacio libre/usado y discos físicos |
| `red` | `5` | Interfaces de red, IP, MAC y estadísticas I/O |
| `usb` | `6` | Dispositivos USB conectados y con problemas |
| `pci` | `7` | Dispositivos en bus PCI, PCIe y ACPI |
| `controladores` | `8` | Drivers del sistema y controladores firmados |
| `problemas` | `9` | Dispositivos con estado Error o Degraded |
| `monitor` | `10` | Tarjeta gráfica (GPU), VRAM y versión de driver |
| `io` | `11` | Monitor de Entrada/Salida de disco y red en tiempo real |
| `reporte` | `12` | Matriz de diagnóstico, veredicto y exportación (CSV/HTML) |
| `clear` | - | Limpiar pantalla |
| `help` | - | Mostrar ayuda de comandos |
| `salir` | `0` | Cerrar DiagnosQui |
