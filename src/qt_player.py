"""
Qt Media Player Wrapper
Wraps QMediaPlayer to conform to BasePlayer interface.
"""
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl
from .base_player import BasePlayer


class QtPlayer(BasePlayer):
    """Qt-based media player implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create QMediaPlayer
        self._player = QMediaPlayer(self)
        self._audio_output = None
        self._video_widget = None
        
        # Connect QMediaPlayer signals to BasePlayer signals
        self._connect_signals()
    
    def _connect_signals(self):
        """Connect internal QMediaPlayer signals to BasePlayer signals."""
        self._player.positionChanged.connect(self.positionChanged.emit)
        self._player.durationChanged.connect(self.durationChanged.emit)
        self._player.playbackStateChanged.connect(self.playbackStateChanged.emit)
        self._player.errorOccurred.connect(self.errorOccurred.emit)
        self._player.mediaStatusChanged.connect(self.mediaStatusChanged.emit)
        self._player.hasVideoChanged.connect(self.hasVideoChanged.emit)
        self._player.hasAudioChanged.connect(self.hasAudioChanged.emit)
        self._player.videoOutputChanged.connect(self.videoOutputChanged.emit)
        self._player.bufferProgressChanged.connect(self.bufferProgressChanged.emit)
    
    def _disconnect_signals(self):
        """Disconnect all signals."""
        try:
            self._player.positionChanged.disconnect()
            self._player.durationChanged.disconnect()
            self._player.playbackStateChanged.disconnect()
            self._player.errorOccurred.disconnect()
            self._player.mediaStatusChanged.disconnect()
            self._player.hasVideoChanged.disconnect()
            self._player.hasAudioChanged.disconnect()
            self._player.videoOutputChanged.disconnect()
            self._player.bufferProgressChanged.disconnect()
        except:
            pass
    
    # ==================== BasePlayer Interface Implementation ====================
    
    def set_video_output(self, video_widget):
        """Set the video output widget."""
        self._video_widget = video_widget
        self._player.setVideoOutput(video_widget)
    
    def set_audio_output(self, audio_output):
        """Set the audio output device."""
        self._audio_output = audio_output
        self._player.setAudioOutput(audio_output)
    
    def set_source(self, url):
        """Set the media source URL."""
        if isinstance(url, str):
            url = QUrl.fromLocalFile(url)
        self._source = url
        self._player.setSource(url)
        # Qt player is always "fully indexed" (no progressive indexing needed)
        self.indexingProgress.emit(100)
        self.indexedDurationChanged.emit(self._player.duration())
    
    def play(self):
        """Start playback."""
        self._player.play()
    
    def pause(self):
        """Pause playback."""
        self._player.pause()
    
    def stop(self):
        """Stop playback."""
        self._player.stop()
    
    def set_position(self, position_ms):
        """Seek to position in milliseconds."""
        self._player.setPosition(position_ms)
    
    def position(self):
        """Get current position in milliseconds."""
        return self._player.position()
    
    def duration(self):
        """Get media duration in milliseconds."""
        return self._player.duration()
    
    def set_playback_rate(self, rate):
        """Set playback speed (0.25x to 2.0x)."""
        self._playback_rate = rate
        self._player.setPlaybackRate(rate)
    
    def playback_rate(self):
        """Get current playback rate."""
        return self._player.playbackRate()
    
    def playback_state(self):
        """Get current playback state."""
        return self._player.playbackState()
    
    def media_status(self):
        """Get current media status."""
        return self._player.mediaStatus()
    
    def has_video(self):
        """Check if media has video."""
        return self._player.hasVideo()
    
    def has_audio(self):
        """Check if media has audio."""
        return self._player.hasAudio()
    
    def error_string(self):
        """Get last error message."""
        return self._player.errorString()
    
    def set_volume(self, volume):
        """Set volume (0.0 to 1.0)."""
        self._volume = volume
        if self._audio_output:
            self._audio_output.setVolume(volume)
    
    def volume(self):
        """Get current volume."""
        if self._audio_output:
            return self._audio_output.volume()
        return self._volume
    
    def set_muted(self, muted):
        """Set mute state."""
        self._is_muted = muted
        if self._audio_output:
            self._audio_output.setMuted(muted)
    
    def is_muted(self):
        """Get mute state."""
        if self._audio_output:
            return self._audio_output.isMuted()
        return self._is_muted
    
    def is_seekable(self):
        """Check if media is seekable."""
        return self._player.isSeekable()
    
    def buffer_progress(self):
        """Get buffer progress (0.0 to 1.0)."""
        return self._player.bufferProgress()
    
    def audio_output(self):
        """Get the audio output device."""
        return self._audio_output
    
    def cleanup(self):
        """Clean up resources before switching players."""
        self.stop()
        self._disconnect_signals()
        self._player.setSource(QUrl())
    
    # ==================== Direct Access ====================
    
    def get_qmediaplayer(self):
        """Get the underlying QMediaPlayer instance."""
        return self._player
