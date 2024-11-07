from typing import List, Tuple, Optional
import vlc
import tkinter as tk


class VideoPlayer:
    """
    A class representing a video player with position, size, and playback controls.
    """

    def __init__(
        self, player: vlc.MediaPlayer, x: int = 0, y: int = 0, w: int = 0, h: int = 0
    ):
        """
        Initializes a new instance of the VideoPlayer class.

        Args:
            player (vlc.MediaPlayer): The VLC media player instance.
            x (int, optional): The x-coordinate of the video player. Defaults to 0.
            y (int, optional): The y-coordinate of the video player. Defaults to 0.
            w (int, optional): The width of the video player. Defaults to 0.
            h (int, optional): The height of the video player. Defaults to 0.
        """
        # Position and size
        self.x: int = x  # X-coordinate
        self.y: int = y  # Y-coordinate
        self.w: int = w  # Width
        self.h: int = h  # Height

        # VLC player instance
        self.instance: Optional[vlc.Instance] = None
        self.player: vlc.MediaPlayer = player  # VLC media player instance
        self.panel: Optional[tk.Frame] = None
        self.offset: int = 0  # Offset for synchronization

        # Flags for dragging and resizing
        self.is_being_dragged: bool = False
        self.is_being_resized: bool = False
        self.resize_sides: List[bool] = [
            False,
            False,
            False,
            False,
        ]  # [Left, Top, Right, Bottom]

        # Control flags
        self.pause_for_frame: bool = False

    def area(self) -> Tuple[int, int, int, int]:
        """
        Returns the current area (position and size) of the video player.

        Returns:
            tuple: A tuple containing (x, y, width, height).
        """
        return self.x, self.y, self.w, self.h

    def set_area(self, video_panel: tk.Frame):
        """
        Updates the position and size attributes based on the given video panel.

        Args:
            video_panel (tk.Frame): The Tkinter frame representing the video panel.
        """
        self.x = video_panel.winfo_x()
        self.y = video_panel.winfo_y()
        self.w = video_panel.winfo_width()
        self.h = video_panel.winfo_height()

    def set_volume(self, value: int):
        """
        Sets the volume of the video player.

        Args:
            value (int): The volume level to set (0-100).
        """
        self.player.audio_set_volume(value)