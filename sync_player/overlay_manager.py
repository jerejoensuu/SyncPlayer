import tkinter as tk
from typing import Optional
import vlc
import settings


class OverlayManager:
    """
    Manages overlay messages on the video player using VLC's OSD features.
    """

    def __init__(self, video_player):
        self.video_player = video_player  # Reference to the VideoPlayer instance
        self.overlay_job = None  # Job handle for overlay timing

    def show_overlay(self, message: str, duration: int = 1000):
        """
        Displays an overlay message using VLC's OSD functionality.
        """
        print(f"Showing overlay: {message}")
        # Cancel any existing overlay job
        self.hide_overlay()

        # Set up the marquee (OSD) options
        self.video_player.player.video_set_marquee_int(vlc.VideoMarqueeOption.Enable, 1)
        self.video_player.player.video_set_marquee_int(
            vlc.VideoMarqueeOption.Timeout, duration
        )
        self.video_player.player.video_set_marquee_int(vlc.VideoMarqueeOption.Size, settings.OVERLAY_SIZE)
        self.video_player.player.video_set_marquee_int(
            vlc.VideoMarqueeOption.Position, vlc.Position.center.value
        )
        self.video_player.player.video_set_marquee_int(
            vlc.VideoMarqueeOption.Opacity, 255
        )  # Fully opaque
        self.video_player.player.video_set_marquee_int(
            vlc.VideoMarqueeOption.Refresh, 1000
        )  # Refresh rate
        self.video_player.player.video_set_marquee_string(
            vlc.VideoMarqueeOption.Text, message
        )

        # Schedule the overlay to be hidden after the duration
        self.overlay_job = self.video_player.panel.after(duration, self.hide_overlay)

    def hide_overlay(self):
        """
        Hides the overlay message.
        """
        print("Hiding overlay")
        self.video_player.player.video_set_marquee_int(vlc.VideoMarqueeOption.Enable, 0)
        if self.overlay_job:
            self.video_player.panel.after_cancel(self.overlay_job)
            self.overlay_job = None
