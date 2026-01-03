#!/usr/bin/env python3
"""
Simple Media Player by Arjun Biswas
Main entry point
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import Qt

from media_player import MediaPlayer
from constants import THEME_PRIMARY, THEME_BLACK, FONT_FAMILY, FONT_SIZE_MEDIUM


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark color palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(THEME_BLACK))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("white"))
    palette.setColor(QPalette.ColorRole.Base, QColor(THEME_BLACK))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(THEME_BLACK))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("white"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("white"))
    palette.setColor(QPalette.ColorRole.Text, QColor("white"))
    palette.setColor(QPalette.ColorRole.Button, QColor(THEME_BLACK))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(THEME_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(THEME_PRIMARY))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    app.setPalette(palette)
    
    # Professional font stack with fallbacks
    font = QFont()
    font.setFamily(FONT_FAMILY)
    font.setPointSize(FONT_SIZE_MEDIUM)
    app.setFont(font)
    
    player = MediaPlayer()
    player.show()
    
    # NO auto-open file dialog - removed per user request
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
