# Constants
EDGE_WIDTH = 10  # Width of the draggable edge for resizing
MIN_WIDTH = 100  # Minimum width for resizing
MIN_HEIGHT = 100  # Minimum height for resizing

OVERLAY_DURATION_SHORT = 500  # Duration in milliseconds for short overlay messages
OVERLAY_DURATION_LONG = 1500  # Duration in milliseconds for long overlay messages
OVERLAY_SIZE = 75  # Font size for overlay messages

# Time in milliseconds to wait before hiding controls
HIDE_CONTROLS_AFTER = 3000

# Default volume
DEFAULT_VOLUME = 75  # Volume level from 0 to 100

# Default initial positions and sizes for video players
VIDEO1_INITIAL_X = 50
VIDEO1_INITIAL_Y = 50
VIDEO1_INITIAL_WIDTH = 320
VIDEO1_INITIAL_HEIGHT = 240

VIDEO2_INITIAL_X = 400
VIDEO2_INITIAL_Y = 50
VIDEO2_INITIAL_WIDTH = 320
VIDEO2_INITIAL_HEIGHT = 240

# Synchronization parameters
SYNC_PARAMS = {
    'fft_bin_size': 1024,
    'overlap': 256,
    'lowcut': 100,
    'highcut': 4000,
    'maxes_per_box': 5,
    'sample_rate': 44100,
}

# Default video paths
DEFAULT_VIDEO1_PATH = r"assets/debug/MR. ROBOT 1×01.mp4"
DEFAULT_VIDEO2_PATH = r"assets/debug/Mr.Robot.S01E01.eps1.0.hellofriend.mov.1080p.10bit.BluRay.AAC5.1.HEVC-Vyndros.mkv"
