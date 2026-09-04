"""
Módulo para generación de la matriz de diagnóstico, veredicto y exportación a CSV y HTML.
"""
import csv
import os
import datetime
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from diagnosqui.core.platform_utils import get_backend
from diagnosqui.diagnostico.matriz import build_diagnostic_matrix, diagnostico_final
from diagnosqui.ui.theme import console, print_header, print_status_badge


def generate_csv_report(matrix: list, verdict: dict, filename: str = "reporte_diagnosqui.csv") -> str:
    """Exporta los hallazgos y matriz de diagnóstico a formato CSV."""
    filepath = os.path.abspath(filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Componente", "Evidencia", "Estado", "Posible Problema"])
        for row in matrix:
            writer.writerow([row["componente"], row["evidencia"], row["estado"], row["problema"]])
        writer.writerow([])
        writer.writerow(["--- Veredicto Final ---"])
        for i, c in enumerate(verdict["causas"], 1):
            writer.writerow([f"Causa {i}", c])
    return filepath


def generate_html_report(matrix: list, verdict: dict, sys_info: dict, filename: str = "reporte_diagnosqui.html") -> str:
    """Genera un reporte HTML moderno, interactivo y con estilo profesional."""
    filepath = os.path.abspath(filename)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Armar filas de la tabla
    rows_html = ""
    for r in matrix:
        status_color = "#22c55e" if r["estado"] == "OK" else ("#eab308" if r["estado"] == "ALERTA" else "#ef4444")
        rows_html += f"""
        <tr>
            <td><strong>{r['componente']}</strong></td>
            <td>{r['evidencia']}</td>
            <td><span class="badge" style="background-color: {status_color};">{r['estado']}</span></td>
            <td>{r['problema']}</td>
        </tr>
        """

    causas_html = "".join(f"<li><strong>{c}</strong></li>" for c in verdict["causas"])
    justificaciones_html = "".join(f"<p>{j}</p>" for j in verdict["justificaciones"])
    recomendaciones_html = "".join(f"<li>{rec}</li>" for rec in verdict["recomendaciones"])

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Diagnóstico — DiagnosQui</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --border: #334155;
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 2rem;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{
            margin: 0;
            color: var(--accent);
            font-size: 2rem;
            letter-spacing: -0.5px;
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: bold;
            color: #000;
        }}
        .card {{
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }}
        .card h2 {{
            margin-top: 0;
            color: var(--accent);
            font-size: 1.3rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background-color: rgba(0, 0, 0, 0.2);
            color: var(--muted);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
        }}
        ul {{
            padding-left: 1.5rem;
        }}
        li {{
            margin-bottom: 0.5rem;
        }}
        .footer {{
            text-align: center;
            color: var(--muted);
            font-size: 0.85rem;
            margin-top: 3rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>DiagnosQui ⚡ Reporte de Hardware</h1>
                <p style="margin: 0.25rem 0 0; color: var(--muted);">Auditoría de buses, controladores y diagnóstico integrado</p>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 0.9rem; color: var(--muted);">{now_str}</span><br>
                <strong>{sys_info.get('hostname', 'Host')}</strong>
            </div>
        </div>

        <div class="card">
            <h2>Información del Entorno Auditado</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div><span style="color: var(--muted);">Sistema Operativo:</span><br><strong>{sys_info.get('os')}</strong></div>
                <div><span style="color: var(--muted);">Procesador:</span><br><strong>{sys_info.get('processor')}</strong></div>
                <div><span style="color: var(--muted);">Tiempo de Actividad:</span><br><strong>{sys_info.get('uptime')}</strong></div>
                <div><span style="color: var(--muted);">Arquitectura:</span><br><strong>{sys_info.get('architecture')}</strong></div>
            </div>
        </div>

        <div class="card">
            <h2>Matriz de Diagnóstico de Componentes</h2>
            <table>
                <thead>
                    <tr>
                        <th>Componente</th>
                        <th>Evidencia Detectada</th>
                        <th>Estado</th>
                        <th>Posible Problema</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>Diagnóstico y Veredicto Final</h2>
            <h3 style="color: #cbd5e1; margin-bottom: 0.5rem;">Causas más probables:</h3>
            <ul>
                {causas_html}
            </ul>

            <h3 style="color: #cbd5e1; margin-top: 1.5rem; margin-bottom: 0.5rem;">Justificación Técnica:</h3>
            <div style="color: #cbd5e1;">
                {justificaciones_html}
            </div>

            <h3 style="color: #cbd5e1; margin-top: 1.5rem; margin-bottom: 0.5rem;">Recomendaciones de Mitigación:</h3>
            <ul>
                {recomendaciones_html}
            </ul>
        </div>

        <div class="footer">
            Generado automáticamente por DiagnosQui v2.4.1 • Paquete de Diagnóstico Multiplataforma
        </div>
    </div>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filepath


def show_reporte(export_files: bool = True):
    """Muestra la matriz de diagnóstico, el veredicto y genera los archivos de reporte."""
    print_header("Reporte y Matriz de Diagnóstico", "Módulo 12 / Matriz & Veredicto")

    backend = get_backend()
    sys_info = backend.get_system_info()
    matrix = build_diagnostic_matrix(backend)
    verdict = diagnostico_final(matrix)

    # 1. Tabla de Matriz en Terminal
    table = Table(title="[bold white]MATRIZ DE DIAGNÓSTICO DE COMPONENTES[/bold white]", border_style="cyan")
    table.add_column("Componente", style="bold white", width=18)
    table.add_column("Evidencia", style="white", width=28)
    table.add_column("Estado", justify="center", width=12)
    table.add_column("Posible Problema", style="cyan", width=38)

    for row in matrix:
        badge = print_status_badge(row["estado"])
        table.add_row(
            row["componente"],
            row["evidencia"],
            badge,
            row["problema"]
        )

    console.print(table)
    console.print()

    # 2. Veredicto Final
    verdict_title = "[bold green]DIAGNÓSTICO FINAL: SISTEMA EN PARÁMETROS NORMALES[/bold green]" if verdict["is_healthy"] else "[bold red]DIAGNÓSTICO FINAL: ANOMALÍAS DETECTADAS[/bold red]"
    box_border = "green" if verdict["is_healthy"] else "red"

    verdict_text = Text()
    verdict_text.append("Causas más probables:\n", style="bold white")
    for i, causa in enumerate(verdict["causas"], 1):
        verdict_text.append(f"  {i}. {causa}\n", style="yellow" if not verdict["is_healthy"] else "green")

    verdict_text.append("\nJustificación Técnica:\n", style="bold white")
    for j in verdict["justificaciones"]:
        verdict_text.append(f"  * {j}\n", style="muted")

    verdict_text.append("\nRecomendaciones:\n", style="bold white")
    for r in verdict["recomendaciones"]:
        verdict_text.append(f"  -> {r}\n", style="cyan")

    console.print(Panel(verdict_text, title=verdict_title, border_style=box_border, padding=(1, 2)))

    # 3. Exportación
    if export_files:
        console.print()
        csv_path = generate_csv_report(matrix, verdict)
        html_path = generate_html_report(matrix, verdict, sys_info)
        console.print(f"[green][OK][/green] Reporte CSV exportado en:  [bold white]{csv_path}[/bold white]")
        console.print(f"[green][OK][/green] Reporte HTML exportado en: [bold white]{html_path}[/bold white]")
