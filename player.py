#!/usr/bin/env python3
"""
Netflix-Style Media Player
Built with PyQt6 and python-mpv
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog, QStyle
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPalette, QColor, QCursor
import mpv


class ControlsWidget(QWidget):
    """Netflix-style auto-hiding controls"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self._opacity = 1.0
        self.setup_ui()
        self.apply_style()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Timeline
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 1000)
        layout.addWidget(self.timeline)
        
        # Time labels
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.duration_label = QLabel("0:00")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.duration_label)
        layout.addLayout(time_layout)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.play_pause_btn = QPushButton("⏸")
        self.play_pause_btn.setFixedSize(50, 50)
        
        self.skip_back_btn = QPushButton("⏪")
        self.skip_back_btn.setFixedSize(50, 50)
        
        self.skip_forward_btn = QPushButton("⏩")
        self.skip_forward_btn.setFixedSize(50, 50)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(150)
        
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setFixedSize(50, 50)
        
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.skip_back_btn)
        controls_layout.addWidget(self.skip_forward_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("🔊"))
        controls_layout.addWidget(self.volume_slider)
        controls_layout.addWidget(self.fullscreen_btn)
        
        layout.addLayout(controls_layout)
        
    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 rgba(0, 0, 0, 200),
                    stop:1 rgba(0, 0, 0, 0)
                );
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 30);
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 50);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 70);
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 30);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e50914;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #e50914;
                border-radius: 3px;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)
    
    def get_opacity(self):
        return self._opacity
    
    def set_opacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)
    
    opacity = pyqtProperty(float, get_opacity, set_opacity)


class MediaPlayer(QMainWindow):
    """Main media player window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Netflix Media Player")
        self.setGeometry(100, 100, 1280, 720)
        self.setStyleSheet("background-color: black;")
        
        # MPV player
        self.player = mpv.MPV(
            wid=str(int(self.winId())),
            keep_open='yes',
            idle='yes',
            input_default_bindings=True,
            input_vo_keyboard=True,
            osc=False
        )
        
        # Controls
        self.controls = ControlsWidget(self)
        self.controls.setGeometry(0, self.height() - 200, self.width(), 200)
        
        # Control visibility timer
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.hide_controls)
        self.hide_timer.setSingleShot(True)
        
        # Update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(100)
        
        self.connect_signals()
        self.show_controls()
        
    def connect_signals(self):
        """Connect UI signals"""
        self.controls.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.controls.skip_back_btn.clicked.connect(lambda: self.seek_relative(-10))
        self.controls.skip_forward_btn.clicked.connect(lambda: self.seek_relative(10))
        self.controls.timeline.sliderPressed.connect(self.on_timeline_pressed)
        self.controls.timeline.sliderReleased.connect(self.on_timeline_released)
        self.controls.volume_slider.valueChanged.connect(self.set_volume)
        self.controls.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play_pause()
        elif event.key() == Qt.Key.Key_Left:
            self.seek_relative(-5)
        elif event.key() == Qt.Key.Key_Right:
            self.seek_relative(5)
        elif event.key() == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_O:
            self.open_file()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        self.show_controls()
        
    def mouseMoveEvent(self, event):
        """Show controls on mouse move"""
        self.show_controls()
        
    def mouseDoubleClickEvent(self, event):
        """Toggle fullscreen on double click"""
        self.toggle_fullscreen()
        
    def resizeEvent(self, event):
        """Reposition controls on resize"""
        super().resizeEvent(event)
        self.controls.setGeometry(0, self.height() - 200, self.width(), 200)
        
    def show_controls(self):
        """Show controls with fade animation"""
        self.controls.show()
        self.controls.opacity = 1.0
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.hide_timer.start(3000)
        
    def hide_controls(self):
        """Hide controls with fade animation"""
        anim = QPropertyAnimation(self.controls, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(self.controls.hide)
        anim.start()
        self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
        
    def open_file(self):
        """Open file dialog"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video File",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv);;All Files (*.*)"
        )
        if filename:
            self.player.play(filename)
            self.controls.play_pause_btn.setText("⏸")
            
    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.player.pause:
            self.player.pause = False
            self.controls.play_pause_btn.setText("⏸")
        else:
            self.player.pause = True
            self.controls.play_pause_btn.setText("▶")
            
    def seek_relative(self, seconds):
        """Seek relative to current position"""
        try:
            current = self.player.time_pos or 0
            self.player.seek(current + seconds, reference='absolute')
        except:
            pass
            
    def on_timeline_pressed(self):
        """Pause updates when dragging timeline"""
        self.update_timer.stop()
        
    def on_timeline_released(self):
        """Seek to timeline position"""
        try:
            duration = self.player.duration or 1
            position = (self.controls.timeline.value() / 1000.0) * duration
            self.player.seek(position, reference='absolute')
        except:
            pass
        self.update_timer.start(100)
        
    def set_volume(self, value):
        """Set volume (0-100)"""
        self.player.volume = value
        
    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def update_ui(self):
        """Update UI with current playback state"""
        try:
            # Update timeline
            if self.player.duration and not self.controls.timeline.isSliderDown():
                position = self.player.time_pos or 0
                duration = self.player.duration
                progress = int((position / duration) * 1000)
                self.controls.timeline.setValue(progress)
                
                # Update time labels
                self.controls.current_time_label.setText(self.format_time(position))
                self.controls.duration_label.setText(self.format_time(duration))
        except:
            pass
            
    def format_time(self, seconds):
        """Format seconds to MM:SS"""
        if seconds is None:
            return "0:00"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
        
    def closeEvent(self, event):
        """Clean up on close"""
        self.player.terminate()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    app.setPalette(palette)
    
    player = MediaPlayer()
    player.show()
    
    # Open file dialog on start
    QTimer.singleShot(100, player.open_file)
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
