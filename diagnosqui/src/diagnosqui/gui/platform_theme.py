"""Identidad visual del SO; no selecciona ni ejecuta backends de diagnóstico."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shlex
from typing import Mapping, Optional


@dataclass(frozen=True)
class PlatformIdentity:
    key: str
    label: str


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    """Lee los campos de os-release sin ejecutar ni interpretar código shell."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}
    values = {}
    for line in lines:
        key, separator, value = line.partition("=")
        if separator and key in {"ID", "NAME", "PRETTY_NAME"}:
            try:
                parts = shlex.split(value, comments=True)
                if parts:
                    values[key] = " ".join(parts)
            except ValueError:
                continue
    return values


def detect_platform(
    system: Optional[str] = None, release: Optional[Mapping[str, str]] = None
) -> PlatformIdentity:
    system = platform.system() if system is None else system
    if system == "Windows":
        return PlatformIdentity("windows", "Windows")
    if system == "Linux":
        values = read_os_release() if release is None else release
        distro = values.get("ID", "").strip().lower()
        if distro in {"ubuntu", "debian"}:
            return PlatformIdentity(distro, distro.capitalize())
        return PlatformIdentity("linux", "Linux")
    return PlatformIdentity("linux", system or "Sistema")
