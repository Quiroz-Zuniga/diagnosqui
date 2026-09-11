"""Exportación de contratos actuales reutilizando los generadores CSV y HTML."""

from __future__ import annotations
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


def export_diagnostic_results(
    results: list[dict[str, Any]],
    directory: str,
    formats: tuple[str, ...] = ("json", "csv", "html"),
) -> dict[str, str]:
    from diagnosqui.core.reporte import generate_csv_report, generate_html_report

    if not results:
        raise ValueError("No hay resultados para exportar.")
    if not formats or any(format not in {"json", "csv", "html"} for format in formats):
        raise ValueError("Formato no disponible. Elige JSON, CSV o HTML.")
    target = Path(directory).expanduser()
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    basename = f"diagnosqui-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}"
    sources = sorted(
        {str((result.get("detalle") or {}).get("fuente", "real")) for result in results}
    )
    source = ", ".join(sources)
    matrix = [
        {
            "componente": row.get("componente", "N/D"),
            "evidencia": row.get("evidencia", "N/D"),
            "estado": row.get("estado", "ADVERTENCIA"),
            "problema": " · ".join(row.get("recomendacion") or [])
            or "Sin recomendaciones del proveedor",
        }
        for row in results
    ]
    incidents = [row for row in matrix if row["estado"] != "NORMAL"]
    verdict = {
        "fuente": source,
        "is_healthy": not incidents,
        "causas": [f"{row['componente']}: {row['evidencia']}" for row in incidents]
        or ["Sin incidencias en los componentes consultados."],
        "justificaciones": [
            f"Fuente de los resultados: {source}. Diagnóstico ejecutado: {stamp}."
        ],
        "recomendaciones": list(
            dict.fromkeys(
                rec for row in results for rec in (row.get("recomendacion") or [])
            )
        ),
    }
    system = next(
        (
            dict(row.get("detalle") or {})
            for row in results
            if row.get("componente") == "Sistema"
        ),
        {},
    )
    system["fuente"] = source
    paths = {}
    for format in dict.fromkeys(formats):
        path = target / f"{basename}.{format}"
        if format == "json":
            with path.open("x", encoding="utf-8") as stream:
                json.dump(
                    {"fuente": source, "generado_en": stamp, "resultados": results},
                    stream,
                    ensure_ascii=False,
                    indent=2,
                )
        elif format == "csv":
            generate_csv_report(matrix, verdict, str(path))
        else:
            generate_html_report(matrix, verdict, system, str(path))
        paths[format] = str(path.resolve())
    return paths
