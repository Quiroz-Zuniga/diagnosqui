"""Aplica un único tema a Qt, QSS y dibujos; escucha cambios del tema nativo."""

from __future__ import annotations
from pathlib import Path
from string import Template
from typing import Optional
from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication
from diagnosqui.gui.platform_theme import PlatformIdentity, detect_platform
from diagnosqui.gui.visual_tokens import VisualTokens, build_tokens

STYLESHEET = Path(__file__).parent / "styles" / "application.qss"


class ThemeManager(QObject):
    changed = Signal(object)

    def __init__(
        self, app: QApplication, identity: Optional[PlatformIdentity] = None
    ) -> None:
        super().__init__(app)
        self.app = app
        self.platform = identity or detect_platform()
        self.mode = "light"
        self.tokens = build_tokens(self.platform.key)
        self.template = Template(STYLESHEET.read_text(encoding="utf-8"))
        self.fonts = set(QFontDatabase.families())
        app.styleHints().colorSchemeChanged.connect(self._system_changed)

    def apply(self, mode: str = "light") -> None:
        self.mode = mode if mode in {"system", "light", "dark"} else "light"
        resolved = self.mode
        if resolved == "system":
            resolved = (
                "dark"
                if self.app.styleHints().colorScheme() == Qt.ColorScheme.Dark
                else "light"
            )
        self.tokens = build_tokens(self.platform.key, resolved)
        self.app.setProperty("platform", self.platform.key)
        self.app.setProperty("appearance", resolved)
        self.app.setPalette(self.palette(self.tokens))
        preferred = {
            "windows": "Segoe UI",
            "ubuntu": "Ubuntu",
            "debian": "Noto Sans",
            "linux": "Noto Sans",
        }.get(self.platform.key, "Noto Sans")
        family = next(
            (
                font
                for font in (preferred, "Noto Sans", "DejaVu Sans")
                if font in self.fonts
            ),
            self.app.font().family(),
        )
        self.app.setFont(QFont(family, 10))
        self.app.setStyleSheet(self.template.substitute(self.tokens.substitutions()))
        self.changed.emit(self.tokens)

    @Slot()
    def _system_changed(self) -> None:
        if self.mode == "system":
            self.apply("system")

    @staticmethod
    def palette(tokens: VisualTokens) -> QPalette:
        palette = QPalette()
        roles = {
            "Window": tokens.bg,
            "WindowText": tokens.text_primary,
            "Base": tokens.surface,
            "AlternateBase": tokens.bg,
            "Text": tokens.text_primary,
            "Button": tokens.surface,
            "ButtonText": tokens.text_primary,
            "Highlight": tokens.accent_soft,
            "HighlightedText": tokens.accent_ink,
            "ToolTipBase": tokens.surface,
            "ToolTipText": tokens.text_primary,
            "Link": tokens.accent_ink,
            "Light": tokens.surface,
            "Mid": tokens.border,
            "Dark": tokens.border,
            "PlaceholderText": tokens.text_secondary,
        }
        for role, color in roles.items():
            palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
        for role in (
            QPalette.ColorRole.Text,
            QPalette.ColorRole.ButtonText,
            QPalette.ColorRole.WindowText,
        ):
            palette.setColor(
                QPalette.ColorGroup.Disabled, role, QColor(tokens.text_secondary)
            )
        return palette
