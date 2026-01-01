"""
Constants for Netflix-inspired UI styling and configuration.
Centralizes all colors, dimensions, and animation timings for easy maintenance.
"""

# ==================== COLOR PALETTE ====================
# Netflix-inspired color scheme

class Colors:
    """Netflix color palette constants."""
    
    # Primary Colors
    BACKGROUND_OVERLAY = "rgba(0, 0, 0, 0.7)"
    CONTROL_BACKGROUND = "rgba(20, 20, 20, 0.9)"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#E5E5E5"
    
    # Accent Colors
    NETFLIX_RED = "#E50914"
    ACTIVE_RED = "#B20710"
    HOVER_GRAY = "rgba(255, 255, 255, 0.1)"
    
    # UI Elements
    PROGRESS_BAR_BACKGROUND = "rgba(255, 255, 255, 0.3)"
    PROGRESS_BAR_FILLED = "#E50914"
    PROGRESS_BAR_BUFFERED = "rgba(255, 255, 255, 0.5)"
    SCRUBBER_DOT = "#E50914"
    
    # Menu Bar
    MENU_BACKGROUND = "rgba(0, 0, 0, 0.95)"
    MENU_DROPDOWN_BACKGROUND = "rgba(20, 20, 20, 0.98)"
    MENU_HOVER = "rgba(229, 9, 20, 0.15)"
    MENU_BORDER = "rgba(255, 255, 255, 0.1)"
    MENU_SEPARATOR = "rgba(255, 255, 255, 0.1)"
    
    # Directory Panel
    PANEL_BACKGROUND = "rgba(20, 20, 20, 0.95)"
    PANEL_ITEM_HOVER = "rgba(255, 255, 255, 0.05)"
    PANEL_ITEM_ACTIVE = "rgba(229, 9, 20, 0.2)"


# ==================== DIMENSIONS ====================

class Dimensions:
    """Layout dimensions and spacing constants."""
    
    # Window
    DEFAULT_WINDOW_WIDTH = 1280
    DEFAULT_WINDOW_HEIGHT = 720
    
    # Control Bar
    CONTROL_BAR_HEIGHT = 80
    CONTROL_BAR_PADDING_H = 20
    CONTROL_BAR_PADDING_V = 16
    BUTTON_SPACING = 16
    
    # Progress Bar
    PROGRESS_BAR_HEIGHT = 4
    PROGRESS_BAR_HEIGHT_HOVER = 6
    PROGRESS_BAR_MARGIN = 12
    SCRUBBER_SIZE = 12
    SCRUBBER_SIZE_HOVER = 18
    
    # Top Bar
    TOP_BAR_HEIGHT = 60
    TOP_BAR_PADDING_H = 16
    
    # Menu Bar
    MENU_BAR_HEIGHT = 32
    MENU_ITEM_HEIGHT = 32
    MENU_MIN_WIDTH = 240
    MENU_PADDING = 8
    
    # Directory Panel
    PANEL_WIDTH = 320
    PANEL_ITEM_HEIGHT = 48
    PANEL_ITEM_PADDING = 12
    
    # Icons
    ICON_SIZE = 24
    ICON_SIZE_LARGE = 32


# ==================== ANIMATION TIMINGS ====================

class Timings:
    """Animation timing constants (in milliseconds)."""
    
    # Control Bar Fade
    FADE_IN = 200
    FADE_OUT = 300
    AUTO_HIDE_DELAY = 3000  # 3 seconds
    
    # Button Interactions
    HOVER_SCALE = 100
    CLICK_SCALE = 50
    COLOR_TRANSITION = 150
    
    # Progress Bar
    SCRUBBER_HOVER = 150
    PREVIEW_APPEAR = 200
    
    # Directory Panel
    PANEL_SLIDE_IN = 300
    PANEL_SLIDE_OUT = 250
    
    # Menu
    MENU_DROPDOWN_OPEN = 200
    MENU_HOVER_HIGHLIGHT = 150


# ==================== FONTS ====================

class Fonts:
    """Font configuration constants."""
    
    FAMILY = "Helvetica Neue, Arial, sans-serif"  # Cross-platform system fonts
    
    # Sizes
    VIDEO_TITLE = 18
    CONTROL_LABEL = 14
    TIME_STAMP = 14
    DIRECTORY_ITEM = 16
    MENU_ITEM = 14
    
    # Weights
    LIGHT = 300
    REGULAR = 400
    MEDIUM = 500
    BOLD = 700


# ==================== KEYBOARD SHORTCUTS ====================

class Shortcuts:
    """Keyboard shortcut mappings."""
    
    PLAY_PAUSE = "Space"
    STOP = "S"
    NEXT = "N"
    PREVIOUS = "P"
    
    # Seeking
    SEEK_FORWARD = "Right"
    SEEK_BACKWARD = "Left"
    SEEK_FORWARD_LONG = "Ctrl+Right"
    SEEK_BACKWARD_LONG = "Ctrl+Left"
    
    # Speed
    SPEED_SLOWER = "["
    SPEED_FASTER = "]"
    SPEED_NORMAL = "="
    
    # Display
    FULLSCREEN = "F"
    FULLSCREEN_INTERFACE = "F11"
    MINIMAL_INTERFACE = "Ctrl+H"
    ALWAYS_ON_TOP = "Ctrl+T"
    
    # Audio
    MUTE = "M"
    VOLUME_UP = "Up"
    VOLUME_DOWN = "Down"
    VOLUME_UP_ALT = "Ctrl+Up"
    VOLUME_DOWN_ALT = "Ctrl+Down"
    
    # File Operations
    OPEN_FILE = "Ctrl+O"
    OPEN_FOLDER = "Ctrl+F"
    OPEN_DIRECTORY = "Ctrl+D"
    PLAYLIST = "Ctrl+L"
    QUIT = "Ctrl+Q"
    
    # Tools
    EFFECTS_FILTERS = "Ctrl+E"
    MEDIA_INFO = "Ctrl+I"
    CODEC_INFO = "Ctrl+J"
    SNAPSHOT = "Shift+S"


# ==================== MOCK DATA ====================

class MockData:
    """Mock data for testing without MPV backend."""
    
    MOCK_FILES = [
        "video1.mp4",
        "video2.ts",
        "video3.mov",
        "movie.wmv",
        "audio1.mp3",
        "documentary.mpeg",
        "music.wav",
    ]
    
    MOCK_CURRENT_TIME = "0:45:23"
    MOCK_TOTAL_TIME = "1:32:45"
    MOCK_VIDEO_TITLE = "The Matrix"
    
    # Supported file extensions
    VIDEO_EXTENSIONS = [".mp4", ".mov", ".wmv", ".ts", ".mpeg"]
    AUDIO_EXTENSIONS = [".mp3", ".wav"]
