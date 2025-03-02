import os
import platform
from tkinter import messagebox
import settings
from align_videos_by_soundtrack import simple_html5_simult_player_builder
from align_videos_by_soundtrack.align_params import SyncDetectorSummarizerParams


def compute_offsets(video1_path, video2_path):
    """
    Computes the synchronization offsets between two videos.
    """
    # Parameters for synchronization from settings
    params = SyncDetectorSummarizerParams(**settings.SYNC_PARAMS)

    # Compute offsets
    offsets = simple_html5_simult_player_builder.get_video_offsets(
        video1_path, video2_path, params
    )
    print("Computed Offsets:")
    print(f"Video 1: {offsets[0]}s")
    print(f"Video 2: {offsets[1]}s")
    return offsets


def get_handle(video_panel):
    """
    Gets the window handle for the video panel.
    """
    handle = video_panel.winfo_id()
    if platform.system() == "Darwin":
        # For macOS, we might need to convert the handle to an integer
        from ctypes import c_void_p

        handle = c_void_p(int(handle))
    return handle


class SyncManager:
    """
    This class focuses on synchronization logic for the video players,
    handling offset calculations, seeking, and managing the play/pause state.
    """

    def __init__(self, root, player1, player2, video1_path, video2_path, event_manager):
        self.media1 = None
        self.media2 = None
        self.seek_bar = None
        self.user_is_seeking = None

        self.root = root
        self.player1 = player1
        self.player2 = player2
        self.event_manager = event_manager

        # Subscribe to events
        self.event_manager.subscribe("play_pause_both", self.play_pause_both)
        self.event_manager.subscribe("play_pause_single", self.play_pause_single)
        self.event_manager.subscribe("stop", self.stop)
        self.event_manager.subscribe("volume_changed", self.set_volume)
        self.event_manager.subscribe("seek", self.perform_seek)
        self.event_manager.subscribe("pause_for_frame", self.pause_for_frame)
        self.event_manager.subscribe("seek_relative", self.seek_relative)
        self.event_manager.subscribe("cycle_subtitles", self.cycle_subtitles)
        self.event_manager.subscribe("cycle_audio_tracks", self.cycle_audio_tracks)

        # Compute offsets
        self.offsets = compute_offsets(video1_path, video2_path)
        self.player1.offset = self.offsets[0]
        self.player2.offset = self.offsets[1]

        # Load videos
        self.load_videos(video1_path, video2_path)

    def load_videos(self, path1, path2):
        """
        Loads the video files into the players.
        """
        # Check if files exist
        if not os.path.exists(path1) or not os.path.exists(path2):
            messagebox.showerror("Error", "One or both video files do not exist.")
            return

        try:
            # Load media
            self.media1 = self.player1.instance.media_new(path1)
            self.player1.player.set_media(self.media1)
            self.media2 = self.player2.instance.media_new(path2)
            self.player2.player.set_media(self.media2)

            # Update the UI to ensure frames are realized
            self.root.update_idletasks()  # Ensures that all widgets are fully initialized

            # Set video output windows
            handle1 = get_handle(self.player1.panel)
            handle2 = get_handle(self.player2.panel)

            system = platform.system()
            if system == "Windows":
                self.player1.player.set_hwnd(handle1)
                self.player2.player.set_hwnd(handle2)
            elif system == "Linux":
                self.player1.player.set_xwindow(handle1)
                self.player2.player.set_xwindow(handle2)
            elif system == "Darwin":
                self.player1.player.set_nsobject(handle1)
                self.player2.player.set_nsobject(handle2)

            # Set initial positions based on offsets
            self.player1.player.play()
            self.player2.player.play()

            # Pause immediately after starting to set positions
            self.player1.player.pause()
            self.player2.player.pause()

            # Set positions
            self.player1.player.set_time(
                int(self.offsets[0] * 1000)
            )  # Convert to milliseconds
            self.player2.player.set_time(int(self.offsets[1] * 1000))

            # Set initial volume from settings
            self.player1.player.audio_set_volume(settings.DEFAULT_VOLUME)
            self.player2.player.audio_set_volume(settings.DEFAULT_VOLUME)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load videos: {e}")

    def perform_seek(self, time_seconds):
        """Performs the seek operation on both video players."""
        try:
            self.player1.seek(time_seconds)
            self.player2.seek(time_seconds)
        except Exception as e:
            print(f"Error performing seek: {e}")

    def on_seek_bar_release(self, event):
        """Called when the seek bar is released."""
        self.user_is_seeking = False
        self.event_manager.trigger("seek", self.seek_bar.get())

    def seek_relative(self, seconds):
        """Seeks both videos by a relative amount of time."""
        self.player1.seek_relative(seconds)
        self.player2.seek_relative(seconds)
        # Show seek feedback using OverlayManager
        direction = '⏪' if seconds < 0 else '⏩'
        message = f"{direction} {abs(seconds)}s"
        self.player1.overlay_manager.show_overlay(message, settings.OVERLAY_DURATION_SHORT)
        self.player2.overlay_manager.show_overlay(message, settings.OVERLAY_DURATION_SHORT)

    def cycle_subtitles(self, player_id):
        """Cycles subtitles for the specified player."""
        if player_id == 2:
            track_name = self.player2.cycle_subtitles()
            # Show subtitle track name using OverlayManager
            self.player2.overlay_manager.show_overlay(f"Subtitles: {track_name}", settings.OVERLAY_DURATION_LONG)

    def cycle_audio_tracks(self, player_id):
        """Cycles audio tracks for the specified player."""
        if player_id == 2:
            track_name = self.player2.cycle_audio_tracks()
            # Show audio track name using OverlayManager
            self.player2.overlay_manager.show_overlay(f"Audio: {track_name}", settings.OVERLAY_DURATION_LONG)

    def play_pause_single(self, player_id):
        """Toggles play/pause for a single player."""
        if player_id == 1:
            if self.player1.is_playing():
                self.player1.pause()
            else:
                self.player1.play()
        elif player_id == 2:
            if self.player2.is_playing():
                self.player2.pause()
            else:
                self.player2.play()

    def play_pause_both(self):
        """Toggles play/pause for both players."""
        if self.player1.is_playing() and self.player2.is_playing():
            self.player1.pause()
            self.player2.pause()
            # Trigger event to update play button text
            self.event_manager.trigger("play_pause_state_changed", "Play")
            # Show pause icon or text using OverlayManager
            self.player1.overlay_manager.show_overlay('⏸', settings.OVERLAY_DURATION_SHORT)
            self.player2.overlay_manager.show_overlay('⏸', settings.OVERLAY_DURATION_SHORT)
        else:
            self.player1.play()
            self.player2.play()
            self.event_manager.trigger("play_pause_state_changed", "Pause")
            # Show play icon or text using OverlayManager
            self.player1.overlay_manager.show_overlay('▶', settings.OVERLAY_DURATION_SHORT)
            self.player2.overlay_manager.show_overlay('▶', settings.OVERLAY_DURATION_SHORT)

    def stop(self):
        """Stops both players."""
        self.player1.stop()
        self.player2.stop()
        # Trigger event to update play button text
        self.event_manager.trigger("play_pause_state_changed", "Play")

    def set_volume(self, player_id, volume):
        """Sets the volume for the specified player."""
        if player_id == 1:
            self.player1.set_volume(volume)
        elif player_id == 2:
            self.player2.set_volume(volume)

    def pause_for_frame(self, player_id):
        """Pauses the video player for one frame."""
        if player_id == 1:
            player = self.player1
        elif player_id == 2:
            player = self.player2
        else:
            return

        # Pause the player for one frame
        player.set_pause(1)  # Pause the video

        # Advance by a single frame (simulate by very short pause)
        fps = player.get_fps()
        if fps <= 0:  # If fps can't be determined, assume 24 fps
            fps = 24

        frame_duration = 1 / fps  # Duration of one frame in seconds

        def unpause_player():
            player.set_pause(0)  # Unpause the video

        # Schedule the unpause after the frame duration
        self.root.after(int(frame_duration * 1000), unpause_player)
