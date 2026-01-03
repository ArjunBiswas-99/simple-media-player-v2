"""
Style helpers for Simple Media Player
Reusable stylesheet generators
"""

from constants import *


def get_button_style(size=BUTTON_SIZE_SMALL):
    """Generate advanced button stylesheet with glow and depth"""
    radius = size // 2
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 15),
                stop:1 rgba(255, 255, 255, 8));
            color: white;
            border: 1px solid rgba(255, 255, 255, 20);
            border-radius: {radius}px;
            font-size: 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {THEME_PRIMARY},
                stop:1 #b8070f);
            border: 1px solid {THEME_PRIMARY};
        }}
        QPushButton:pressed {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #b8070f,
                stop:1 #8a0509);
            border: 1px solid #b8070f;
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
    """Generate advanced menu bar with glass morphism and modern effects"""
    return f"""
        QMenuBar {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(20, 20, 20, 240),
                stop:1 rgba(15, 15, 15, 250));
            color: white;
            font-size: {FONT_SIZE_SMALL}px;
            font-weight: {FONT_WEIGHT_MEDIUM};
            padding: 6px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 8);
            spacing: 8px;
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 8px 16px;
            border-radius: 6px;
            margin: 0px 2px;
        }}
        QMenuBar::item:selected {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {THEME_PRIMARY},
                stop:1 #b8070f);
            border: 1px solid rgba(255, 255, 255, 20);
        }}
        QMenuBar::item:pressed {{
            background: #b8070f;
        }}
        QMenu {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(47, 47, 47, 250),
                stop:1 rgba(35, 35, 35, 250));
            color: white;
            font-size: {FONT_SIZE_SMALL}px;
            border: 1px solid rgba(229, 9, 20, 80);
            border-radius: 8px;
            padding: 8px 0px;
        }}
        QMenu::item {{
            background: transparent;
            padding: 10px 40px 10px 40px;
            margin: 2px 8px;
            border-radius: 6px;
        }}
        QMenu::item:selected {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {THEME_PRIMARY},
                stop:1 #b8070f);
            border: 1px solid rgba(255, 255, 255, 15);
        }}
        QMenu::separator {{
            height: 1px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(255, 255, 255, 0),
                stop:0.5 rgba(255, 255, 255, 20),
                stop:1 rgba(255, 255, 255, 0));
            margin: 8px 16px;
        }}
        QMenu::icon {{
            padding-left: 10px;
        }}
    """
