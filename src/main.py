"""
Simple Media Player V2 - Main Entry Point
Netflix-inspired UI with VLC-style functionality.

This module initializes the Qt application and launches the main window.
Follows Single Responsibility Principle: Only handles application lifecycle.
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    """
    Initialize and run the media player application.
    
    Returns:
        int: Application exit code
    """
    # Enable high DPI scaling for modern displays
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create the Qt application instance
    app = QApplication(sys.argv)
    app.setApplicationName("Simple Media Player V2")
    app.setOrganizationName("SimpleMediaPlayer")
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
