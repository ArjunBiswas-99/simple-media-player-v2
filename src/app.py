from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import apply_dark_theme


def main() -> int:
    # Encourage Qt to use a GPU backed surface where available.
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    apply_dark_theme(app)

    window = MainWindow()
    window.resize(1100, 650)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
