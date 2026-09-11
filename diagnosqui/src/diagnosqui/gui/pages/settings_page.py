"""Preferencias persistentes de escritorio con QSettings."""

from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QSettings, QStandardPaths, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)
from diagnosqui import __version__
from diagnosqui.gui.widgets.common import button, label, page_layout


def default_reports_directory() -> str:
    documents = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    return str(Path(documents or str(Path.home())) / "DiagnosQui" / "Reportes")


class SettingsPage(QWidget):
    changed = Signal()

    def __init__(self, settings: QSettings) -> None:
        super().__init__()
        self.settings = settings
        layout = page_layout(
            self,
            "Configuración",
            "Preferencias guardadas para este usuario en el sistema operativo.",
        )
        form = QFormLayout()
        form.setSpacing(18)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.appearance = QComboBox()
        self.appearance.setAccessibleName("Tema visual")
        for title, mode in (
            ("Tema del sistema", "system"),
            ("Claro", "light"),
            ("Oscuro", "dark"),
        ):
            self.appearance.addItem(title, mode)
        selected = self.appearance.findData(
            settings.value("appearance", "light", type=str)
        )
        self.appearance.setCurrentIndex(selected if selected >= 0 else 1)
        form.addRow("Apariencia", self.appearance)
        form.addRow(
            "",
            label("El acento se adapta al sistema operativo detectado.", "muted", True),
        )
        self.interval = QSpinBox()
        self.interval.setRange(1, 30)
        self.interval.setMaximumWidth(180)
        self.interval.setSuffix(" segundos")
        self.interval.setValue(settings.value("monitor_interval", 1, type=int))
        form.addRow("Actualizar monitor cada", self.interval)
        self.animations = QCheckBox("Activar transiciones discretas")
        self.animations.setChecked(settings.value("animations", True, type=bool))
        form.addRow("Animaciones", self.animations)
        self.confirm_close = QCheckBox("Pedir confirmación antes de cerrar")
        self.confirm_close.setChecked(settings.value("confirm_close", False, type=bool))
        form.addRow("Cierre de la aplicación", self.confirm_close)
        self.directory = QLineEdit(
            settings.value("report_directory", default_reports_directory(), type=str)
        )
        self.directory.setAccessibleName("Carpeta predeterminada de reportes")
        row = QHBoxLayout()
        row.addWidget(self.directory)
        choose = button("Elegir…")
        choose.clicked.connect(self.choose_directory)
        row.addWidget(choose)
        form.addRow("Carpeta de reportes", row)
        form.addRow("Versión", label(__version__))
        form.addRow(
            "Sistema operativo",
            label(QApplication.instance().theme_manager.platform.label),
        )
        layout.addLayout(form)
        save = button("Guardar preferencias", True)
        save.clicked.connect(self.save)
        from PySide6.QtCore import Qt

        layout.addWidget(save, 0, Qt.AlignmentFlag.AlignLeft)
        self.message = label("", "muted", True)
        layout.addWidget(self.message)
        layout.addStretch()

    def choose_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Carpeta predeterminada", self.directory.text()
        )
        if selected:
            self.directory.setText(selected)

    def save(self) -> None:
        if not self.directory.text().strip():
            self.message.setText("Elige una carpeta de reportes.")
            return
        for key, value in {
            "monitor_interval": self.interval.value(),
            "animations": self.animations.isChecked(),
            "confirm_close": self.confirm_close.isChecked(),
            "report_directory": self.directory.text(),
            "appearance": self.appearance.currentData(),
        }.items():
            self.settings.setValue(key, value)
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            self.message.setText(
                "No se pudieron guardar las preferencias. Comprueba los permisos."
            )
            return
        self.message.setText("Preferencias guardadas.")
        self.changed.emit()
