from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, QSize, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QToolButton


class AnimatedToolButton(QToolButton):
    """A QToolButton with smooth hover/press animations.

    We animate iconSize (cheap + looks like scale) to give a modern
    "video player" feel.
    """

    def __init__(self, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self._base_icon = QSize(18, 18)
        self._hover_icon = QSize(20, 20)
        self._press_icon = QSize(17, 17)
        self._pop_icon = QSize(22, 22)

        self._anim = QPropertyAnimation(self, b"animatedIconSize", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.setAnimatedIconSize(self._base_icon)

    def setIconSize(self, size: QSize) -> None:  # noqa: N802
        # keep base setter behavior for Qt
        super().setIconSize(size)

    def _get_animated_icon_size(self) -> QSize:
        return self.iconSize()

    def _set_animated_icon_size(self, size: QSize) -> None:
        super().setIconSize(size)

    animatedIconSize = Property(QSize, _get_animated_icon_size, _set_animated_icon_size)

    def setBaseIconSize(self, size: QSize) -> None:  # noqa: N802
        self._base_icon = size
        self.setAnimatedIconSize(size)

    def setHoverIconSize(self, size: QSize) -> None:  # noqa: N802
        self._hover_icon = size

    def setPressIconSize(self, size: QSize) -> None:  # noqa: N802
        self._press_icon = size

    def setPopIconSize(self, size: QSize) -> None:  # noqa: N802
        self._pop_icon = size

    def setAnimatedIconSize(self, size: QSize) -> None:  # noqa: N802
        self._set_animated_icon_size(size)

    def enterEvent(self, event) -> None:  # noqa: N802
        super().enterEvent(event)
        self._animate_to(self._hover_icon)

    def leaveEvent(self, event) -> None:  # noqa: N802
        super().leaveEvent(event)
        self._animate_to(self._base_icon)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        super().mousePressEvent(event)
        self._animate_to(self._press_icon, duration=70)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        # Netflix-like click feedback: quick expand then settle.
        self._animate_click_bounce()

    def pulse(self) -> None:
        """Trigger the same visual feedback as a click.

        Used when the underlying action is triggered programmatically (keyboard
        shortcut, click on video surface, etc.) so the UI stays consistent.
        """
        self._animate_click_bounce()

    def _animate_to(self, size: QSize, duration: int = 120) -> None:
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setKeyValues([])
        self._anim.setStartValue(self.iconSize())
        self._anim.setEndValue(size)
        self._anim.start()

    def _animate_click_bounce(self) -> None:
        target = self._hover_icon if self.underMouse() else self._base_icon
        self._anim.stop()
        self._anim.setDuration(165)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(self.iconSize())
        self._anim.setKeyValueAt(0.42, self._pop_icon)
        self._anim.setEndValue(target)
        self._anim.start()
