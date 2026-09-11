# -*- mode: python ; coding: utf-8 -*-
"""Especificación PyInstaller para Windows.

Genera dos ejecutables onefile:
    - dist/diagnosqui.exe           terminal (consola).
    - dist/DiagnosQui-Escritorio.exe escritorio PySide6 (sin consola).

Uso (desde la raíz del proyecto, con PyInstaller instalado):
    pyinstaller --clean --noconfirm build_exe.spec
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SPECPATH = os.path.abspath(SPECPATH)  # directorio del .spec (raíz del repo)

datas = collect_data_files("diagnosqui.gui")
hiddenimports = collect_submodules("diagnosqui")
pathex = [os.path.join(SPECPATH, "diagnosqui", "src")]
icono = os.path.join(SPECPATH, "assets", "icon.ico")

# ------------------------------------------------------------------ Terminal
cli_a = Analysis(
    [os.path.join(SPECPATH, "diagnosqui", "src", "diagnosqui", "cli.py")],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
cli_pyz = PYZ(cli_a.pure)
cli_exe = EXE(
    cli_pyz,
    cli_a.scripts,
    [],
    exclude_binaries=True,
    name="diagnosqui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    icon=icono,
)

# ------------------------------------------------------------- Escritorio
gui_a = Analysis(
    [os.path.join(SPECPATH, "diagnosqui", "src", "diagnosqui", "gui_cli.py")],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
gui_pyz = PYZ(gui_a.pure)
gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    [],
    exclude_binaries=True,
    name="DiagnosQui-Escritorio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=icono,
)