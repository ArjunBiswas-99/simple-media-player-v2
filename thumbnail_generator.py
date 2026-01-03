"""
Thumbnail Generator - Background thread for extracting video thumbnails
Uses PyAV for efficient frame extraction with compressed storage in RAM
"""

import av
from PyQt6.QtCore import QThread, pyqtSignal, QByteArray, QBuffer
from PyQt6.QtGui import QPixmap, QImage
from queue import PriorityQueue, Empty
import time


class ThumbnailGenerator(QThread):
    """Background thread that generates video thumbnails with smart priority queue"""
    
    thumbnail_ready = pyqtSignal(float, bytes)  # timestamp, jpeg_bytes
    generation_complete = pyqtSignal()
    
    def __init__(self, video_path, duration):
        super().__init__()
        self.video_path = video_path
        self.duration = duration
        self.thumbnails = {}  # {timestamp: jpeg_bytes} - Compressed storage in RAM
        self.queue = PriorityQueue()
        self.running = True
        self.hover_position = None
        
        # Adaptive interval based on video length
        if duration < 600:  # <10 min
            self.interval = 3
        elif duration < 3600:  # 10-60 min
            self.interval = 5
        elif duration < 7200:  # 1-2 hours
            self.interval = 10
        else:  # >2 hours
            self.interval = 15
        
        # Calculate total thumbnails
        self.total_thumbnails = int(duration / self.interval)
        self.generated_count = 0
        
    def request_thumbnail(self, timestamp):
        """Request thumbnail at specific timestamp (user hover)"""
        self.hover_position = timestamp
        
        # Round to nearest interval for cache lookup
        nearest_interval = round(timestamp / self.interval) * self.interval
        
        # Add hover position with HIGH priority (0) if not cached
        if nearest_interval not in self.thumbnails:
            self.queue.put((0, nearest_interval))
            
            # Also add nearby thumbnails (±5 intervals for smoother scrubbing)
            for offset in range(-5, 6):
                if offset == 0:
                    continue
                nearby_ts = nearest_interval + (offset * self.interval)
                if 0 <= nearby_ts <= self.duration and nearby_ts not in self.thumbnails:
                    self.queue.put((1, nearby_ts))  # Medium priority
    
    def get_thumbnail(self, timestamp):
        """Get cached thumbnail (returns jpeg bytes or None)"""
        return self.thumbnails.get(timestamp)
    
    def get_nearest_thumbnail(self, timestamp):
        """Get nearest cached thumbnail within reasonable range"""
        # Try exact match first
        if timestamp in self.thumbnails:
            return self.thumbnails[timestamp]
        
        # Find nearest thumbnail within ±interval*2 range
        search_range = self.interval * 2
        nearest_ts = None
        min_distance = float('inf')
        
        for cached_ts in self.thumbnails.keys():
            distance = abs(cached_ts - timestamp)
            if distance < min_distance and distance <= search_range:
                min_distance = distance
                nearest_ts = cached_ts
        
        if nearest_ts is not None:
            return self.thumbnails[nearest_ts]
        
        return None
    
    def stop(self):
        """Stop generation thread"""
        self.running = False
        self.wait()
    
    def clear(self):
        """Clear all thumbnails from memory"""
        self.thumbnails.clear()
    
    def run(self):
        """Background thread main loop"""
        try:
            # Queue all sequential thumbnails with LOW priority (2)
            for i in range(self.total_thumbnails):
                timestamp = i * self.interval
                self.queue.put((2, timestamp))
            
            # Open video file
            container = av.open(self.video_path)
            video_stream = container.streams.video[0]
            
            while self.running and self.generated_count < self.total_thumbnails:
                try:
                    # Get next thumbnail to generate (priority-based)
                    priority, timestamp = self.queue.get(timeout=0.1)
                    
                    # Skip if already generated
                    if timestamp in self.thumbnails:
                        continue
                    
                    # Extract frame
                    jpeg_bytes = self._extract_frame(container, video_stream, timestamp)
                    
                    if jpeg_bytes:
                        # Store compressed in RAM
                        self.thumbnails[timestamp] = jpeg_bytes
                        self.generated_count += 1
                        
                        # Emit signal
                        self.thumbnail_ready.emit(timestamp, jpeg_bytes)
                    
                    # Rate limit: 20 thumbnails/second for high priority, 10/sec for sequential
                    if priority < 2:  # High/medium priority (hover-related)
                        time.sleep(0.05)  # 50ms = 20/sec
                    else:  # Low priority (sequential)
                        time.sleep(0.1)  # 100ms = 10/sec
                    
                except Empty:
                    continue
            
            container.close()
            self.generation_complete.emit()
            
        except Exception as e:
            print(f"Thumbnail generation error: {e}")
    
    def _extract_frame(self, container, stream, timestamp):
        """Extract single frame at timestamp and compress to JPEG"""
        try:
            # Seek to timestamp (convert seconds to AV_TIME_BASE units)
            seek_ts = int(timestamp * 1000000)  # Convert to microseconds
            container.seek(seek_ts, backward=True, any_frame=False)
            
            # Decode next frame
            for frame in container.decode(video=0):
                # Convert to PIL Image
                img = frame.to_image()
                
                # Resize to thumbnail size (160×90)
                img.thumbnail((160, 90))
                
                # Convert to QPixmap
                width, height = img.size
                img_data = img.convert('RGB').tobytes()
                qimage = QImage(img_data, width, height, width * 3, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                
                # Compress to JPEG bytes
                buffer = QByteArray()
                writer = QBuffer(buffer)
                writer.open(QBuffer.OpenModeFlag.WriteOnly)
                pixmap.save(writer, "JPEG", quality=85)
                
                return bytes(buffer.data())
                
        except Exception as e:
            print(f"Frame extraction error at {timestamp}s: {e}")
            return None
