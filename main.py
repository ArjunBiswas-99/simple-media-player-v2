#!/usr/bin/env python3
"""
Simple Media Player v2
A modern, high-performance desktop media player with Netflix-inspired UI
"""

import sys
import os
from pathlib import Path
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import QUrl

# Set the Qt Quick Controls style to Basic (for custom styling)
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"

# Import player module
sys.path.insert(0, str(Path(__file__).parent / "src"))
from player import MediaPlayer


def main():
    """Main entry point for the application"""
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Simple Media Player")
    app.setOrganizationName("SimpleMediaPlayer")
    
    # Create media player instance
    player = MediaPlayer()
    
    engine = QQmlApplicationEngine()
    
    # Expose player to QML
    engine.rootContext().setContextProperty("mediaPlayer", player)
    
    # Load the main QML file
    qml_file = Path(__file__).parent / "src" / "main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    
    if not engine.rootObjects():
        sys.exit(-1)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
