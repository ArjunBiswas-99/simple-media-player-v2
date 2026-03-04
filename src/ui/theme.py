from __future__ import annotations

from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtWidgets import QApplication

from ui.style_tokens import StyleTokens


def apply_dark_theme(app: QApplication) -> None:
    """Apply a minimal dark theme."""

    # A simple modern font. (System-provided on Windows; later we can bundle one.)
    app.setFont(QFont("Segoe UI", 10))

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(StyleTokens.BG))
    palette.setColor(QPalette.WindowText, QColor("#f2f2f2"))
    palette.setColor(QPalette.Base, QColor(StyleTokens.SURFACE))
    palette.setColor(QPalette.AlternateBase, QColor(StyleTokens.SURFACE_2))
    palette.setColor(QPalette.ToolTipBase, QColor(StyleTokens.SURFACE_2))
    palette.setColor(QPalette.ToolTipText, QColor("#f2f2f2"))
    palette.setColor(QPalette.Text, QColor("#f2f2f2"))
    palette.setColor(QPalette.Button, QColor(StyleTokens.SURFACE_2))
    palette.setColor(QPalette.ButtonText, QColor("#f2f2f2"))
    palette.setColor(QPalette.Highlight, QColor(StyleTokens.ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget { font-size: 12px; }
        QMainWindow { background: #0b0d10; }

        /* Menus */
        QMenuBar { background: #0b0d10; color: #f2f2f2; }
        QMenuBar::item:selected { background: rgba(255,255,255,18); }
        QMenu {
            background: #000000;
            color: #ffffff;
            border: 1px solid rgba(255,255,255,32);
        }
        QMenu::item:selected { background: rgba(255,255,255,22); }

        QPushButton {
            background: #171b21;
            border: 1px solid rgba(255,255,255,28);
            border-radius: 10px;
            padding: 6px 10px;
        }
        QPushButton:hover { background: #222; }
        QPushButton:pressed { background: #111; }

        QSlider::groove:horizontal {
            height: 6px;
            background: rgba(255,255,255,20);
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #e50914;
            width: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }
        QSlider::sub-page:horizontal {
            background: #e50914;
            border-radius: 3px;
        }
        """
    )
