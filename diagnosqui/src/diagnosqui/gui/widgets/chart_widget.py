"""Gráficas técnicas Qt: líneas de acento, ejes legibles y 60 muestras acotadas."""

from __future__ import annotations
import math
from collections import deque
from typing import Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from diagnosqui.gui.theme import (
    LABELS,
    current_tokens,
    format_percentage,
    percentage_state,
)
from diagnosqui.gui.visual_tokens import readable_color


class ChartWidget(QWidget):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.title = title
        self.history: deque[float] = deque(maxlen=60)
        self.unit = "%"
        self.value: Optional[float] = None
        self.percent: Optional[float] = None
        self.detail = "Esperando la primera muestra"
        self.setMinimumSize(210, 150)
        self.setAccessibleName(f"Gráfica de {title}, últimos 60 valores")

    def add_sample(
        self,
        value: Optional[float],
        unit: str = "%",
        percent: Optional[float] = None,
        detail: str = "",
    ) -> None:
        if unit != self.unit:
            self.history.clear()
        self.unit, self.percent, self.detail = unit, percent, detail
        self.value = value if value is not None and math.isfinite(value) else None
        if self.value is not None:
            self.history.append(self.value)
        self.setToolTip(detail)
        state = LABELS.get(percentage_state(percent), "Sin porcentaje")
        self.setAccessibleDescription(f"{self.current_value()}. {state}. {detail}")
        self.update()

    def current_value(self) -> str:
        if self.unit == "%":
            return format_percentage(self.value)
        return "N/D" if self.value is None else f"{self.value:.1f} {self.unit}"

    def paintEvent(self, event: object) -> None:
        tokens = current_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(tokens.border), 1))
        painter.setBrush(QColor(tokens.surface))
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(1, 1, -1, -1), tokens.radius, tokens.radius
        )
        painter.setPen(QColor(tokens.text_secondary))
        painter.drawText(14, 23, self.title)
        state = percentage_state(self.percent)
        attention = state in {"ADVERTENCIA", "CRITICO"}
        trace = (
            tokens.state_ink(state)
            if attention
            else readable_color(tokens.accent, tokens.surface, 3)
        )
        painter.setPen(
            QColor(tokens.state_ink(state) if attention else tokens.text_primary)
        )
        font = painter.font()
        font.setPixelSize(22)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(14, 51, self.current_value())
        area = QRectF(30, 67, self.width() - 44, self.height() - 96)
        painter.setPen(QPen(QColor(tokens.border), 0.7, Qt.PenStyle.DotLine))
        for portion in (0, 0.5, 1):
            y = area.top() + area.height() * portion
            painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
        maximum = (
            100 if self.unit == "%" else max(max(self.history, default=0) * 1.1, 1)
        )
        if len(self.history) > 1:
            path = QPainterPath()
            for index, value in enumerate(self.history):
                point = QPointF(
                    area.left() + index / 59 * area.width(),
                    area.bottom() - min(max(value / maximum, 0), 1) * area.height(),
                )
                if index == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(trace), 1.5))
            painter.drawPath(path)
        font.setPixelSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(tokens.text_secondary))
        painter.drawText(
            QRectF(2, area.top() - 6, 24, 14),
            Qt.AlignmentFlag.AlignRight,
            f"{maximum:.0f}" if maximum >= 10 else f"{maximum:.1f}",
        )
        painter.drawText(15, int(area.bottom()), "0")
        painter.drawText(
            14,
            self.height() - 10,
            f"{LABELS.get(state, 'Sin porcentaje')} · 60 muestras",
        )
        painter.end()
