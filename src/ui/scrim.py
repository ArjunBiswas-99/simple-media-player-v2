from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QLinearGradient, QColor, QPainter
from PySide6.QtWidgets import QWidget


class BottomScrim(QWidget):
    """A bottom gradient overlay to make controls readable and feel cinematic."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        r = self.rect()
        grad = QLinearGradient(0, 0, 0, r.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.35, QColor(0, 0, 0, 60))
        grad.setColorAt(1.0, QColor(0, 0, 0, 200))
        painter.fillRect(r, grad)
        painter.end()
