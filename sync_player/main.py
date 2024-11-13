import sys
import os

# Adjust the system path to include the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tkinter as tk
import vlc

# Local application imports
import settings
from video_player import VideoPlayer
from ui_manager import UIManager
from sync_manager import SyncManager
from event_manager import EventManager


class SyncedPlayer:
    """
    The main application class that initializes the players, UIManager, and SyncManager.
    """

    def __init__(self, root, video1_path, video2_path):
        self.root = root
        self.root.title("Synchronized Video Player")

        # Initialize EventManager
        self.event_manager = EventManager()

        # VLC instances
        self.instance1 = vlc.Instance("--no-video-title-show")
        self.instance2 = vlc.Instance("--no-video-title-show")

        # Create VideoPlayer instances
        self.player1 = VideoPlayer(
            self.instance1.media_player_new(),
            x=settings.VIDEO1_INITIAL_X,
            y=settings.VIDEO1_INITIAL_Y,
            w=settings.VIDEO1_INITIAL_WIDTH,
            h=settings.VIDEO1_INITIAL_HEIGHT,
        )
        self.player1.instance = self.instance1

        self.player2 = VideoPlayer(
            self.instance2.media_player_new(),
            x=settings.VIDEO2_INITIAL_X,
            y=settings.VIDEO2_INITIAL_Y,
            w=settings.VIDEO2_INITIAL_WIDTH,
            h=settings.VIDEO2_INITIAL_HEIGHT,
        )
        self.player2.instance = self.instance2

        # Set mouse and key input settings
        self.player1.player.video_set_mouse_input(False)
        self.player1.player.video_set_key_input(False)
        self.player2.player.video_set_mouse_input(False)
        self.player2.player.video_set_key_input(False)

        # Create panels for the video players
        self.player1.create_panel(self.root, bg_color="red")
        self.player2.create_panel(self.root, bg_color="blue")

        # Initialize SyncManager with event_manager
        self.sync_manager = SyncManager(
            self.root,
            self.player1,
            self.player2,
            video1_path,
            video2_path,
            self.event_manager,
        )

        # Initialize UIManager with event_manager
        self.ui_manager = UIManager(
            self.root, self.player1, self.player2, self.sync_manager, self.event_manager
        )

        # Ensure proper resource cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.ui_manager.on_closing)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        video1_path = settings.DEFAULT_VIDEO1_PATH
        video2_path = settings.DEFAULT_VIDEO2_PATH
    else:
        video1_path = sys.argv[1]
        video2_path = sys.argv[2]

    root = tk.Tk()
    player = SyncedPlayer(root, video1_path, video2_path)
    root.mainloop()
