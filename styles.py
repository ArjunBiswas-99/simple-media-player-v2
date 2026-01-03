"""
Style helpers for Simple Media Player
Reusable stylesheet generators
"""

from constants import *


def get_button_style(size=BUTTON_SIZE_SMALL):
    """Generate button stylesheet"""
    radius = size // 2
    return f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 10);
            color: white;
            border: none;
            border-radius: {radius}px;
            font-size: 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {THEME_PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: #b8070f;
        }}
    """


def get_timeline_style():
    """Generate timeline slider stylesheet"""
    return f"""
        QSlider::groove:horizontal {{
            height: {TIMELINE_HEIGHT}px;
            background: rgba(255, 255, 255, 30);
            border-radius: 2px;
        }}
        QSlider::groove:horizontal:hover {{
            height: {TIMELINE_HEIGHT_HOVER}px;
        }}
        QSlider::handle:horizontal {{
            background: {THEME_PRIMARY};
            width: 12px;
            height: 12px;
            margin: -5px 0;
            border-radius: 6px;
            border: 2px solid white;
        }}
        QSlider::sub-page:horizontal {{
            background: {THEME_PRIMARY};
            border-radius: 2px;
        }}
    """


def get_volume_slider_style():
    """Generate volume slider stylesheet"""
    return f"""
        QSlider::groove:horizontal {{
            height: {TIMELINE_HEIGHT}px;
            background: rgba(255, 255, 255, 30);
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: white;
            width: 10px;
            height: 10px;
            margin: -4px 0;
            border-radius: 5px;
        }}
        QSlider::sub-page:horizontal {{
            background: white;
            border-radius: 2px;
        }}
    """


def get_popover_container_style():
    """Generate modern glass-effect popover container style"""
    return f"""
        QWidget {{
            background-color: rgba(20, 20, 20, 230);
            border-radius: 10px;
            border: 1px solid rgba(229, 9, 20, 80);
        }}
    """


def get_popover_list_style():
    """Generate popover list widget style"""
    return """
        QListWidget {
            background-color: transparent;
            border: none;
            outline: none;
            color: white;
            font-size: 13px;
        }
        QListWidget::item {
            padding: 10px 8px;
            border-radius: 4px;
            margin: 1px 0px;
        }
        QListWidget::item:hover {
            background-color: rgba(255, 255, 255, 15);
        }
        QListWidget::item:selected {
            background-color: rgba(229, 9, 20, 40);
        }
        QScrollBar:vertical {
            background-color: transparent;
            width: 6px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: rgba(255, 255, 255, 50);
            border-radius: 3px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: rgba(255, 255, 255, 80);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """


def get_main_window_style():
    """Generate main window stylesheet"""
    return f"""
        QMainWindow {{
            background-color: {THEME_BLACK};
        }}
        QToolTip {{
            background-color: {THEME_DARK_GRAY};
            color: white;
            border: 1px solid {THEME_PRIMARY};
            padding: 5px;
            font-size: {FONT_SIZE_SMALL}px;
        }}
    """


def get_menubar_style():
    """Generate menu bar stylesheet"""
    return f"""
        QMenuBar {{
            background-color: {THEME_BLACK};
            color: white;
            font-size: {FONT_SIZE_SMALL}px;
            padding: 4px;
        }}
        QMenuBar::item:selected {{
            background-color: {THEME_PRIMARY};
        }}
        QMenu {{
            background-color: {THEME_DARK_GRAY};
            color: white;
            border: 1px solid {THEME_PRIMARY};
        }}
        QMenu::item:selected {{
            background-color: {THEME_PRIMARY};
        }}
    """
