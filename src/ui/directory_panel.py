"""
Directory Panel - Netflix-styled file browser panel.

Responsibilities:
- Display list of media files from current directory
- Highlight currently playing file
- Handle file selection
- Slide in/out animation
- Netflix visual styling
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget, 
                               QListWidgetItem, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import Colors, Dimensions, Timings, Fonts, MockData


class DirectoryPanel(QWidget):
    """
    Side panel displaying directory contents.
    
    Responsibilities:
    - Show list of media files
    - Highlight active file
    - Emit signals on file selection
    - Animate slide in/out
    
    Signals:
        fileSelected: Emitted when user selects a file (str: filename)
        closeRequested: Emitted when panel should close
    """
    
    # Signals
    fileSelected = Signal(str)
    closeRequested = Signal()
    
    def __init__(self, parent=None):
        """Initialize directory panel."""
        super().__init__(parent)
        
        # State
        self._is_visible = False
        self._current_file = None
        
        # Setup UI
        self._setup_ui()
        
        # Setup animations
        self._setup_animations()
        
        # Initially hidden
        self.hide()
        
    def _setup_ui(self):
        """Create and layout panel elements."""
        # Set fixed width
        self.setFixedWidth(Dimensions.PANEL_WIDTH)
        
        # Apply Netflix panel styling
        self.setStyleSheet(f"""
            QWidget {{
                background: {Colors.PANEL_BACKGROUND};
                border-left: 1px solid {Colors.MENU_BORDER};
            }}
        """)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel("📁 Current Folder")
        header.setStyleSheet(f"""
            QLabel {{
                background: rgba(0, 0, 0, 0.5);
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.DIRECTORY_ITEM}px;
                font-weight: {Fonts.MEDIUM};
                font-family: {Fonts.FAMILY};
                padding: {Dimensions.PANEL_ITEM_PADDING}px;
                border-bottom: 1px solid {Colors.MENU_SEPARATOR};
            }}
        """)
        layout.addWidget(header)
        
        # File list
        self._file_list = QListWidget()
        self._file_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            
            QListWidget::item {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.DIRECTORY_ITEM}px;
                font-family: {Fonts.FAMILY};
                padding: {Dimensions.PANEL_ITEM_PADDING}px;
                min-height: {Dimensions.PANEL_ITEM_HEIGHT}px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }}
            
            QListWidget::item:hover {{
                background: {Colors.PANEL_ITEM_HOVER};
            }}
            
            QListWidget::item:selected {{
                background: {Colors.PANEL_ITEM_ACTIVE};
                color: {Colors.NETFLIX_RED};
            }}
        """)
        
        # Populate with mock data
        self._populate_mock_files()
        
        # Connect selection signal
        self._file_list.itemClicked.connect(self._on_file_clicked)
        
        layout.addWidget(self._file_list)
        
    def _populate_mock_files(self):
        """Populate list with mock file data (for initial display)."""
        # Start with empty list - will be populated when file is loaded
        pass
                
    def _setup_animations(self):
        """Setup slide animation for panel."""
        # Position animation for sliding
        self._slide_animation = QPropertyAnimation(self, b"pos")
        self._slide_animation.setDuration(Timings.PANEL_SLIDE_IN)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def _on_file_clicked(self, item):
        """
        Handle file selection.
        
        Args:
            item: QListWidgetItem that was clicked
        """
        # Extract filename (remove "▶ " prefix)
        filename = item.text().replace("▶ ", "")
        self._current_file = filename
        self.fileSelected.emit(filename)
        
    def slide_in(self):
        """Animate panel sliding in from right."""
        if self._is_visible:
            return
            
        self._is_visible = True
        self.show()
        
        # Calculate start and end positions
        parent_width = self.parent().width() if self.parent() else 0
        start_pos = QPoint(parent_width, 0)
        end_pos = QPoint(parent_width - self.width(), 0)
        
        # Animate
        self._slide_animation.setDuration(Timings.PANEL_SLIDE_IN)
        self._slide_animation.setStartValue(start_pos)
        self._slide_animation.setEndValue(end_pos)
        self._slide_animation.start()
        
    def slide_out(self):
        """Animate panel sliding out to right."""
        if not self._is_visible:
            return
            
        self._is_visible = False
        
        # Calculate start and end positions
        parent_width = self.parent().width() if self.parent() else 0
        start_pos = self.pos()
        end_pos = QPoint(parent_width, 0)
        
        # Animate
        self._slide_animation.setDuration(Timings.PANEL_SLIDE_OUT)
        self._slide_animation.setStartValue(start_pos)
        self._slide_animation.setEndValue(end_pos)
        
        # Hide after animation completes
        self._slide_animation.finished.connect(self.hide)
        self._slide_animation.start()
        
    def toggle_visibility(self):
        """Toggle panel visibility."""
        if self._is_visible:
            self.slide_out()
        else:
            self.slide_in()
            
    def update_file_list(self, files):
        """
        Update the file list with new files.
        
        Args:
            files: List of filenames
        """
        self._file_list.clear()
        for filename in files:
            item = QListWidgetItem(f"▶ {filename}")
            self._file_list.addItem(item)
            
    def set_current_file(self, filename):
        """
        Mark a file as currently playing.
        
        Args:
            filename: Name of the currently playing file
        """
        self._current_file = filename
        
        # Find and select the corresponding item
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            item_filename = item.text().replace("▶ ", "")
            if item_filename == filename:
                item.setSelected(True)
            else:
                item.setSelected(False)
