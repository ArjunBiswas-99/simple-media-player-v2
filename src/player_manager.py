"""
Player Manager
Orchestrates media playback using QtPlayer.
Provides unified interface matching QMediaPlayer API.
"""
import os
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from .base_player import BasePlayer
from .qt_player import QtPlayer


class PlayerManager(QObject):
    """
    Manages media playback using QtPlayer.
    Provides unified interface matching QMediaPlayer API.
    """
    
    # Define PlayerManager's own signals
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    playbackStateChanged = pyqtSignal(object)
    errorOccurred = pyqtSignal(object, str)
    mediaStatusChanged = pyqtSignal(object)
    hasVideoChanged = pyqtSignal(bool)
    hasAudioChanged = pyqtSignal(bool)
    videoOutputChanged = pyqtSignal()
    bufferProgressChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create Qt player
        self._qt_player = QtPlayer(self)
        
        # Current active player
        self._current_player: BasePlayer = self._qt_player
        
        # Shared resources
        self._audio_output = None
        self._video_widget = None
        
        # State preservation
        self._volume = 1.0
        self._is_muted = False
        self._playback_rate = 1.0
        
        # Connect signals
        self._connect_player_signals(self._qt_player)
    
    def _connect_player_signals(self, player: BasePlayer):
        """Connect a player's signals to manager's signals."""
        # Forward signals only from active player
        player.positionChanged.connect(lambda pos: self._forward_if_active(player, self.positionChanged, pos))
        player.durationChanged.connect(lambda dur: self._forward_if_active(player, self.durationChanged, dur))
        player.playbackStateChanged.connect(lambda state: self._forward_if_active(player, self.playbackStateChanged, state))
        player.errorOccurred.connect(lambda error, msg: self._forward_if_active(player, self.errorOccurred, error, msg))
        player.mediaStatusChanged.connect(lambda status: self._forward_if_active(player, self.mediaStatusChanged, status))
        player.hasVideoChanged.connect(lambda has: self._forward_if_active(player, self.hasVideoChanged, has))
        player.hasAudioChanged.connect(lambda has: self._forward_if_active(player, self.hasAudioChanged, has))
        player.videoOutputChanged.connect(lambda: self._forward_if_active(player, self.videoOutputChanged))
        player.bufferProgressChanged.connect(lambda prog: self._forward_if_active(player, self.bufferProgressChanged, prog))
    
    def _forward_if_active(self, player: BasePlayer, signal, *args):
        """Forward signal only if it came from the active player."""
        if player == self._current_player:
            signal.emit(*args)
    
    # ==================== Public API (matches QMediaPlayer) ====================
    
    def setAudioOutput(self, audio_output: QAudioOutput):
        """Set audio output for player."""
        self._audio_output = audio_output
        self._qt_player.set_audio_output(audio_output)
    
    def setVideoOutput(self, video_widget: QVideoWidget):
        """Set video output widget."""
        self._video_widget = video_widget
        self._qt_player.set_video_output(video_widget)
    
    def setSource(self, url):
        """
        Set media source.
        """
        # Get file path
        if isinstance(url, QUrl):
            file_path = url.toLocalFile()
        else:
            file_path = url
        
        # Load media
        self._current_player.set_source(file_path)
    
    def play(self):
        """Start playback."""
        self._current_player.play()
    
    def pause(self):
        """Pause playback."""
        self._current_player.pause()
    
    def stop(self):
        """Stop playback."""
        self._current_player.stop()
    
    def setPosition(self, position_ms: int):
        """Seek to position."""
        self._current_player.set_position(position_ms)
    
    def position(self) -> int:
        """Get current position."""
        return self._current_player.position()
    
    def duration(self) -> int:
        """Get media duration."""
        return self._current_player.duration()
    
    def setPlaybackRate(self, rate: float):
        """Set playback speed."""
        self._playback_rate = rate
        self._current_player.set_playback_rate(rate)
    
    def playbackRate(self) -> float:
        """Get playback speed."""
        return self._current_player.playback_rate()
    
    def playbackState(self):
        """Get playback state."""
        return self._current_player.playback_state()
    
    def mediaStatus(self):
        """Get media status."""
        return self._current_player.media_status()
    
    def hasVideo(self) -> bool:
        """Check if has video."""
        return self._current_player.has_video()
    
    def hasAudio(self) -> bool:
        """Check if has audio."""
        return self._current_player.has_audio()
    
    def errorString(self) -> str:
        """Get error message."""
        return self._current_player.error_string()
    
    def isSeekable(self) -> bool:
        """Check if seekable."""
        return self._current_player.is_seekable()
    
    def bufferProgress(self) -> float:
        """Get buffer progress."""
        return self._current_player.buffer_progress()
    
    def audioOutput(self):
        """Get audio output."""
        return self._audio_output
    
    # ==================== Volume Management ====================
    
    def setVolume(self, volume: float):
        """Set volume for current player and save state."""
        self._volume = volume
        if self._audio_output:
            self._audio_output.setVolume(volume)
    
    def volume(self) -> float:
        """Get current volume."""
        if self._audio_output:
            return self._audio_output.volume()
        return self._volume
    
    def setMuted(self, muted: bool):
        """Set mute state."""
        self._is_muted = muted
        if self._audio_output:
            self._audio_output.setMuted(muted)
    
    def isMuted(self) -> bool:
        """Get mute state."""
        if self._audio_output:
            return self._audio_output.isMuted()
        return self._is_muted
    
    # ==================== Player Info ====================
    
    def getCurrentPlayerType(self) -> str:
        """Get the type of currently active player."""
        return self._current_player.get_player_type()
    
    def isUsingFFmpegPlayer(self) -> bool:
        """Check if currently using MpvPlayer (legacy method name for compatibility)."""
        return isinstance(self._current_player, MpvPlayer)
    
    # ==================== Fallback Mechanism ====================
    
    def fallbackToQtPlayer(self):
        """
        Emergency fallback to Qt player if FFmpeg player fails.
        Useful for error recovery.
        """
        if not isinstance(self._current_player, QtPlayer):
            print("⚠️ Falling back to Qt player due to error")
            self._switch_player(self._qt_player, "")
