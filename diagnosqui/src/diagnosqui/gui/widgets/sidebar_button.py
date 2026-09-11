"""Botón lateral con icono Qt y etiqueta accesible incluso al contraerse."""

from __future__ import annotations
from PySide6.QtCore import QSize, Slot
from PySide6.QtWidgets import QApplication, QPushButton
from diagnosqui.gui.widgets.icons import icon


class SidebarButton(QPushButton):
    def __init__(self, title: str, icon_name: str) -> None:
        super().__init__(title)
        self.title = title
        self.icon_name = icon_name
        self.refresh_theme()
        self.setIconSize(QSize(18, 18))
        self.setCheckable(True)
        self.setProperty("role", "nav")
        self.setMinimumHeight(32)
        self.setAccessibleName(title)
        self.setToolTip(title)
        QApplication.instance().theme_manager.changed.connect(self.refresh_theme)

    @Slot()
    def refresh_theme(self) -> None:
        self.setIcon(icon(self.icon_name))

    def set_collapsed(self, collapsed: bool) -> None:
        self.setText("" if collapsed else self.title)
        self.setProperty("collapsed", collapsed)
        self.style().unpolish(self)
        self.style().polish(self)
