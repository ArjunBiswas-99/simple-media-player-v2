"""
Playlist Popover Widget - Netflix-style folder video list
"""

from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QFrame
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor
from constants import *
from styles import get_popover_container_style, get_popover_list_style


class PlaylistPopover(QWidget):
    """Netflix-style playlist popover showing videos in current folder"""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.media_player_ref = None
        self.video_files = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup popover UI with modern glass effect"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container with glass effect
        container = QWidget()
        container.setStyleSheet(get_popover_container_style())
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Playlist")
        title.setStyleSheet(f"color: white; font-size: {FONT_SIZE_MEDIUM}px; font-weight: 600;")
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: rgba(255, 255, 255, 180);
                font-size: 20px;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover { 
                background-color: rgba(229, 9, 20, 180); 
                color: white;
            }
        """)
        close_btn.clicked.connect(self.hide)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 15);")
        separator.setFixedHeight(1)
        container_layout.addWidget(separator)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.setStyleSheet(get_popover_list_style())
        self.video_list.setMaximumHeight(POPOVER_MAX_HEIGHT)
        self.video_list.setMinimumWidth(POPOVER_MIN_WIDTH)
        self.video_list.itemClicked.connect(self._on_video_selected)
        container_layout.addWidget(self.video_list)
        
        layout.addWidget(container)
        
        # Add shadow effect
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)
        
    def load_videos(self, current_file_path):
        """Scan folder for video files"""
        self.video_list.clear()
        self.video_files = []
        
        if not current_file_path:
            return
            
        folder_path = Path(current_file_path).parent
        current_filename = Path(current_file_path).name
        
        video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', 
                     '.webm', '.m4v', '.mpg', '.mpeg', '.m2ts', '.ts'}
        
        try:
            for file_path in sorted(folder_path.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in video_exts:
                    self.video_files.append(str(file_path))
                    
                    item = QListWidgetItem()
                    is_current = file_path.name == current_filename
                    
                    icon = "▶" if is_current else "□"
                    item.setText(f"{icon}  {file_path.name}")
                    item.setData(Qt.ItemDataRole.UserRole, str(file_path))
                    
                    if is_current:
                        item.setForeground(QColor(NETFLIX_RED))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    
                    self.video_list.addItem(item)
        except Exception as e:
            print(f"Error loading videos: {e}")
            
    def _on_video_selected(self, item):
        """Handle video selection"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and self.media_player_ref:
            self.media_player_ref.load_video(file_path)
            self.hide()
            
    def show_at_button(self, button):
        """Position popover above button"""
        self.adjustSize()
        button_pos = button.mapToGlobal(QPoint(0, 0))
        x = button_pos.x() - self.width() + button.width()
        y = button_pos.y() - self.height() - 10
        self.move(x, y)
        self.show()
        self.raise_()
