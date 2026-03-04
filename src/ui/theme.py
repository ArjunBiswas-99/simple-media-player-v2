from __future__ import annotations

from PySide6.QtGui import QPalette, QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from ui.style_tokens import StyleTokens


def apply_dark_theme(app: QApplication) -> None:
    """Apply a minimal dark theme."""

    # Typography baseline: prefer Inter, fallback to Segoe UI.
    families = {f.lower() for f in QFontDatabase.families()}
    family = "Inter" if "inter" in families else "Segoe UI"
    base_font = QFont(family, 10)
    base_font.setWeight(QFont.Weight.DemiBold)
    app.setFont(base_font)

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
        QWidget { font-size: 12px; font-family: 'Inter', 'Segoe UI'; }
        QMainWindow { background: #0b0d10; }

        /* Menus */
        QMenuBar {
            background: #0b0d10;
            color: #f2f2f2;
            border-bottom: 1px solid rgba(255,255,255,18);
        }
        QMenuBar::item {
            padding: 6px 10px;
            border-radius: 6px;
            margin: 2px 4px;
            background: transparent;
        }
        QMenuBar::item:selected {
            color: #ffffff;
            background: rgba(229, 9, 20, 46);
            border: 1px solid rgba(229, 9, 20, 120);
        }
        QMenuBar::item:pressed {
            background: rgba(229, 9, 20, 62);
            border: 1px solid rgba(229, 9, 20, 160);
        }
        QMenu {
            background: #000000;
            color: #ffffff;
            border: 1px solid rgba(255,255,255,32);
            padding: 6px;
        }
        QMenu::item {
            padding: 8px 28px 8px 28px;
            border-radius: 7px;
            margin: 2px 4px;
            border-left: 3px solid transparent;
        }
        QMenu::item:selected {
            background: rgba(229, 9, 20, 50);
            border-left: 3px solid #e50914;
        }
        QMenu::separator {
            height: 1px;
            margin: 8px 12px;
            background: rgba(255,255,255,26);
        }

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
