"""
MPV Player Implementation
Uses libmpv for robust .ts file playback with perfect A/V sync.
"""
import os
import sys
import platform
# Note: mpv imported lazily in _load_mpv() to avoid import errors if library not found
from PyQt6.QtCore import QTimer, QUrl, Qt
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QWidget
from .base_player import BasePlayer


class MpvPlayer(BasePlayer):
    """mpv-based media player for .ts files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # mpv module (loaded lazily)
        self._mpv_module = None
        self._mpv_load_error = None
        
        # Find libmpv location
        self._libmpv_path = self._find_libmpv()
        
        # State
        self._player = None
        self._video_widget = None
        self._audio_output = None
        self._playback_state = QMediaPlayer.PlaybackState.StoppedState
        self._media_status = QMediaPlayer.MediaStatus.NoMedia
        self._is_seeking = False
        
        # Position update timer
        self._position_timer = QTimer(self)
        self._position_timer.timeout.connect(self._update_position)
        self._position_timer.setInterval(100)  # Update every 100ms
        
        # Error tracking
        self._last_error = ""
    
    def _load_mpv(self):
        """Lazy load mpv module to avoid import errors at startup."""
        if self._mpv_module is not None:
            return True
        
        if self._mpv_load_error is not None:
            return False  # Already tried and failed
        
        try:
            # Set library path before import if we have bundled version
            if self._libmpv_path:
                import ctypes.util
                # Override find_library to return our bundled path
                original_find = ctypes.util.find_library
                def find_mpv(name):
                    if 'mpv' in name.lower():
                        return self._libmpv_path
                    return original_find(name)
                ctypes.util.find_library = find_mpv
            
            # Now import mpv
            import mpv as mpv_module
            self._mpv_module = mpv_module
            
            # Restore original find_library
            if self._libmpv_path:
                ctypes.util.find_library = original_find
            
            return True
            
        except OSError as e:
            self._mpv_load_error = str(e)
            
            # Provide helpful error message
            if 'Windows' in platform.system():
                self._mpv_load_error = (
                    "libmpv-2.dll not found. Please download it from:\n"
                    "https://sourceforge.net/projects/mpv-player-windows/files/libmpv/\n"
                    "and place it in: external/mpv/windows/libmpv-2.dll"
                )
            elif 'Darwin' in platform.system():
                self._mpv_load_error = (
                    "libmpv not found. Please run: brew install mpv\n"
                    "Or the bundled library may be missing from: external/mpv/macos/"
                )
            else:
                self._mpv_load_error = f"libmpv not found: {e}"
            
            print(f"MpvPlayer: {self._mpv_load_error}")
            return False
        
        except Exception as e:
            self._mpv_load_error = f"Failed to load mpv: {str(e)}"
            print(f"MpvPlayer: {self._mpv_load_error}")
            return False
    
    def _find_libmpv(self):
        """Locate libmpv library - checks bundled location first, then system."""
        # Get repo root (two levels up from src/)
        repo_root = os.path.dirname(os.path.dirname(__file__))
        
        # Check platform
        system = platform.system()
        
        if system == 'Windows':
            lib_name = 'libmpv-2.dll'
            bundled_path = os.path.join(repo_root, 'external', 'mpv', 'windows', lib_name)
        elif system == 'Darwin':  # macOS
            lib_name = 'libmpv.2.dylib'
            bundled_path = os.path.join(repo_root, 'external', 'mpv', 'macos', lib_name)
        elif system == 'Linux':
            lib_name = 'libmpv.so.2'
            bundled_path = os.path.join(repo_root, 'external', 'mpv', 'linux', lib_name)
        else:
            bundled_path = None
        
        # Check bundled location first
        if bundled_path and os.path.exists(bundled_path):
            return bundled_path
        
        # Fall back to system-installed mpv (python-mpv will find it)
        return None
    
    def _create_mpv_instance(self, widget):
        """Create mpv player instance with widget embedding."""
        # Load mpv module first
        if not self._load_mpv():
            self._last_error = self._mpv_load_error or "Failed to load mpv"
            return False
        
        try:
            # Ensure widget has native window handle
            widget.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
            widget.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, False)
            
            # DEBUG: Print window ID
            wid_value = int(widget.winId())
            print(f"DEBUG: Widget winId = {wid_value} (type: {type(wid_value)})")
            
            # Try creating mpv WITHOUT wid first to test if wid is the problem
            print("DEBUG: Attempting to create mpv WITHOUT wid parameter...")
            try:
                test_player = self._mpv_module.MPV(
                    keep_open='yes',
                    idle='yes',
                    input_default_bindings=False,
                    input_vo_keyboard=False,
                    osc=False
                )
                test_player.terminate()
                print("DEBUG: mpv creation without wid SUCCEEDED")
            except Exception as e:
                print(f"DEBUG: mpv creation without wid FAILED: {e}")
                self._last_error = f"Failed to create mpv even without wid: {str(e)}"
                return False
            
            # Now try with wid
            print(f"DEBUG: Creating mpv WITH wid={wid_value}...")
            self._player = self._mpv_module.MPV(
                wid=str(wid_value),
                keep_open='yes',
                idle='yes',
                input_default_bindings=False,
                input_vo_keyboard=False,
                osc=False
            )
            print("DEBUG: mpv creation with wid SUCCEEDED")
            
            # Register event handlers
            @self._player.event_callback('end-file')
            def on_end_file(event):
                self._on_end_of_media()
            
            @self._player.property_observer('duration')
            def on_duration_change(name, value):
                if value:
                    self._duration = int(value * 1000)  # Convert to ms
                    self.durationChanged.emit(self._duration)
            
            return True
            
        except Exception as e:
            self._last_error = f"Failed to initialize mpv: {str(e)}"
            print(f"MpvPlayer error: {self._last_error}")
            return False
    
    # ==================== BasePlayer Interface Implementation ====================
    
    def set_video_output(self, video_widget):
        """Set the video output widget."""
        self._video_widget = video_widget
        
        if not isinstance(video_widget, QWidget):
            self._last_error = "Invalid video widget"
            return
        
        # Don't create mpv instance here - delay until set_source()
        # This ensures the widget is fully ready for video embedding
        print("MpvPlayer: video widget registered, will create instance on first playback")
    
    def set_audio_output(self, audio_output):
        """Set the audio output device (mpv handles audio internally)."""
        self._audio_output = audio_output
        # Note: mpv uses system audio directly, not Qt's audio output
        # Volume/mute controls still work via mpv properties
    
    def set_source(self, url):
        """Set the media source URL."""
        print(f"MpvPlayer.set_source called with: {url}")
        
        # Create mpv instance on first playback if not already created
        if not self._player:
            if not self._video_widget:
                self._last_error = "No video widget set"
                print(f"ERROR: {self._last_error}")
                self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
                return
            
            print("MpvPlayer: creating mpv instance now that playback is starting")
            if not self._create_mpv_instance(self._video_widget):
                self._last_error = f"Failed to create mpv instance: {self._last_error}"
                print(f"ERROR: {self._last_error}")
                self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
                return
        
        # Stop current playback
        self.stop()
        
        # Store source
        if isinstance(url, QUrl):
            url = url.toLocalFile()
        self._source = url
        
        print(f"MpvPlayer loading file: {url}")
        print(f"DEBUG: File path type: {type(url)}, length: {len(url)}")
        print(f"DEBUG: File exists: {os.path.exists(url)}")
        
        # Load file - test different approaches
        try:
            # Test 1: Try without 'replace' parameter
            print("DEBUG: Attempting loadfile WITHOUT 'replace' parameter...")
            try:
                self._player.loadfile(url)
                print("DEBUG: loadfile without 'replace' SUCCEEDED")
            except Exception as e1:
                print(f"DEBUG: loadfile without 'replace' FAILED: {e1}")
                print(f"DEBUG: Exception type: {type(e1)}")
                
                # Test 2: Try with 'replace' parameter
                print("DEBUG: Attempting loadfile WITH 'replace' parameter...")
                try:
                    self._player.loadfile(url, 'replace')
                    print("DEBUG: loadfile with 'replace' SUCCEEDED")
                except Exception as e2:
                    print(f"DEBUG: loadfile with 'replace' ALSO FAILED: {e2}")
                    
                    # Test 3: Try loadfile with NEW mpv instance WITHOUT wid to isolate the problem
                    print("DEBUG: Testing if wid is the problem - creating mpv WITHOUT wid...")
                    try:
                        test_player = self._mpv_module.MPV(
                            keep_open='yes',
                            idle='yes',
                            input_default_bindings=False,
                            input_vo_keyboard=False,
                            osc=False
                        )
                        test_player.loadfile(url)
                        print("DEBUG: ✓ loadfile WITHOUT wid SUCCEEDED - WID IS THE PROBLEM")
                        test_player.terminate()
                    except Exception as e3:
                        print(f"DEBUG: ✗ loadfile WITHOUT wid ALSO FAILED: {e3}")
                        print("DEBUG: Problem is NOT wid - file or mpv itself is broken")
                    
                    raise e2
            
            print(f"MpvPlayer file loaded successfully")
            self._media_status = QMediaPlayer.MediaStatus.LoadedMedia
            self.mediaStatusChanged.emit(self._media_status)
            
            # Check if has video/audio
            # Note: these properties may not be immediately available
            self.hasVideoChanged.emit(True)  # Assume .ts has video
            self.hasAudioChanged.emit(True)  # Assume .ts has audio
            
        except Exception as e:
            self._last_error = f"Failed to load file: {str(e)}"
            print(f"ERROR: {self._last_error}")
            print(f"ERROR: Full exception: {repr(e)}")
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
            self._media_status = QMediaPlayer.MediaStatus.InvalidMedia
            self.mediaStatusChanged.emit(self._media_status)
    
    def play(self):
        """Start playback."""
        print(f"MpvPlayer.play() called")
        
        if not self._player:
            print("ERROR: No player instance")
            return
        
        try:
            self._player.pause = False
            self._position_timer.start()
            self._playback_state = QMediaPlayer.PlaybackState.PlayingState
            self.playbackStateChanged.emit(self._playback_state)
            self._media_status = QMediaPlayer.MediaStatus.BufferedMedia
            self.mediaStatusChanged.emit(self._media_status)
            print("MpvPlayer playing")
        except Exception as e:
            self._last_error = f"Play error: {str(e)}"
            print(f"ERROR: {self._last_error}")
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
    
    def pause(self):
        """Pause playback."""
        if not self._player:
            return
        
        try:
            self._player.pause = True
            self._position_timer.stop()
            self._playback_state = QMediaPlayer.PlaybackState.PausedState
            self.playbackStateChanged.emit(self._playback_state)
        except Exception as e:
            self._last_error = f"Pause error: {str(e)}"
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
    
    def stop(self):
        """Stop playback."""
        if not self._player:
            return
        
        try:
            self._player.stop()
            self._position_timer.stop()
            self._position = 0
            self.positionChanged.emit(0)
            self._playback_state = QMediaPlayer.PlaybackState.StoppedState
            self.playbackStateChanged.emit(self._playback_state)
        except Exception as e:
            self._last_error = f"Stop error: {str(e)}"
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
    
    def set_position(self, position_ms):
        """Seek to position in milliseconds."""
        if not self._player:
            return
        
        try:
            self._is_seeking = True
            position_sec = position_ms / 1000.0
            self._player.seek(position_sec, 'absolute')
            self._position = position_ms
            self.positionChanged.emit(position_ms)
            self._is_seeking = False
        except Exception as e:
            self._last_error = f"Seek error: {str(e)}"
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
            self._is_seeking = False
    
    def position(self):
        """Get current position in milliseconds."""
        if not self._player:
            return 0
        
        try:
            pos = self._player.time_pos
            if pos is not None:
                return int(pos * 1000)
        except:
            pass
        
        return self._position
    
    def duration(self):
        """Get media duration in milliseconds."""
        if not self._player:
            return 0
        
        try:
            dur = self._player.duration
            if dur is not None:
                return int(dur * 1000)
        except:
            pass
        
        return self._duration
    
    def set_playback_rate(self, rate):
        """Set playback speed (0.25x to 2.0x)."""
        if not self._player:
            return
        
        try:
            self._playback_rate = rate
            self._player.speed = rate
        except Exception as e:
            self._last_error = f"Set playback rate error: {str(e)}"
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
    
    def playback_rate(self):
        """Get current playback rate."""
        if not self._player:
            return self._playback_rate
        
        try:
            return self._player.speed
        except:
            return self._playback_rate
    
    def playback_state(self):
        """Get current playback state."""
        return self._playback_state
    
    def media_status(self):
        """Get current media status."""
        return self._media_status
    
    def has_video(self):
        """Check if media has video."""
        # For .ts files, assume always true
        return True
    
    def has_audio(self):
        """Check if media has audio."""
        # For .ts files, assume always true
        return True
    
    def error_string(self):
        """Get last error message."""
        return self._last_error
    
    def set_volume(self, volume):
        """Set volume (0.0 to 1.0)."""
        if not self._player:
            return
        
        try:
            self._volume = volume
            self._player.volume = int(volume * 100)  # mpv uses 0-100
        except Exception as e:
            self._last_error = f"Set volume error: {str(e)}"
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
    
    def volume(self):
        """Get current volume."""
        if not self._player:
            return self._volume
        
        try:
            return self._player.volume / 100.0
        except:
            return self._volume
    
    def set_muted(self, muted):
        """Set mute state."""
        if not self._player:
            return
        
        try:
            self._is_muted = muted
            self._player.mute = muted
        except Exception as e:
            self._last_error = f"Set mute error: {str(e)}"
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
    
    def is_muted(self):
        """Get mute state."""
        if not self._player:
            return self._is_muted
        
        try:
            return self._player.mute
        except:
            return self._is_muted
    
    def is_seekable(self):
        """Check if media is seekable."""
        if not self._player:
            return False
        
        try:
            return self._player.seekable
        except:
            return True  # Assume seekable for files
    
    def buffer_progress(self):
        """Get buffer progress (0.0 to 1.0)."""
        # For local files, consider fully buffered
        return 1.0
    
    def audio_output(self):
        """Get the audio output device."""
        return self._audio_output
    
    def get_player_type(self):
        """Get player type identifier."""
        return "mpv"
    
    def cleanup(self):
        """Clean up resources before switching players."""
        self.stop()
        
        if self._player:
            try:
                self._player.terminate()
            except:
                pass
            self._player = None
    
    # ==================== Internal Methods ====================
    
    def _update_position(self):
        """Emit position updates (called by timer)."""
        if not self._is_seeking:
            pos = self.position()
            self.positionChanged.emit(pos)
            
            # Check if reached end
            if self._duration > 0 and pos >= self._duration - 100:  # 100ms tolerance
                # Let mpv's end-file event handle it
                pass
    
    def _on_end_of_media(self):
        """Handle end of playback."""
        self.stop()
        self._media_status = QMediaPlayer.MediaStatus.EndOfMedia
        self.mediaStatusChanged.emit(self._media_status)
