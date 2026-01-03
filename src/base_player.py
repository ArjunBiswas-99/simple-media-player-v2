"""
Base Player Interface
Abstract base class defining the common interface for all player implementations.
"""
from abc import ABCMeta, abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal


# Create a metaclass that combines Qt and ABC metaclasses
class QABCMeta(type(QObject), ABCMeta):
    pass


class BasePlayer(QObject, metaclass=QABCMeta):
    """Abstract base class for all player implementations."""
    
    # Signals that all players must emit
    positionChanged = pyqtSignal(int)  # Position in milliseconds
    durationChanged = pyqtSignal(int)  # Duration in milliseconds
    playbackStateChanged = pyqtSignal(object)  # PlaybackState enum
    errorOccurred = pyqtSignal(object, str)  # Error type, error message
    mediaStatusChanged = pyqtSignal(object)  # MediaStatus enum
    hasVideoChanged = pyqtSignal(bool)  # Whether video is available
    hasAudioChanged = pyqtSignal(bool)  # Whether audio is available
    videoOutputChanged = pyqtSignal()  # Video output changed
    bufferProgressChanged = pyqtSignal(float)  # Buffer progress (0.0-1.0)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = None
        self._position = 0
        self._duration = 0
        self._playback_rate = 1.0
        self._volume = 1.0
        self._is_muted = False
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    def set_video_output(self, video_widget):
        """Set the video output widget."""
        pass
    
    @abstractmethod
    def set_audio_output(self, audio_output):
        """Set the audio output device."""
        pass
    
    @abstractmethod
    def set_source(self, url):
        """Set the media source URL."""
        pass
    
    @abstractmethod
    def play(self):
        """Start playback."""
        pass
    
    @abstractmethod
    def pause(self):
        """Pause playback."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop playback."""
        pass
    
    @abstractmethod
    def set_position(self, position_ms):
        """Seek to position in milliseconds."""
        pass
    
    @abstractmethod
    def position(self):
        """Get current position in milliseconds."""
        pass
    
    @abstractmethod
    def duration(self):
        """Get media duration in milliseconds."""
        pass
    
    @abstractmethod
    def set_playback_rate(self, rate):
        """Set playback speed (0.25x to 2.0x)."""
        pass
    
    @abstractmethod
    def playback_rate(self):
        """Get current playback rate."""
        pass
    
    @abstractmethod
    def playback_state(self):
        """Get current playback state."""
        pass
    
    @abstractmethod
    def media_status(self):
        """Get current media status."""
        pass
    
    @abstractmethod
    def has_video(self):
        """Check if media has video."""
        pass
    
    @abstractmethod
    def has_audio(self):
        """Check if media has audio."""
        pass
    
    @abstractmethod
    def error_string(self):
        """Get last error message."""
        pass
    
    @abstractmethod
    def set_volume(self, volume):
        """Set volume (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def volume(self):
        """Get current volume."""
        pass
    
    @abstractmethod
    def set_muted(self, muted):
        """Set mute state."""
        pass
    
    @abstractmethod
    def is_muted(self):
        """Get mute state."""
        pass
    
    @abstractmethod
    def is_seekable(self):
        """Check if media is seekable."""
        pass
    
    @abstractmethod
    def buffer_progress(self):
        """Get buffer progress (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def audio_output(self):
        """Get the audio output device."""
        pass
    
    # ==================== Common Properties ====================
    
    def source(self):
        """Get current media source."""
        return self._source
    
    def get_player_type(self):
        """Get player implementation type."""
        return self.__class__.__name__
    
    # ==================== Cleanup ====================
    
    @abstractmethod
    def cleanup(self):
        """Clean up resources before switching players."""
        pass
