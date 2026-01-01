"""
MPV Player wrapper for integration with Qt/QML
"""

import os
import sys

# Set library path for macOS Homebrew before importing mpv
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib'

import mpv
from PySide6.QtCore import QObject, Signal, Slot, Property
import locale


class MediaPlayer(QObject):
    """Main media player controller"""
    
    # Signals
    positionChanged = Signal(float)  # Current position in seconds
    durationChanged = Signal(float)  # Total duration in seconds
    playingChanged = Signal(bool)    # Playing state
    volumeChanged = Signal(int)      # Volume (0-100)
    fileLoaded = Signal(str)         # File path loaded
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set locale for MPV
        locale.setlocale(locale.LC_NUMERIC, 'C')
        
        # Initialize MPV with window embedding
        self.mpv = mpv.MPV(
            input_default_bindings=True,
            input_vo_keyboard=True,
            osc=False,  # Disable on-screen controller
            hwdec='auto',
            keep_open='yes',
            idle='yes'
        )
        
        # Internal state
        self._playing = False
        self._position = 0.0
        self._duration = 0.0
        self._volume = 80
        self._current_file = ""
        
        # Set initial volume
        self.mpv.volume = self._volume
        
        # Property observers
        @self.mpv.property_observer('time-pos')
        def on_position_change(_name, value):
            if value is not None:
                self._position = float(value)
                self.positionChanged.emit(self._position)
        
        @self.mpv.property_observer('duration')
        def on_duration_change(_name, value):
            if value is not None:
                self._duration = float(value)
                self.durationChanged.emit(self._duration)
        
        @self.mpv.property_observer('pause')
        def on_pause_change(_name, value):
            if value is not None:
                self._playing = not value
                self.playingChanged.emit(self._playing)
    
    # File operations
    @Slot(str)
    def openFile(self, filepath):
        """Load and play a media file"""
        try:
            # Remove file:// prefix if present
            if filepath.startswith('file://'):
                filepath = filepath[7:]
            
            self.mpv.play(filepath)
            self._current_file = filepath
            self._playing = True
            self.fileLoaded.emit(filepath)
            self.playingChanged.emit(True)
        except Exception as e:
            print(f"Error loading file: {e}")
    
    # Playback controls
    @Slot()
    def play(self):
        """Start playback"""
        self.mpv.pause = False
        self._playing = True
        self.playingChanged.emit(True)
    
    @Slot()
    def pause(self):
        """Pause playback"""
        self.mpv.pause = True
        self._playing = False
        self.playingChanged.emit(False)
    
    @Slot()
    def togglePlayPause(self):
        """Toggle between play and pause"""
        if self._playing:
            self.pause()
        else:
            self.play()
    
    @Slot(float)
    def seek(self, seconds):
        """Seek relative to current position"""
        try:
            self.mpv.seek(seconds, 'relative')
        except:
            pass
    
    @Slot(float)
    def setPosition(self, position):
        """Set absolute position in seconds"""
        try:
            self.mpv.seek(position, 'absolute')
        except:
            pass
    
    # Volume controls
    @Slot(int)
    def setVolume(self, volume):
        """Set volume (0-100)"""
        self._volume = max(0, min(100, volume))
        self.mpv.volume = self._volume
        self.volumeChanged.emit(self._volume)
    
    @Slot()
    def toggleMute(self):
        """Toggle mute"""
        self.mpv.mute = not self.mpv.mute
    
    # Properties
    @Property(bool, notify=playingChanged)
    def playing(self):
        return self._playing
    
    @Property(float, notify=positionChanged)
    def position(self):
        return self._position
    
    @Property(float, notify=durationChanged)
    def duration(self):
        return self._duration
    
    @Property(int, notify=volumeChanged)
    def volume(self):
        return self._volume
    
    @Property(str, notify=fileLoaded)
    def currentFile(self):
        return self._current_file
    
    def get_wid(self):
        """Get the window ID for embedding"""
        return str(int(self.mpv.wid)) if hasattr(self.mpv, 'wid') else None
