#!/usr/bin/env python3
"""
Netflix-Style Media Player
Built with PyQt6 and QtMultimedia (native Qt video playback)
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QPalette, QColor, QCursor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class MediaPlayer(QMainWindow):
    """Netflix-style media player with embedded video"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Netflix Media Player")
        self.setGeometry(100, 100, 1280, 720)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget (displays video)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)
        
        # Media player setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        
        # Controls container
        self.controls_widget = QWidget()
        self.controls_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 rgba(0, 0, 0, 200),
                    stop:1 rgba(0, 0, 0, 0)
                );
            }
        """)
        layout.addWidget(self.controls_widget)
        
        self.setup_controls()
        self.connect_signals()
        
        # Control visibility timer
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.hide_controls)
        self.hide_timer.setSingleShot(True)
        
        # UI update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(100)
        
        self.is_seeking = False
        self.show_controls()
        
    def setup_controls(self):
        """Setup Netflix-style controls"""
        layout = QVBoxLayout(self.controls_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Timeline slider
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 0)
        self.timeline.setStyleSheet("""
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
        """)
        layout.addWidget(self.timeline)
        
        # Time labels
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color: white; font-size: 14px;")
        self.duration_label = QLabel("0:00")
        self.duration_label.setStyleSheet("color: white; font-size: 14px;")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.duration_label)
        layout.addLayout(time_layout)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        button_style = """
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
        """
        
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setFixedSize(50, 50)
        self.play_pause_btn.setStyleSheet(button_style)
        
        self.skip_back_btn = QPushButton("⏪")
        self.skip_back_btn.setFixedSize(50, 50)
        self.skip_back_btn.setStyleSheet(button_style)
        
        self.skip_forward_btn = QPushButton("⏩")
        self.skip_forward_btn.setFixedSize(50, 50)
        self.skip_forward_btn.setStyleSheet(button_style)
        
        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setFixedSize(50, 50)
        self.stop_btn.setStyleSheet(button_style)
        
        self.open_btn = QPushButton("📁")
        self.open_btn.setFixedSize(50, 50)
        self.open_btn.setStyleSheet(button_style)
        
        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("color: white; font-size: 20px;")
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(150)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 30);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: white;
                border-radius: 3px;
            }
        """)
        
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setFixedSize(50, 50)
        self.fullscreen_btn.setStyleSheet(button_style)
        
        controls_layout.addWidget(self.open_btn)
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.skip_back_btn)
        controls_layout.addWidget(self.skip_forward_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(volume_label)
        controls_layout.addWidget(self.volume_slider)
        controls_layout.addWidget(self.fullscreen_btn)
        
        layout.addLayout(controls_layout)
        
    def connect_signals(self):
        """Connect all signals"""
        # Player signals
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.playbackStateChanged.connect(self.state_changed)
        
        # Button signals
        self.open_btn.clicked.connect(self.open_file)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.stop_btn.clicked.connect(self.player.stop)
        self.skip_back_btn.clicked.connect(lambda: self.seek_relative(-10000))
        self.skip_forward_btn.clicked.connect(lambda: self.seek_relative(10000))
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        
        # Slider signals
        self.timeline.sliderPressed.connect(self.on_timeline_pressed)
        self.timeline.sliderMoved.connect(self.on_timeline_moved)
        self.timeline.sliderReleased.connect(self.on_timeline_released)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
    def open_file(self):
        """Open file dialog and load video"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video File",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm);;All Files (*.*)"
        )
        if filename:
            self.player.setSource(QUrl.fromLocalFile(filename))
            self.player.play()
            
    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()
            
    def seek_relative(self, ms):
        """Seek relative to current position (in milliseconds)"""
        new_position = self.player.position() + ms
        new_position = max(0, min(new_position, self.player.duration()))
        self.player.setPosition(new_position)
        
    def on_timeline_pressed(self):
        """Handle timeline press"""
        self.is_seeking = True
        
    def on_timeline_moved(self, position):
        """Handle timeline drag"""
        if self.is_seeking:
            self.current_time_label.setText(self.format_time(position))
            
    def on_timeline_released(self):
        """Handle timeline release - seek to position"""
        self.player.setPosition(self.timeline.value())
        self.is_seeking = False
        
    def set_volume(self, value):
        """Set volume (0-100)"""
        self.audio_output.setVolume(value / 100.0)
        
    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def position_changed(self, position):
        """Update timeline when position changes"""
        if not self.is_seeking:
            self.timeline.setValue(position)
            self.current_time_label.setText(self.format_time(position))
            
    def duration_changed(self, duration):
        """Update timeline range when duration changes"""
        self.timeline.setRange(0, duration)
        self.duration_label.setText(self.format_time(duration))
        
    def state_changed(self, state):
        """Update play/pause button when state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setText("⏸")
        else:
            self.play_pause_btn.setText("▶")
            
    def update_ui(self):
        """Update UI periodically"""
        pass  # Position updates handled by signals
        
    def format_time(self, ms):
        """Format milliseconds to MM:SS"""
        seconds = ms // 1000
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Space:
            self.toggle_play_pause()
        elif event.key() == Qt.Key.Key_Left:
            self.seek_relative(-5000)
        elif event.key() == Qt.Key.Key_Right:
            self.seek_relative(5000)
        elif event.key() == Qt.Key.Key_F or event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_O:
            self.open_file()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        elif event.key() == Qt.Key.Key_Up:
            current_volume = self.volume_slider.value()
            self.volume_slider.setValue(min(100, current_volume + 5))
        elif event.key() == Qt.Key.Key_Down:
            current_volume = self.volume_slider.value()
            self.volume_slider.setValue(max(0, current_volume - 5))
        self.show_controls()
        
    def mouseMoveEvent(self, event):
        """Show controls on mouse move"""
        self.show_controls()
        
    def mouseDoubleClickEvent(self, event):
        """Toggle fullscreen on double click"""
        self.toggle_fullscreen()
        
    def show_controls(self):
        """Show controls"""
        self.controls_widget.show()
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.hide_timer.start(3000)
        
    def hide_controls(self):
        """Hide controls"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.controls_widget.hide()
            self.setCursor(QCursor(Qt.CursorShape.BlankCursor))


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
    QTimer.singleShot(500, player.open_file)
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
