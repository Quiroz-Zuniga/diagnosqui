"""Ventana nativa con navegación persistente y cierre cooperativo de tareas."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, QTimer, Qt, Slot
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QStackedWidget,
    QApplication,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from diagnosqui.gui.controller import Controller
from diagnosqui.gui.pages.component_page import ComponentPage
from diagnosqui.gui.pages.dashboard_page import DashboardPage
from diagnosqui.gui.pages.monitor_page import MonitorPage
from diagnosqui.gui.pages.processes_page import ProcessesPage
from diagnosqui.gui.pages.problems_page import ProblemsPage
from diagnosqui.gui.pages.reports_page import ReportsPage
from diagnosqui.gui.pages.settings_page import SettingsPage
from diagnosqui.gui.services.diagnostic_service import COMPONENTS, DiagnosticService
from diagnosqui.gui.services.telemetry_service import TelemetryService
from diagnosqui.gui.theme import PRIORITY
from diagnosqui.gui.widgets.icons import NAV_ICONS, icon
from diagnosqui.gui.widgets.common import button, label
from diagnosqui.gui.widgets.sidebar_button import SidebarButton
from diagnosqui.gui.widgets.status_badge import StatusBadge


class MainWindow(QMainWindow):
    def __init__(
        self,
        service: Optional[DiagnosticService] = None,
        telemetry: Optional[TelemetryService] = None,
        settings: Optional[QSettings] = None,
        auto_start: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowTitle("DiagnosQui — Diagnóstico y administración de hardware")
        self.resize(1366, 768)
        self.setMinimumSize(1000, 660)
        self.settings = (
            settings if settings is not None else QSettings("DiagnosQui", "Escritorio")
        )
        self.theme_manager = QApplication.instance().theme_manager
        self.theme_manager.apply(self.settings.value("appearance", "light", type=str))
        self.current_page = "inicio"
        self._closing = False
        self._allow_close = False
        central = QWidget(objectName="workspace")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        topbar = QFrame(objectName="topbar")
        top = QHBoxLayout(topbar)
        top.setContentsMargins(18, 10, 18, 10)
        branding = QVBoxLayout()
        branding.addWidget(label("DiagnosQui", "brand"))
        branding.addWidget(label("Diagnóstico y administración de hardware", "muted"))
        top.addLayout(branding)
        top.addStretch()
        self.platform_label = label(self.theme_manager.platform.label)
        self.platform_label.setObjectName("platform")
        self.platform_label.setFixedHeight(28)
        top.addWidget(self.platform_label)
        top.addSpacing(12)
        top.addWidget(label("Estado general", "muted"))
        self.overall = StatusBadge()
        self.overall.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred
        )
        top.addWidget(self.overall)
        self.refresh_button = button("Actualizar datos", True)
        self.refresh_button.setToolTip("Actualizar diagnóstico completo (F5)")
        top.addWidget(self.refresh_button)
        root.addWidget(topbar)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = QFrame(objectName="sidebar")
        self.sidebar.setFixedWidth(230)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(8, 8, 8, 8)
        self.collapse = button("Navegación")
        self.collapse.setProperty("role", "collapse")
        self.collapse.setToolTip("Contraer navegación")
        self.collapse.setAccessibleName("Contraer navegación")
        self.collapse.clicked.connect(self.toggle_sidebar)
        side.addWidget(self.collapse)
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_container = QWidget()
        nav = QVBoxLayout(nav_container)
        nav.setContentsMargins(0, 4, 0, 4)
        nav.setSpacing(1)
        self.nav_categories = []
        self.stack = QStackedWidget()
        self.pages: dict[str, QWidget] = {}
        self.nav_buttons: dict[str, SidebarButton] = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.dashboard = DashboardPage()
        self.dashboard.navigate.connect(self.navigate)
        self.components = {
            key: ComponentPage(key, *description)
            for key, description in COMPONENTS.items()
            if key != "problemas"
        }
        self.processes = ProcessesPage()
        self.monitor = MonitorPage()
        self.problems = ProblemsPage()
        self.preferences = SettingsPage(self.settings)
        self.reports = ReportsPage(self.preferences.directory.text())
        entries = [("inicio", "Inicio", self.dashboard)]
        entries.extend(
            (key, title, self.components[key])
            for key, (title, _) in COMPONENTS.items()
            if key != "problemas"
        )
        entries.extend(
            [
                ("problemas", "Dispositivos con problemas", self.problems),
                ("procesos", "Procesos", self.processes),
                ("monitor", "Monitor en vivo", self.monitor),
                ("reportes", "Reportes", self.reports),
                ("configuracion", "Configuración", self.preferences),
            ]
        )
        categories = {
            "inicio": "EQUIPO",
            "cpu": "COMPONENTES",
            "problemas": "ACTIVIDAD",
            "reportes": "UTILIDADES",
        }
        for key, title, page in entries:
            if key in categories:
                category = label(categories[key], "category")
                self.nav_categories.append(category)
                nav.addWidget(category)
            self.pages[key] = page
            self.stack.addWidget(page)
            nav_button = SidebarButton(title, NAV_ICONS[key])
            nav_button.clicked.connect(
                lambda checked=False, target=key: self.navigate(target)
            )
            self.nav_buttons[key] = nav_button
            self.button_group.addButton(nav_button)
            nav.addWidget(nav_button)
        nav.addStretch()
        nav_scroll.setWidget(nav_container)
        side.addWidget(nav_scroll, 1)
        self.side_footer = label("Lecturas del sistema · Solo lectura", "muted")
        side.addWidget(self.side_footer)
        body.addWidget(self.sidebar)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)
        self.setCentralWidget(central)
        self.fade = QGraphicsOpacityEffect(self.stack)
        self.fade.setOpacity(1)
        self.stack.setGraphicsEffect(self.fade)
        self.animation = QPropertyAnimation(self.fade, b"opacity", self)
        self.animation.setDuration(110)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.controller = Controller(
            self,
            service or DiagnosticService(),
            telemetry or TelemetryService(),
            auto_start,
        )
        self.close_timer = QTimer(self)
        self.close_timer.setInterval(100)
        self.close_timer.timeout.connect(self._finish_close)
        shortcut = QShortcut(QKeySequence("F5"), self)
        shortcut.activated.connect(self.controller.refresh_all)
        home = QShortcut(QKeySequence("Ctrl+1"), self)
        home.activated.connect(lambda: self.navigate("inicio"))
        self.theme_manager.changed.connect(self.refresh_theme)
        self.refresh_theme()
        self.navigate("inicio")
        self.statusBar().showMessage(
            "Listo · Las consultas usan los permisos actuales del usuario."
        )

    def navigate(self, key: str) -> None:
        if self._closing or key not in self.pages:
            return
        self.animation.stop()
        self.current_page = key
        self.stack.setCurrentWidget(self.pages[key])
        self.nav_buttons[key].setChecked(True)
        if self.preferences.animations.isChecked() and self.isVisible():
            self.animation.setStartValue(0.75)
            self.animation.setEndValue(1)
            self.animation.start()
        else:
            self.fade.setOpacity(1)
        if key == "procesos":
            self.controller.tick()

    def toggle_sidebar(self) -> None:
        collapsed = self.sidebar.width() > 100
        self.sidebar.setFixedWidth(72 if collapsed else 230)
        self.collapse.setText("" if collapsed else "Navegación")
        self.collapse.setAccessibleName(
            "Expandir navegación" if collapsed else "Contraer navegación"
        )
        for category in self.nav_categories:
            category.setVisible(not collapsed)
        self.side_footer.setVisible(not collapsed)
        self.refresh_theme()
        self.collapse.setToolTip(
            "Expandir navegación" if collapsed else "Contraer navegación"
        )
        for item in self.nav_buttons.values():
            item.set_collapsed(collapsed)

    @Slot()
    def refresh_theme(self) -> None:
        self.platform_label.setText(self.theme_manager.platform.label)
        self.setProperty("platform", self.theme_manager.platform.key)
        self.collapse.setIcon(
            icon(
                "panel-left-open" if self.sidebar.width() < 100 else "panel-left-close"
            )
        )
        self.refresh_button.setIcon(
            icon("refresh-cw", self.theme_manager.tokens.on_accent)
        )

    def update_summary(self, results: dict) -> None:
        if not results:
            self.overall.set_state(None)
            return
        worst = min(
            (item.get("estado", "ADVERTENCIA") for item in results.values()),
            key=lambda state: PRIORITY.get(state, 1),
        )
        self.overall.set_state(worst)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._allow_close:
            event.accept()
            return
        if not self._closing and self.preferences.confirm_close.isChecked():
            question = QMessageBox(self)
            question.setWindowTitle("Cerrar DiagnosQui")
            question.setText("¿Quieres cerrar la aplicación?")
            question.setIcon(QMessageBox.Icon.Question)
            yes = question.addButton("Cerrar", QMessageBox.ButtonRole.AcceptRole)
            question.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            question.exec()
            if question.clickedButton() is not yes:
                event.ignore()
                return
        self._closing = True
        self.animation.stop()
        self.controller.stop()
        if self.controller.workers.finished():
            self._allow_close = True
            event.accept()
        else:
            event.ignore()
            self.centralWidget().setEnabled(False)
            self.statusBar().showMessage(
                "Finalizando las lecturas en curso antes de cerrar…"
            )
            self.close_timer.start()

    def _finish_close(self) -> None:
        if self.controller.workers.finished():
            self.close_timer.stop()
            self._allow_close = True
            self.close()
