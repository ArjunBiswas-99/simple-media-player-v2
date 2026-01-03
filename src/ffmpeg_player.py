"""
FFmpeg Player Implementation
Direct FFmpeg/PyAV player for efficient .ts file playback.
"""
import av
import threading
import time
import queue
from PyQt6.QtCore import QTimer, QUrl, Qt
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QAudioFormat, QAudioSink, QAudio
from PyQt6.QtGui import QImage
from .base_player import BasePlayer
from .custom_video_widget import CustomVideoWidget
import numpy as np


class FFmpegPlayer(BasePlayer):
    """FFmpeg-based media player for .ts files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._container = None
        self._video_stream = None
        self._audio_stream = None
        self._video_widget = None
        self._audio_output = None
        self._audio_sink = None
        
        # Playback control
        self._playback_state = QMediaPlayer.PlaybackState.StoppedState
        self._media_status = QMediaPlayer.MediaStatus.NoMedia
        self._is_playing = False
        self._is_paused = False
        self._target_position_ms = None  # For seeking
        
        # Timing and sync
        self._start_time = 0  # System time when playback started
        self._pause_time = 0  # Position when paused
        self._video_time_base = 1.0  # Video stream time base
        self._audio_time_base = 1.0  # Audio stream time base
        
        # Frame rendering timer
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._render_frame)
        self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)  # PreciseTimer for smooth playback
        
        # Decoding threads
        self._decode_thread = None
        self._decode_queue = queue.Queue(maxsize=30)  # Video frame queue
        self._audio_queue = queue.Queue(maxsize=100)  # Audio frame queue
        self._stop_decode = threading.Event()
        
        # Audio playback
        self._audio_io_device = None  # QIODevice for audio output
        self._audio_buffer = bytearray()
        self._audio_resampler = None  # Reuse single resampler instance
        
        # Error handling
        self._last_error = ""
    
    # ==================== BasePlayer Interface Implementation ====================
    
    def set_video_output(self, video_widget):
        """Set the video output widget."""
        if isinstance(video_widget, CustomVideoWidget):
            self._video_widget = video_widget
        else:
            # Create CustomVideoWidget wrapper if needed
            self._video_widget = CustomVideoWidget()
    
    def set_audio_output(self, audio_output):
        """Set the audio output device."""
        self._audio_output = audio_output
        self._setup_audio_sink()
    
    def _setup_audio_sink(self):
        """Setup QAudioSink for audio playback."""
        if not self._audio_output:
            return
        
        # Stop existing audio sink
        if self._audio_sink:
            self._audio_sink.stop()
        
        # Create audio format (default: 48kHz, stereo, 16-bit)
        audio_format = QAudioFormat()
        audio_format.setSampleRate(48000)
        audio_format.setChannelCount(2)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        
        # Create audio sink
        device = self._audio_output.device()
        self._audio_sink = QAudioSink(device, audio_format)
        
        # Start audio sink with a buffer
        from PyQt6.QtCore import QBuffer, QIODevice
        self._audio_io_device = self._audio_sink.start()
    
    def set_source(self, url):
        """Set the media source URL."""
        # Stop current playback
        self.stop()
        
        # Close existing container
        if self._container:
            try:
                self._container.close()
            except:
                pass
            self._container = None
        
        # Store source
        if isinstance(url, QUrl):
            url = url.toLocalFile()
        self._source = url
        
        # Try to open the file
        try:
            self._container = av.open(url)
            
            # Find video and audio streams
            self._video_stream = self._container.streams.video[0] if self._container.streams.video else None
            self._audio_stream = self._container.streams.audio[0] if self._container.streams.audio else None
            
            # Get duration
            if self._container.duration:
                self._duration = int(self._container.duration / 1000)  # Convert to milliseconds
                self.durationChanged.emit(self._duration)
            
            # Get time bases
            if self._video_stream:
                self._video_time_base = float(self._video_stream.time_base)
                self.hasVideoChanged.emit(True)
            
            if self._audio_stream:
                self._audio_time_base = float(self._audio_stream.time_base)
                self.hasAudioChanged.emit(True)
                
                # Create audio resampler once
                self._audio_resampler = av.AudioResampler(
                    format='s16',
                    layout='stereo',
                    rate=48000
                )
            
            # Update media status
            self._media_status = QMediaPlayer.MediaStatus.LoadedMedia
            self.mediaStatusChanged.emit(self._media_status)
            
        except Exception as e:
            self._last_error = f"Failed to open media: {str(e)}"
            self._media_status = QMediaPlayer.MediaStatus.InvalidMedia
            self.errorOccurred.emit(QMediaPlayer.Error.ResourceError, self._last_error)
            self.mediaStatusChanged.emit(self._media_status)
    
    def play(self):
        """Start playback."""
        if not self._container:
            return
        
        if self._playback_state == QMediaPlayer.PlaybackState.PlayingState:
            return  # Already playing
        
        # Resume from pause
        if self._is_paused:
            self._start_time = time.time() - (self._pause_time / 1000.0)
            self._is_paused = False
        else:
            # Start fresh
            self._start_time = time.time()
            self._position = 0
            
            # Start decode thread
            self._stop_decode.clear()
            self._decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
            self._decode_thread.start()
        
        # Start audio sink if available
        if self._audio_sink:
            if self._audio_sink.state() != QAudio.State.ActiveState:
                self._audio_io_device = self._audio_sink.start()
        
        # Start rendering
        self._is_playing = True
        frame_rate = 30  # Default FPS
        if self._video_stream and self._video_stream.average_rate:
            frame_rate = float(self._video_stream.average_rate)
        
        # Adjust frame interval based on playback rate (for 2x speed support)
        interval_ms = int(1000 / (frame_rate * self._playback_rate))
        self._render_timer.start(interval_ms)
        
        # Update state
        self._playback_state = QMediaPlayer.PlaybackState.PlayingState
        self.playbackStateChanged.emit(self._playback_state)
        self._media_status = QMediaPlayer.MediaStatus.BufferedMedia
        self.mediaStatusChanged.emit(self._media_status)
    
    def pause(self):
        """Pause playback."""
        if not self._is_playing:
            return
        
        self._is_playing = False
        self._is_paused = True
        self._pause_time = self._position
        self._render_timer.stop()
        
        self._playback_state = QMediaPlayer.PlaybackState.PausedState
        self.playbackStateChanged.emit(self._playback_state)
    
    def stop(self):
        """Stop playback."""
        self._is_playing = False
        self._is_paused = False
        self._render_timer.stop()
        
        # Stop audio sink
        if self._audio_sink:
            self._audio_sink.stop()
        
        # Stop decode thread
        if self._decode_thread and self._decode_thread.is_alive():
            self._stop_decode.set()
            self._decode_thread.join(timeout=1.0)
        
        # Clear frame queues
        while not self._decode_queue.empty():
            try:
                self._decode_queue.get_nowait()
            except:
                break
        
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except:
                break
        
        # Clear video widget
        if self._video_widget:
            self._video_widget.clear_frame()
        
        # Reset position
        self._position = 0
        self.positionChanged.emit(0)
        
        self._playback_state = QMediaPlayer.PlaybackState.StoppedState
        self.playbackStateChanged.emit(self._playback_state)
    
    def set_position(self, position_ms):
        """Seek to position in milliseconds."""
        if not self._container or not self.is_seekable():
            return
        
        self._target_position_ms = position_ms
        
        # Stop current playback temporarily
        was_playing = self._is_playing
        
        # Stop decode thread completely before seeking
        if self._decode_thread and self._decode_thread.is_alive():
            self._stop_decode.set()
            self._decode_thread.join(timeout=1.0)
        
        # Stop rendering
        if was_playing:
            self._is_playing = False
            self._render_timer.stop()
        
        # Stop audio temporarily
        if self._audio_sink:
            self._audio_sink.stop()
        
        # Clear frame queues before seeking
        while not self._decode_queue.empty():
            try:
                self._decode_queue.get_nowait()
            except:
                break
        
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except:
                break
        
        # Seek the container
        try:
            # Convert milliseconds to microseconds
            seek_target = int(position_ms * 1000)
            
            # Use BACKWARD flag for keyframe seeking
            self._container.seek(seek_target, backward=True, any_frame=False)
            
            # For long seeks, skip frames to target position quickly
            if self._video_stream:
                target_pts = seek_target / 1000000.0  # Convert to seconds
                frames_skipped = 0
                
                # Decode and skip frames until we reach target position
                for packet in self._container.demux(self._video_stream):
                    for frame in packet.decode():
                        frame_time = float(frame.pts * self._video_stream.time_base)
                        
                        # If we're close to target, stop skipping
                        if frame_time >= target_pts - 0.5:  # Within 0.5 seconds
                            break
                        frames_skipped += 1
                        
                        # Limit frame skipping to avoid taking too long
                        if frames_skipped > 300:  # ~10 seconds at 30fps
                            break
                    
                    # Break outer loop too
                    if frames_skipped > 0:
                        break
            
            # Update position
            self._position = position_ms
            self._pause_time = position_ms
            
            # Reset start time for accurate playback timing
            self._start_time = time.time() - (position_ms / 1000.0 / self._playback_rate)
            
            self.positionChanged.emit(position_ms)
            
            # Restart decode thread if was playing
            if was_playing:
                self._stop_decode.clear()
                self._decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
                self._decode_thread.start()
                
                # Restart audio sink
                if self._audio_sink and self._audio_io_device:
                    self._audio_io_device = self._audio_sink.start()
                
                # Resume playback
                self._start_time = time.time() - (position_ms / 1000.0)
                self._is_playing = True
                
                # Restart rendering
                frame_rate = 30
                if self._video_stream and self._video_stream.average_rate:
                    frame_rate = float(self._video_stream.average_rate)
                
                # Adjust for playback rate
                interval_ms = int(1000 / (frame_rate * self._playback_rate))
                self._render_timer.start(interval_ms)
        
        except Exception as e:
            self._last_error = f"Seek failed: {str(e)}"
            print(f"FFmpegPlayer seek error: {self._last_error}")
    
    def position(self):
        """Get current position in milliseconds."""
        if self._is_playing:
            elapsed = time.time() - self._start_time
            self._position = int(elapsed * 1000 * self._playback_rate)
        return self._position
    
    def duration(self):
        """Get media duration in milliseconds."""
        return self._duration
    
    def set_playback_rate(self, rate):
        """Set playback speed (0.25x to 2.0x)."""
        self._playback_rate = rate
        # Adjust start time to maintain current position
        if self._is_playing:
            current_pos = self.position()
            self._start_time = time.time() - (current_pos / 1000.0)
            
            # Adjust render timer interval for new rate
            frame_rate = 30
            if self._video_stream and self._video_stream.average_rate:
                frame_rate = float(self._video_stream.average_rate)
            
            interval_ms = int(1000 / (frame_rate * self._playback_rate))
            self._render_timer.setInterval(interval_ms)
    
    def playback_rate(self):
        """Get current playback rate."""
        return self._playback_rate
    
    def playback_state(self):
        """Get current playback state."""
        return self._playback_state
    
    def media_status(self):
        """Get current media status."""
        return self._media_status
    
    def has_video(self):
        """Check if media has video."""
        return self._video_stream is not None
    
    def has_audio(self):
        """Check if media has audio."""
        return self._audio_stream is not None
    
    def error_string(self):
        """Get last error message."""
        return self._last_error
    
    def set_volume(self, volume):
        """Set volume (0.0 to 1.0)."""
        self._volume = volume
        if self._audio_sink:
            self._audio_sink.setVolume(volume)
    
    def volume(self):
        """Get current volume."""
        if self._audio_sink:
            return self._audio_sink.volume()
        return self._volume
    
    def set_muted(self, muted):
        """Set mute state."""
        self._is_muted = muted
        # Implement by setting volume to 0 or restoring
        if self._audio_sink:
            if muted:
                self._audio_sink.setVolume(0.0)
            else:
                self._audio_sink.setVolume(self._volume)
    
    def is_muted(self):
        """Get mute state."""
        return self._is_muted
    
    def is_seekable(self):
        """Check if media is seekable."""
        return self._container is not None and self._container.duration is not None
    
    def buffer_progress(self):
        """Get buffer progress (0.0 to 1.0)."""
        # For local files, consider fully buffered
        return 1.0
    
    def audio_output(self):
        """Get the audio output device."""
        return self._audio_output
    
    def cleanup(self):
        """Clean up resources before switching players."""
        self.stop()
        
        if self._container:
            try:
                self._container.close()
            except:
                pass
            self._container = None
        
        self._video_stream = None
        self._audio_stream = None
        self._audio_resampler = None
    
    # ==================== Internal Methods ====================
    
    def _decode_loop(self):
        """Background thread for decoding both video and audio."""
        try:
            # Check if container is still valid
            if not self._container:
                return
            
            # Demux both video and audio streams
            streams_to_demux = []
            if self._video_stream:
                streams_to_demux.append(self._video_stream)
            if self._audio_stream:
                streams_to_demux.append(self._audio_stream)
            
            if not streams_to_demux:
                return
            
            for packet in self._container.demux(*streams_to_demux):
                if self._stop_decode.is_set():
                    break
                
                try:
                    for frame in packet.decode():
                        if self._stop_decode.is_set():
                            break
                        
                        # Handle video frames
                        if packet.stream.type == 'video':
                            # Convert to RGB
                            frame_rgb = frame.to_ndarray(format='rgb24')
                            
                            # Put in video queue
                            try:
                                self._decode_queue.put((frame_rgb, frame.width, frame.height), timeout=0.1)
                            except queue.Full:
                                continue  # Skip frame if queue is full
                        
                        # Handle audio frames
                        elif packet.stream.type == 'audio' and self._audio_resampler:
                            # Use pre-created resampler to avoid thread creation
                            resampled_frames = self._audio_resampler.resample(frame)
                            
                            # Convert resampled frames to bytes
                            for resampled in resampled_frames:
                                audio_data = resampled.to_ndarray().tobytes()
                                
                                # Put in audio queue
                                try:
                                    self._audio_queue.put(audio_data, timeout=0.1)
                                except queue.Full:
                                    continue  # Skip if queue is full
                
                except Exception as decode_error:
                    # Handle decode errors gracefully
                    print(f"Decode error: {decode_error}")
                    continue
        
        except Exception as e:
            print(f"FFmpegPlayer decode loop error: {e}")
    
    def _render_frame(self):
        """Render the next frame and output audio (called by timer)."""
        if not self._is_playing:
            return
        
        # Get and render video frame
        try:
            frame_data, width, height = self._decode_queue.get_nowait()
            
            # Render to widget
            if self._video_widget:
                self._video_widget.set_frame(
                    frame_data.tobytes(),
                    width,
                    height,
                    QImage.Format.Format_RGB888
                )
            
            # Update position
            current_pos = self.position()
            self.positionChanged.emit(current_pos)
            
            # Check if reached end
            if self._duration > 0 and current_pos >= self._duration:
                self.stop()
                self._media_status = QMediaPlayer.MediaStatus.EndOfMedia
                self.mediaStatusChanged.emit(self._media_status)
        
        except queue.Empty:
            # No frame available, continue
            pass
        
        # Output audio data - only write amount corresponding to one video frame
        if self._audio_io_device and self._audio_sink:
            try:
                # Calculate how much audio to write for one video frame
                # At 48kHz stereo s16: 48000 samples/sec * 2 channels * 2 bytes = 192000 bytes/sec
                frame_rate = 30
                if self._video_stream and self._video_stream.average_rate:
                    frame_rate = float(self._video_stream.average_rate)
                
                # Bytes per video frame at 48kHz stereo s16
                bytes_per_frame = int((48000 * 2 * 2) / frame_rate)
                
                # Write only the audio for this frame duration
                bytes_written = 0
                while bytes_written < bytes_per_frame and not self._audio_queue.empty():
                    try:
                        audio_data = self._audio_queue.get_nowait()
                        if self._audio_io_device.isOpen():
                            written = self._audio_io_device.write(audio_data)
                            bytes_written += len(audio_data)
                    except queue.Empty:
                        break
            except Exception as e:
                pass
