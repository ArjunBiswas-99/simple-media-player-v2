"""
File Manager Utility - Handle file operations and directory scanning.

Responsibilities:
- Scan directories for media files
- Filter files by supported formats
- Provide file path utilities
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import MockData


class FileManager:
    """
    Utility class for file operations.
    
    Responsibilities:
    - Scan directories for media files
    - Filter by supported extensions
    - Sort files naturally
    """
    
    @staticmethod
    def get_supported_extensions():
        """
        Get list of all supported file extensions.
        
        Returns:
            list: List of supported extensions (with dots)
        """
        return MockData.VIDEO_EXTENSIONS + MockData.AUDIO_EXTENSIONS
    
    @staticmethod
    def is_supported_file(filepath):
        """
        Check if file has a supported extension.
        
        Args:
            filepath: Path to file
            
        Returns:
            bool: True if supported, False otherwise
        """
        ext = os.path.splitext(filepath)[1].lower()
        return ext in FileManager.get_supported_extensions()
    
    @staticmethod
    def scan_directory(directory):
        """
        Scan a directory for supported media files.
        
        Args:
            directory: Path to directory
            
        Returns:
            list: List of absolute file paths to supported media files
        """
        if not os.path.isdir(directory):
            return []
        
        media_files = []
        
        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                
                # Only include files (not directories)
                if os.path.isfile(filepath):
                    if FileManager.is_supported_file(filepath):
                        media_files.append(filepath)
            
            # Sort files naturally
            media_files.sort()
            
        except Exception as e:
            print(f"Error scanning directory: {e}")
        
        return media_files
    
    @staticmethod
    def get_files_in_same_directory(filepath):
        """
        Get all supported media files in the same directory as the given file.
        
        Args:
            filepath: Path to a file
            
        Returns:
            list: List of absolute file paths in same directory
        """
        if not os.path.isfile(filepath):
            return []
        
        directory = os.path.dirname(filepath)
        return FileManager.scan_directory(directory)
    
    @staticmethod
    def format_time(seconds):
        """
        Format time in seconds to human-readable string.
        
        Args:
            seconds: Time in seconds (float)
            
        Returns:
            str: Formatted time string (H:MM:SS or M:SS)
        """
        if seconds is None or seconds < 0:
            return "0:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    @staticmethod
    def get_filename(filepath):
        """
        Get filename from path.
        
        Args:
            filepath: Full file path
            
        Returns:
            str: Filename without path
        """
        return os.path.basename(filepath)
    
    @staticmethod
    def get_file_extension(filepath):
        """
        Get file extension.
        
        Args:
            filepath: Full file path
            
        Returns:
            str: File extension (with dot)
        """
        return os.path.splitext(filepath)[1].lower()
