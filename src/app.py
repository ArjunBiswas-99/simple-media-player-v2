from __future__ import annotations

import os
import sys
import ctypes
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from ui.main_window import MainWindow
from ui.theme import apply_dark_theme


def main() -> int:
    # Encourage Qt to use a GPU backed surface where available.
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    # Windows: ensure taskbar grouping/identity is our app (not python.exe).
    # This improves the taskbar icon behavior when running from source.
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.arjun.mediaplayer")
        except Exception:
            pass

    app = QApplication(sys.argv)

    # App icon (title bar / Alt-Tab / often taskbar)
    icon_path = Path(__file__).resolve().parent / "ui" / "Assets" / "Icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    apply_dark_theme(app)

    window = MainWindow()
    window.resize(1100, 650)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
