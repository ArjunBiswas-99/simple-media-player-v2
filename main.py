#!/usr/bin/env python3
"""
Netflix-Style Professional Media Player
Main entry point
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import Qt

from media_player import MediaPlayer
from constants import NETFLIX_RED, NETFLIX_BLACK


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark Netflix palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(229, 9, 20))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(229, 9, 20))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)
    
    # Clean system font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    player = MediaPlayer()
    player.show()
    
    # NO auto-open file dialog - removed per user request
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
