#!/usr/bin/env python3
"""Genera assets/icon.ico con la librería estándar (sin Pillow).

Diseño: fondo oscuro redondeado, barra diagonal teal (marca de DiagnosQui)
y punto verde. Escribe un ICO con imagen PNG comprimida (soportado por
Windows Vista+ y por PyInstaller --icon).
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

ANCHO = 256
FONDO = (10, 17, 24, 255)          # #0a1118
PRIMARIO = (52, 211, 200, 255)     # #34d3c8
NORMAL = (70, 227, 138, 255)       # #46e38a
MUTED = (128, 145, 155, 255)       # #80919b


def _en_rango(x: int, y: int) -> bool:
    """Máscara de esquinas redondeadas (radio 48 px)."""
    radio = 48
    if x < radio and y < radio:
        dx, dy = radio - x, radio - y
        return dx * dx + dy * dy <= radio * radio
    if x >= ANCHO - radio and y < radio:
        dx, dy = (ANCHO - 1 - x) - radio, radio - y
        return dx * dx + dy * dy <= radio * radio
    if x < radio and y >= ANCHO - radio:
        dx, dy = radio - x, (ANCHO - 1 - y) - radio
        return dx * dx + dy * dy <= radio * radio
    if x >= ANCHO - radio and y >= ANCHO - radio:
        dx, dy = (ANCHO - 1 - x) - radio, (ANCHO - 1 - y) - radio
        return dx * dx + dy * dy <= radio * radio
    return True


def _pixel(x: int, y: int) -> tuple:
    if not _en_rango(x, y):
        return (0, 0, 0, 0)
    # Barra diagonal principal: franja ancha teal cruzando la esquina.
    diagonal = abs((y - x) - 40) < 26
    borde = abs((y - x) - 40) < 31 and diagonal or abs((y - x) + (ANCHO // 3) - 40) < 6
    # Segundo trazo superior verde.
    trazo = (y < x + ANCHO // 3) and (_en_rango(x, y) and abs((y - x) - (ANCHO - 120)) < 20)
    punto = (x - 190) ** 2 + (y - 46) ** 2 <= 12 ** 2
    if punto:
        return NORMAL
    if abs((y - x) - 40) < 26:
        return PRIMARIO
    if trazo:
        return NORMAL
    if borde:
        return MUTED
    return FONDO


def _png_pixels() -> bytes:
    """Rows en orden de arriba a abajo, filtro 0 por fila (RGBA)."""
    filas = bytearray()
    for y in range(ANCHO):
        filas.append(0)
        for x in range(ANCHO):
            filas.extend(_pixel(x, y))
    return bytes(filas)


def _cr32(datos: bytes) -> int:
    return zlib.crc32(datos) & 0xFFFFFFFF


def _chunk(tipo: bytes, datos: bytes) -> bytes:
    cuerpo = tipo + datos
    return struct.pack(">I", len(datos)) + cuerpo + struct.pack(">I", _cr32(cuerpo))


def _png(datos_imagen: bytes) -> bytes:
    encabezado = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", ANCHO, ANCHO, 8, 6, 0, 0, 0)
    idat = zlib.compress(datos_imagen, 9)
    return encabezado + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def generar_ico(ruta: str) -> None:
    png = _png(_png_pixels())
    encabezado = struct.pack("<HHH", 0, 1, 1)
    entrada = struct.pack(
        "<BBBBHHII",
        0,      # ancho 256 (0 = 256)
        0,      # alto 256
        0,      # paleta
        0,      # reservado
        1,      # planos
        32,     # bits por píxel
        len(png),
        22,     # offset de los datos PNG
    )
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(encabezado + entrada + png)
    print(f"Generado: {destino.resolve()} ({destino.stat().st_size} bytes)")


if __name__ == "__main__":
    generar_ico(str(Path(__file__).resolve().parent.parent / "assets" / "icon.ico"))