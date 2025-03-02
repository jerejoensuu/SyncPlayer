import tkinter as tk
from typing import Optional
from overlay_manager import OverlayManager
import vlc


class VideoPlayer:
    """
    A class representing a video player with position, size, and playback controls.
    """

    def __init__(self, player, x=0, y=0, w=0, h=0):
        """
        Initializes a new instance of the VideoPlayer class.
        """
        # Position and size
        self.x = x  # X-coordinate
        self.y = y  # Y-coordinate
        self.w = w  # Width
        self.h = h  # Height

        # VLC player instance
        self.instance = None
        self.player = player  # VLC media player instance
        self.panel: Optional[tk.Frame] = None
        self.offset = 0  # Offset for synchronization

        # Flags for dragging and resizing
        self.is_being_dragged = False
        self.is_being_resized = False
        self.resize_sides = [False, False, False, False]  # [Left, Top, Right, Bottom]

        # Control flags
        self.pause_for_frame = False

        # Variables to store initial positions and sizes during drag/resize
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_w = 0
        self.drag_start_h = 0

        self.overlay_manager: Optional[OverlayManager] = OverlayManager(self)

    def create_panel(self, root, bg_color="black"):
        """
        Creates the Tkinter frame (panel) for the video player.
        """
        self.panel = tk.Frame(
            root,
            bg=bg_color,
            width=self.w,
            height=self.h,
        )
        self.panel.place(x=self.x, y=self.y)

        # Ensure the panel's geometry is updated
        self.panel.update_idletasks()

    def show_osd_message(self, message: str, duration: int = 1000):
        """
        Displays an OSD message using VLC's built-in functionality.
        """
        # Use the marquee filter to display the message
        self.player.video_set_marquee_int(vlc.VideoMarqueeOption.Enable, 1)
        self.player.video_set_marquee_int(vlc.VideoMarqueeOption.Timeout, duration)
        self.player.video_set_marquee_int(vlc.VideoMarqueeOption.Size, 24)
        self.player.video_set_marquee_int(
            vlc.VideoMarqueeOption.Position, vlc.Position.Center
        )
        self.player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, message)

    def area(self):
        """
        Returns the current area (position and size) of the video player.
        """
        return self.x, self.y, self.w, self.h

    def set_area(self, video_panel):
        """
        Updates the position and size attributes based on the given video panel.
        """
        self.x = video_panel.winfo_x()
        self.y = video_panel.winfo_y()
        self.w = video_panel.winfo_width()
        self.h = video_panel.winfo_height()

    # High-level methods abstracting VLC functionalities
    def play(self):
        """Starts or resumes playback."""
        self.player.play()

    def pause(self):
        """Pauses playback."""
        self.player.pause()

    def stop(self):
        """Stops playback."""
        self.player.stop()

    def set_volume(self, value):
        """Sets the volume of the video player."""
        self.player.audio_set_volume(int(value))

    def toggle_mute(self):
        """Toggles mute state."""
        self.player.audio_toggle_mute()

    def set_mute(self, mute: bool):
        """Sets mute state."""
        self.player.audio_set_mute(mute)

    def is_muted(self) -> bool:
        """Checks if the player is muted."""
        return self.player.audio_get_mute()

    def get_volume(self) -> int:
        """Gets the current volume."""
        return self.player.audio_get_volume()

    def seek(self, time_seconds: float):
        """Seeks to a specific time in seconds."""
        self.player.set_time(int(time_seconds * 1000))  # Convert to milliseconds

    def seek_relative(self, seconds):
        """Seeks by a relative amount of time."""
        try:
            current_time = self.get_time() / 1000  # Convert to seconds
            new_time = current_time + seconds
            # Ensure new time is within bounds
            new_time = max(0, min(new_time, self.get_length() / 1000))
            self.seek(new_time)
        except Exception as e:
            print(f"Error performing relative seek: {e}")

    def get_time(self) -> int:
        """Gets the current playback time in milliseconds."""
        return self.player.get_time()

    def get_length(self) -> int:
        """Gets the total length of the media in milliseconds."""
        return self.player.get_length()

    def set_position(self, x: int, y: int, width: int, height: int):
        """Sets the position and size of the video panel."""
        self.x = x
        self.y = y
        self.w = width
        self.h = height
        if self.panel:
            self.panel.place(x=self.x, y=self.y, width=self.w, height=self.h)

    def set_media(self, media):
        """Sets the media for the player."""
        self.player.set_media(media)

    def set_hwnd(self, hwnd):
        """Sets the window handle for video output (Windows)."""
        self.player.set_hwnd(hwnd)

    def set_xwindow(self, xwindow):
        """Sets the window handle for video output (Linux)."""
        self.player.set_xwindow(xwindow)

    def set_nsobject(self, nsobject):
        """Sets the window handle for video output (macOS)."""
        self.player.set_nsobject(nsobject)

    def set_mouse_input(self, state: bool):
        """Enables or disables mouse input."""
        self.player.video_set_mouse_input(state)

    def set_key_input(self, state: bool):
        """Enables or disables key input."""
        self.player.video_set_key_input(state)

    def set_time(self, milliseconds: int):
        """Sets the playback time in milliseconds."""
        self.player.set_time(milliseconds)

    def get_fps(self) -> float:
        """Gets the frames per second of the current media."""
        return self.player.get_fps()

    def is_playing(self) -> bool:
        """Checks if the player is currently playing."""
        return self.player.is_playing()

    def set_pause(self, pause: bool):
        """Pauses or resumes playback."""
        self.player.set_pause(pause)

    def cycle_subtitles(self):
        """Cycles through available subtitle tracks and returns the selected track's name."""
        try:
            track_descriptions = self.player.video_get_spu_description()
            if track_descriptions:
                # Extract IDs and names
                track_ids = [desc[0] for desc in track_descriptions]
                track_names = [desc[1].decode('utf-8') if isinstance(desc[1], bytes) else desc[1] for desc in track_descriptions]
                current_id = self.player.video_get_spu()

                # Find the next track ID and name
                if current_id in track_ids:
                    idx = track_ids.index(current_id)
                    next_idx = (idx + 1) % len(track_ids)
                else:
                    next_idx = 0  # Default to the first track if no match

                next_id = track_ids[next_idx]
                next_name = track_names[next_idx]

                # Set the next subtitle track
                self.player.video_set_spu(next_id)

                print(f"Subtitle track set to: {next_name}")
                return next_name  # Return the name of the selected subtitle track

        except Exception as e:
            print(f"Error cycling subtitles: {e}")
            return None

    def cycle_audio_tracks(self):
        """Cycles through available audio tracks and returns the selected track's name."""
        try:
            track_descriptions = self.player.audio_get_track_description()
            if track_descriptions:
                # Extract IDs and names
                track_ids = [desc[0] for desc in track_descriptions]
                track_names = [desc[1].decode('utf-8') if isinstance(desc[1], bytes) else desc[1] for desc in track_descriptions]
                current_id = self.player.audio_get_track()

                # Find the next track ID and name
                if current_id in track_ids:
                    idx = track_ids.index(current_id)
                    next_idx = (idx + 1) % len(track_ids)
                else:
                    next_idx = 0  # Default to the first track if no match

                next_id = track_ids[next_idx]
                next_name = track_names[next_idx]

                # Set the next audio track
                self.player.audio_set_track(next_id)

                print(f"Audio track set to: {next_name}")
                return next_name  # Return the name of the selected audio track

        except Exception as e:
            print(f"Error cycling audio tracks: {e}")
            return None
