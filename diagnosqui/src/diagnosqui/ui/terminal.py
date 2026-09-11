"""Shell Bash y resultados, independientes de los módulos de diagnóstico real.

``fixture_provider(command)`` es el punto de conexión con los módulos del equipo:
debe devolver un resultado o una lista de resultados con el contrato de FIXTURES.
"""
from __future__ import annotations

import csv
import io
import json
import os
import platform
import sys
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
from html import escape
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.styles import Style as PromptStyle
from rich.table import Table
from rich.text import Text

from diagnosqui.ui.theme import (
    BACKGROUND_COLOR, MUTED_COLOR, NORMAL_COLOR, PRIMARY_COLOR, TEXT_COLOR,
    CRITICAL_STYLE, MUTED_STYLE, NORMAL_STYLE, PRIMARY_STYLE, WARNING_STYLE,
    console, style_for_status,
)

# Metadatos compartidos con el menú: número estable, nombre visible.
COMMANDS_MAP = {
    "general": ("1", "Diagnóstico general"),
    "cpu": ("2", "Diagnóstico CPU"),
    "memoria": ("3", "Diagnóstico memoria RAM"),
    "pci": ("4", "Diagnóstico PCI / PCIe"),
    "red": ("5", "Diagnóstico de red"),
    "usb": ("6", "Diagnóstico USB"),
    "disco": ("7", "Diagnóstico de almacenamiento"),
    "gpu": ("8", "Diagnóstico GPU / vídeo"),
    "controladores": ("9", "Diagnóstico de controladores"),
    "problemas": ("10", "Detectar dispositivos con problemas"),
    "conectividad": ("11", "Pruebas de conectividad"),
    "monitor": ("12", "Monitorización del sistema"),
    "recomendaciones": ("13", "Recomendaciones de solución"),
    "reporte": ("14", "Generar reporte"),
    "exportar": ("15", "Exportar diagnóstico"),
    "optimizacion": ("16", "Optimización de Windows"),
    "salir": ("17", "Salir"),
}
_ALIASES = {number: name for name, (number, _) in COMMANDS_MAP.items()}
_ALIASES.update({
    "0": "salir", "exit": "salir", "quit": "salir", "q": "salir",
    "ayuda": "help", "?": "help", "cls": "clear", "sistema": "general",
    "discos": "disco", "optimización": "optimizacion",
})
_CONTROL_COMMANDS = ("help", "clear", "setup")


def _fixture(component, evidence, value, status, recommendation, **details):
    return {
        "componente": component,
        "evidencia": evidence,
        "valor_numerico": value,
        "estado": status,
        "detalle": {"fuente": "fixture", **details},
        "recomendacion": [recommendation],
    }


FIXTURES = {
    "cpu": _fixture("CPU", "42% de uso", 42, "NORMAL", "Mantener ventilación adecuada.", nucleos=8),
    "memoria": _fixture("Memoria RAM", "76% utilizado · 12,2 / 16 GB", 76, "ADVERTENCIA", "Cerrar aplicaciones que no se utilicen."),
    "pci": _fixture("PCI / PCIe", "4 dispositivos detectados", 4, "NORMAL", "No se requieren acciones."),
    "red": _fixture("Red", "Ethernet conectado · 1 Gbps", 12, "NORMAL", "Mantener el controlador actualizado."),
    "usb": _fixture("USB", "3 dispositivos reconocidos", 3, "NORMAL", "Expulsar las unidades antes de desconectarlas."),
    "disco": _fixture("Almacenamiento", "92% ocupado · 460 / 500 GB", 92, "CRITICO", "Liberar espacio después de respaldar los archivos."),
    "gpu": _fixture("GPU / vídeo", "28% de uso · 45 °C", 28, "NORMAL", "Mantener ventilación adecuada."),
    "controladores": _fixture("Controladores", "1 actualización pendiente (simulada)", 1, "ADVERTENCIA", "Consultar el controlador en la web del fabricante."),
    "problemas": _fixture("Dispositivos con problemas", "1 incidencia simulada: adaptador USB", 1, "ADVERTENCIA", "Revisar la conexión del adaptador USB."),
    "conectividad": _fixture("Conectividad", "Latencia simulada: 18 ms · 0% pérdida", 18, "NORMAL", "La conexión de ejemplo responde correctamente."),
    "optimizacion": _fixture("Optimización de Windows", "Vista de ejemplo; no se aplicaron cambios", 0, "NORMAL", "Revisar las aplicaciones de inicio antes de realizar cambios."),
}
DIAGNOSTIC_FIXTURES = FIXTURES


class ShellAction(Enum):
    CONTINUE = "continue"
    EXIT = "exit"
    ERROR = "error"


def resolve_command(raw: str):
    """Resuelve nombres y números sin ejecutar acciones ni consultar hardware."""
    name = raw.strip().casefold()
    name = _ALIASES.get(name, name)
    return name if name in COMMANDS_MAP or name in _CONTROL_COMMANDS else None


def get_fixture_results(command: str):
    """Devuelve copias independientes para no alterar el catálogo compartido."""
    command = resolve_command(command)
    if command in {"general", "reporte", "exportar", "recomendaciones"}:
        results = [value for name, value in FIXTURES.items() if name != "optimizacion"]
    elif command in FIXTURES:
        results = [FIXTURES[command]]
    else:
        raise ValueError(f"No hay datos de prueba para {command!r}")
    return deepcopy(results)


def _as_results(results):
    return [results] if isinstance(results, Mapping) else list(results)


def build_result_table(result):
    """Cada resultado es una tabla de una fila; el contenido nunca es markup."""
    table = Table(border_style=PRIMARY_COLOR, header_style=f"bold {PRIMARY_COLOR}", expand=True)
    table.add_column("Componente", ratio=2)
    table.add_column("Evidencia", ratio=3)
    table.add_column("Estado", ratio=2)
    table.add_column("Recomendación", ratio=4)
    recommendations = result.get("recomendacion") or []
    first = str(recommendations[0]).splitlines() if recommendations else []
    status = str(result.get("estado", ""))
    table.add_row(
        Text(str(result.get("componente", ""))),
        Text(str(result.get("evidencia", ""))),
        Text(status, style=style_for_status(status)),
        Text(first[0] if first else "—"),
    )
    return table


def state_directory(system_name=None):
    """Ubicación configurable de historial y marcador de primer arranque."""
    configured = os.environ.get("DIAGNOSQUI_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    if (system_name or platform.system()) == "Windows":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "DiagnosQui"
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "diagnosqui"


class _ResilientFileHistory(FileHistory):
    """La pérdida de acceso al archivo no interrumpe una sesión ya iniciada."""

    def load_history_strings(self):
        try:
            yield from super().load_history_strings()
        except OSError:
            return

    def store_string(self, string):
        try:
            super().store_string(string)
        except OSError:
            pass  # History conserva en memoria las entradas de esta sesión.


def _history(system_name=None):
    try:
        directory = state_directory(system_name)
        directory.mkdir(parents=True, exist_ok=True)
        history_file = directory / "history"
        history_file.touch(exist_ok=True)
        return _ResilientFileHistory(str(history_file))
    except OSError:
        return InMemoryHistory()


def command_completer(system_name=None):
    """El autocompletado usa los mismos números del menú para cada plataforma."""
    windows = (system_name or platform.system()) == "Windows"
    words = list(_CONTROL_COMMANDS) + ["0"]
    for name, (number, _) in COMMANDS_MAP.items():
        if name != "optimizacion" or windows:
            words.extend((name, number))
    return WordCompleter(words, ignore_case=True)


def print_help_menu(*, console_instance=None, system_name=None):
    output = console_instance or console
    windows = (system_name or platform.system()) == "Windows"
    table = Table(title="COMANDOS DISPONIBLES", border_style=PRIMARY_COLOR)
    table.add_column("Nº")
    table.add_column("Comando", style=PRIMARY_COLOR)
    table.add_column("Descripción")
    for command, (number, description) in COMMANDS_MAP.items():
        if command != "optimizacion" or windows:
            table.add_row(number, command, description)
    table.add_row("—", "help / clear / setup", "Ayuda / limpiar pantalla / animación de inicio")
    table.add_row("0", "salir", "También puedes salir con 17 o Ctrl-D")
    output.print(table)


def _report_content(results, file_format):
    if file_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    headers = ("componente", "evidencia", "valor_numerico", "estado", "detalle", "recomendacion")
    if file_format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(headers)
        for result in results:
            writer.writerow([
                json.dumps(result[field], ensure_ascii=False) if isinstance(result[field], (dict, list))
                else result[field]
                for field in headers
            ])
        return stream.getvalue()
    rows = []
    for result in results:
        cells = [result["componente"], result["evidencia"], result["estado"], "\n".join(result["recomendacion"])]
        rows.append("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in cells) + "</tr>")
    return (
        '<!doctype html><html lang="es"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>DiagnosQui — Reporte de prueba</title>'
        '<style>body{font-family:system-ui,sans-serif;margin:2rem;background:' + BACKGROUND_COLOR + ';color:' + TEXT_COLOR + '}'
        'table{border-collapse:collapse;width:100%}th,td{border:1px solid ' + MUTED_COLOR + ';padding:.75rem;'
        'text-align:left;white-space:pre-line}th{color:' + PRIMARY_COLOR + '}</style>'
        '<body><h1>DiagnosQui — Reporte de prueba</h1>'
        '<p>Datos simulados (fixtures); no representan un diagnóstico del equipo.</p>'
        '<table><thead><tr><th>Componente</th><th>Evidencia</th><th>Estado</th><th>Recomendación</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></body></html>\n'
    )


def export_fixture_report(results, directory=None, formats=("json",)):
    """Exporta fixtures sin sobrescribir reportes existentes; retorna sus rutas."""
    results = _as_results(results)
    if isinstance(formats, str):
        formats = (formats,)
    formats = tuple(dict.fromkeys(file_format.lower() for file_format in formats))
    if not formats or any(file_format not in {"json", "csv", "html"} for file_format in formats):
        raise ValueError("Formatos disponibles: json, csv, html")
    payloads = {file_format: _report_content(results, file_format) for file_format in formats}
    target = Path(directory) if directory is not None else Path.cwd() / "reportes"
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    exported = {}
    for file_format, payload in payloads.items():
        suffix = 0
        while True:
            name = f"diagnosqui-fixtures-{stamp}" + (f"-{suffix}" if suffix else "")
            path = target / f"{name}.{file_format}"
            try:
                with path.open("x", encoding="utf-8", newline="") as report:
                    report.write(payload)
                exported[file_format] = path
                break
            except FileExistsError:
                suffix += 1
    return exported


def dispatch_command(raw, *, console_instance=None, fixture_provider=None,
                     monitor_runner=None, optimization_runner=None,
                     system_name=None, menu_printer=None,
                     export_directory=None):
    """Despacha un comando; las funciones inyectables permiten integrar el core."""
    output = console_instance or console
    provider = fixture_provider or get_fixture_results
    system_name = system_name or platform.system()
    command = resolve_command(raw)

    def show_menu():
        if menu_printer is not None:
            menu_printer()
        else:
            print_help_menu(console_instance=output, system_name=system_name)

    if not raw.strip():
        return ShellAction.CONTINUE
    if command is None:
        output.print(Text(f"Comando no reconocido: {raw.strip()!r}. Escribe 'help' para ver el menú.", style=WARNING_STYLE))
        return ShellAction.ERROR
    if command == "salir":
        output.print("Sesión de DiagnosQui finalizada.", style=PRIMARY_STYLE)
        return ShellAction.EXIT
    if command in {"help", "clear"}:
        if command == "clear":
            output.clear()
        show_menu()
        return ShellAction.CONTINUE
    if command == "optimizacion" and system_name != "Windows":
        output.print("La optimización solo esta disponible en Windows.", style=WARNING_STYLE)
        return ShellAction.ERROR
    try:
        if command == "setup":
            from diagnosqui.ui.boot import run_boot_animation

            run_boot_animation()
            show_menu()
        elif command == "monitor":
            if monitor_runner is None:
                if not (sys.stdin.isatty() and sys.stdout.isatty()):
                    output.print("El monitor necesita una terminal interactiva.", style=WARNING_STYLE)
                    return ShellAction.ERROR
                from diagnosqui.ui.monitor_tui import run_monitor

                monitor_runner = run_monitor
            monitor_result = monitor_runner()
            show_menu()
            if monitor_result is False:
                return ShellAction.ERROR
        elif command == "optimizacion":
            if optimization_runner is None:
                from diagnosqui.optimizacion.menu_optimizacion import run_optimizacion

                optimization_runner = run_optimizacion
            optimization_result = optimization_runner(confirmar_fn=None, output=output)
            show_menu()
            if optimization_result is False:
                return ShellAction.ERROR
        else:
            results = _as_results(provider(command))
            output.print("Datos de prueba (fixtures) · No representan el hardware del equipo.", style=MUTED_STYLE)
            if command == "exportar":
                exported = export_fixture_report(results, export_directory)
                for path in exported.values():
                    output.print(Text(f"Diagnóstico de prueba exportado: {path}", style=NORMAL_STYLE))
            else:
                if command == "reporte":
                    output.rule("REPORTE DE DIAGNÓSTICO · DATOS DE PRUEBA", style=PRIMARY_COLOR)
                for result in results:
                    output.print(build_result_table(result))
                    if command == "recomendaciones":
                        for recommendation in result.get("recomendacion", []):
                            output.print(Text(f"  • {recommendation}"))
    except KeyboardInterrupt:
        output.print("Operación cancelada. Puedes escribir otro comando.", style=WARNING_STYLE)
        return ShellAction.CONTINUE
    except Exception as exc:
        output.print(Text(f"No se pudo completar '{command}': {exc}", style=CRITICAL_STYLE))
        return ShellAction.ERROR
    return ShellAction.CONTINUE


def run_interactive_shell(*, console_instance=None, fixture_provider=None,
                          monitor_runner=None, optimization_runner=None,
                          system_name=None, menu_printer=None,
                          export_directory=None):
    """Prompt con historial y Tab; acepta entradas redirigidas sin avisos TTY."""
    output = console_instance or console
    system_name = system_name or platform.system()
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    session = None
    if interactive:
        session = PromptSession(
            history=_history(system_name),
            completer=command_completer(system_name),
            complete_while_typing=False,
            style=PromptStyle.from_dict({
                "arrow": f"{NORMAL_COLOR} bold", "prompt": f"{PRIMARY_COLOR} bold",
                "host": MUTED_COLOR,
            }),
        )
        output.print("Escribe un comando o su número · Tab autocompleta · ↑/↓ historial · Ctrl-D sale.", style=MUTED_STYLE)
    prompt = FormattedText([
        ("class:arrow", "➜ "), ("class:prompt", "diagnosqui"), ("class:host", " $ "),
    ])
    while True:
        try:
            raw = session.prompt(prompt) if session is not None else input()
        except KeyboardInterrupt:
            output.print("\nLínea cancelada. Puedes escribir otro comando.", style=WARNING_STYLE)
            continue
        except EOFError:
            output.print("Sesión de DiagnosQui finalizada.", style=PRIMARY_STYLE)
            return ShellAction.EXIT
        action = dispatch_command(
            raw, console_instance=output, fixture_provider=fixture_provider,
            monitor_runner=monitor_runner, optimization_runner=optimization_runner,
            system_name=system_name,
            menu_printer=menu_printer, export_directory=export_directory,
        )
        if action is ShellAction.EXIT:
            return action
