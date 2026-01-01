"""
MPV Player Backend - Wrapper for libmpv integration.

Responsibilities:
- Initialize and configure MPV player
- Handle video playback (play, pause, seek)
- Manage audio (volume, mute, tracks)
- Provide playback state and properties
- Optimize for fast seeking (especially .ts files)
- Enable hardware acceleration
"""

import os
import sys
import locale
from PySide6.QtCore import QObject, Signal, QTimer

# Set locale for MPV (required on some systems)
try:
    locale.setlocale(locale.LC_NUMERIC, 'C')
except:
    pass

# Help find libmpv on macOS (Homebrew)
if sys.platform == 'darwin':
    os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:/usr/local/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')

# Try to import mpv
try:
    import mpv
    MPV_AVAILABLE = True
except (ImportError, OSError) as e:
    MPV_AVAILABLE = False
    print(f"MPV not available: {e}")
    if sys.platform == 'darwin':
        print("Install: brew install mpv")
    elif sys.platform == 'win32':
        print("Windows: Download MPV from https://mpv.io/installation/")
        print("Extract libmpv-2.dll to your Python folder or add to PATH")
    else:
        print("Linux: sudo apt install libmpv-dev")


class MPVPlayer(QObject):
    """
    MPV player backend wrapper.
    
    Provides a clean interface to MPV functionality and emits Qt signals
    for UI updates.
    
    Signals:
        playbackStateChanged: Emitted when play/pause state changes (bool: is_playing)
        positionChanged: Emitted when playback position changes (float: position in seconds)
        durationChanged: Emitted when media duration is available (float: duration in seconds)
        volumeChanged: Emitted when volume changes (int: volume 0-100)
        mediaLoaded: Emitted when new media file is loaded successfully
        mediaEnded: Emitted when playback reaches the end
        errorOccurred: Emitted on playback errors (str: error message)
    """
    
    # Signals
    playbackStateChanged = Signal(bool)  # is_playing
    positionChanged = Signal(float)  # position in seconds
    durationChanged = Signal(float)  # duration in seconds
    volumeChanged = Signal(int)  # volume 0-100
    mediaLoaded = Signal()
    mediaEnded = Signal()
    errorOccurred = Signal(str)
    
    def __init__(self):
        """Initialize MPV player with optimized settings."""
        super().__init__()
        
        # Check if MPV is available
        if not MPV_AVAILABLE:
            self._player = None
            self._is_playing = False
            self._current_file = None
            self._duration = 0.0
            self._position = 0.0
            self._position_timer = QTimer()
            return
        
        # Create MPV instance with optimized configuration
        try:
            self._player = mpv.MPV(
                # Video output
                vo='gpu',  # Use GPU-accelerated rendering
                
                # Hardware decoding (Windows: d3d11va, auto-detect others)
                hwdec='auto-safe',  # Enable hardware decoding
                
                # Fast seeking optimization (crucial for .ts files)
                hr_seek='yes',  # Enable high-resolution seeking
                hr_seek_framedrop='yes',  # Drop frames for faster seeking
                
                # Cache settings for better performance
                cache='yes',
                demuxer_max_bytes='150M',
                demuxer_max_back_bytes='75M',
                
                # Keep window reference for embedding
                keep_open='yes',
                idle='yes',
                
                # Disable OSD (we have our own UI)
                osd_level='0',
                
                # Input handling
                input_default_bindings='no',
                input_vo_keyboard='no',
                
                # Log level (only errors)
                msg_level='all=error',
            )
        except Exception as e:
            print(f"Failed to initialize MPV: {e}")
            self._player = None
            self._is_playing = False
            self._current_file = None
            self._duration = 0.0
            self._position = 0.0
            self._position_timer = QTimer()
            return
        
        # State tracking
        self._is_playing = False
        self._current_file = None
        self._duration = 0.0
        self._position = 0.0
        
        # Setup MPV event observers
        self._setup_observers()
        
        # Timer for position updates (30 FPS for smooth progress bar)
        self._position_timer = QTimer()
        self._position_timer.setInterval(33)  # ~30 FPS
        self._position_timer.timeout.connect(self._update_position)
        
    def _setup_observers(self):
        """Setup MPV property observers for state tracking."""
        if not self._player:
            return
            
        # Observe pause state
        @self._player.property_observer('pause')
        def on_pause_change(_name, value):
            if value is not None:
                self._is_playing = not value
                self.playbackStateChanged.emit(self._is_playing)
                
                # Don't start/stop timer from MPV thread - let main thread handle it
        
        # Observe duration
        @self._player.property_observer('duration')
        def on_duration_change(_name, value):
            if value is not None and value > 0:
                self._duration = value
                self.durationChanged.emit(value)
        
        # Observe end of file
        @self._player.property_observer('eof-reached')
        def on_eof(_name, value):
            if value:
                self.mediaEnded.emit()
                self._is_playing = False
                self.playbackStateChanged.emit(False)
    
    def _update_position(self):
        """Update current playback position."""
        if not self._player:
            return
        try:
            pos = self._player.time_pos
            if pos is not None:
                self._position = pos
                self.positionChanged.emit(pos)
        except:
            pass
    
    # ==================== Playback Control ====================
    
    def load_file(self, filepath):
        """
        Load a media file for playback.
        
        Args:
            filepath: Absolute path to media file
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        if not self._player:
            self.errorOccurred.emit("MPV player not initialized. Please install libmpv.")
            return False
            
        try:
            if not os.path.exists(filepath):
                self.errorOccurred.emit(f"File not found: {filepath}")
                return False
            
            self._current_file = filepath
            self._player.loadfile(filepath)
            
            # Wait a bit for file to load
            self._player.wait_for_property('duration')
            
            # Start position timer if not running
            if not self._position_timer.isActive():
                self._position_timer.start(100)
            
            self.mediaLoaded.emit()
            return True
            
        except Exception as e:
            self.errorOccurred.emit(f"Failed to load file: {str(e)}")
            return False
    
    def play(self):
        """Start or resume playback."""
        if not self._player:
            return
        try:
            self._player.pause = False
        except:
            pass
    
    def pause(self):
        """Pause playback."""
        if not self._player:
            return
        try:
            self._player.pause = True
        except:
            pass
    
    def toggle_play_pause(self):
        """Toggle between play and pause."""
        if not self._player:
            return
        try:
            self._player.pause = not self._player.pause
        except:
            pass
    
    def stop(self):
        """Stop playback."""
        if not self._player:
            return
        try:
            self._player.stop()
            self._is_playing = False
            self.playbackStateChanged.emit(False)
        except:
            pass
    
    def seek(self, position, absolute=True):
        """
        Seek to a position in the media.
        
        Args:
            position: Position in seconds (if absolute) or offset (if relative)
            absolute: If True, seek to absolute position. If False, seek relative to current.
        """
        if not self._player:
            return
        try:
            if absolute:
                self._player.seek(position, reference='absolute')
            else:
                self._player.seek(position, reference='relative')
        except:
            pass
    
    def seek_forward(self, seconds=10):
        """
        Seek forward by specified seconds.
        
        Args:
            seconds: Number of seconds to seek forward
        """
        self.seek(seconds, absolute=False)
    
    def seek_backward(self, seconds=10):
        """
        Seek backward by specified seconds.
        
        Args:
            seconds: Number of seconds to seek backward
        """
        self.seek(-seconds, absolute=False)
    
    # ==================== Audio Control ====================
    
    def set_volume(self, volume):
        """
        Set playback volume.
        
        Args:
            volume: Volume level (0-100)
        """
        if not self._player:
            return
        try:
            self._player.volume = max(0, min(100, volume))
            self.volumeChanged.emit(int(self._player.volume))
        except:
            pass
    
    def get_volume(self):
        """
        Get current volume.
        
        Returns:
            int: Current volume (0-100)
        """
        if not self._player:
            return 70
        try:
            return int(self._player.volume)
        except:
            return 70  # Default
    
    def set_mute(self, muted):
        """
        Mute or unmute audio.
        
        Args:
            muted: True to mute, False to unmute
        """
        if not self._player:
            return
        try:
            self._player.mute = muted
        except:
            pass
    
    def toggle_mute(self):
        """Toggle mute state."""
        if not self._player:
            return
        try:
            self._player.mute = not self._player.mute
        except:
            pass
    
    def is_muted(self):
        """
        Check if audio is muted.
        
        Returns:
            bool: True if muted, False otherwise
        """
        if not self._player:
            return False
        try:
            return self._player.mute
        except:
            return False
    
    # ==================== Playback Speed ====================
    
    def set_speed(self, speed):
        """
        Set playback speed.
        
        Args:
            speed: Playback speed multiplier (0.25 - 2.0)
        """
        if not self._player:
            return
        try:
            self._player.speed = max(0.25, min(2.0, speed))
        except:
            pass
    
    def get_speed(self):
        """
        Get current playback speed.
        
        Returns:
            float: Current speed multiplier
        """
        if not self._player:
            return 1.0
        try:
            return self._player.speed
        except:
            return 1.0
    
    # ==================== State Queries ====================
    
    def is_playing(self):
        """
        Check if media is currently playing.
        
        Returns:
            bool: True if playing, False if paused or stopped
        """
        return self._is_playing
    
    def get_position(self):
        """
        Get current playback position.
        
        Returns:
            float: Current position in seconds
        """
        return self._position
    
    def get_duration(self):
        """
        Get media duration.
        
        Returns:
            float: Duration in seconds
        """
        return self._duration
    
    def get_current_file(self):
        """
        Get currently loaded file path.
        
        Returns:
            str: File path or None
        """
        return self._current_file
    
    # ==================== Advanced Features ====================
    
    def set_aspect_ratio(self, ratio):
        """
        Set video aspect ratio.
        
        Args:
            ratio: Aspect ratio string (e.g., "16:9", "4:3", "-1" for default)
        """
        if not self._player:
            return
        try:
            if ratio.lower() == "default":
                self._player.video_aspect_override = "-1"
            else:
                self._player.video_aspect_override = ratio
        except:
            pass
    
    def get_video_params(self):
        """
        Get video parameters.
        
        Returns:
            dict: Video parameters (width, height, fps, codec, etc.)
        """
        if not self._player:
            return {}
        try:
            return {
                'width': self._player.width,
                'height': self._player.height,
                'fps': self._player.estimated_vf_fps,
                'codec': self._player.video_codec,
            }
        except:
            return {}
    
    def get_audio_params(self):
        """
        Get audio parameters.
        
        Returns:
            dict: Audio parameters (codec, sample rate, channels, etc.)
        """
        if not self._player:
            return {}
        try:
            return {
                'codec': self._player.audio_codec,
                'sample_rate': self._player.audio_params.get('samplerate') if self._player.audio_params else None,
                'channels': self._player.audio_params.get('channel_count') if self._player.audio_params else None,
            }
        except:
            return {}
    
    def get_mpv_handle(self):
        """
        Get the underlying MPV handle for embedding in UI.
        
        Returns:
            int: MPV window handle (wid) or None if player not available
        """
        if not self._player:
            return None
        return self._player.wid
    
    # ==================== Cleanup ====================
    
    def shutdown(self):
        """Cleanup and shutdown MPV player."""
        if not self._player:
            return
        try:
            self._position_timer.stop()
            self._player.terminate()
        except:
            pass
