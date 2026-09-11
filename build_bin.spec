# -*- mode: python ; coding: utf-8 -*-
"""Especificación PyInstaller para Linux.

Genera dos binarios ELF (onefile):
    - dist/diagnosqui              terminal.
    - dist/diagnosqui-gui          escritorio PySide6.

Uso (desde la raíz del proyecto, con PyInstaller instalado):
    pyinstaller --clean --noconfirm build_bin.spec
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
    cipher=None,
    noarchive=False,
)
cli_pyz = PYZ(cli_a.pure)
cli_exe = EXE(
    cli_pyz,
    cli_a.scripts,
    [],
    exclude_binaries=False,
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
    cipher=None,
    noarchive=False,
)
gui_pyz = PYZ(gui_a.pure)
gui_exe = EXE(
    gui_pyz,
    gui_a.scripts,
    [],
    exclude_binaries=False,
    name="diagnosqui-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    icon=icono,
)