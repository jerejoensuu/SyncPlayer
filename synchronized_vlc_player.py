import sys
import os
import platform
import tkinter as tk
from tkinter import filedialog, messagebox
import vlc
from pynput import mouse
from align_videos_by_soundtrack import simple_html5_simult_player_builder
from align_videos_by_soundtrack.align_params import SyncDetectorSummarizerParams

# Constants
EDGE_WIDTH = 10  # Width of the draggable edge for resizing
MIN_WIDTH = 100  # Minimum width for resizing
MIN_HEIGHT = 100  # Minimum height for resizing


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
        self.panel = None
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

    def set_volume(self, value):
        """
        Sets the volume of the video player.
        """
        self.player.audio_set_volume(int(value))


class SyncedPlayer:
    """
    A synchronized video player that plays two videos in sync.
    """

    def __init__(self, root, video1_path, video2_path):
        self.root = root
        self.root.title("Synchronized Video Player")

        # VLC instances
        self.instance1 = vlc.Instance("--no-video-title-show", "--aout=directsound")
        self.instance2 = vlc.Instance("--no-video-title-show", "--aout=directsound")

        # Create VideoPlayer instances
        self.player1 = VideoPlayer(
            self.instance1.media_player_new(), x=50, y=50, w=320, h=240
        )
        self.player1.instance = self.instance1
        self.player1.player.video_set_mouse_input(False)

        self.player2 = VideoPlayer(
            self.instance2.media_player_new(), x=400, y=50, w=320, h=240
        )
        self.player2.instance = self.instance2
        self.player2.player.video_set_mouse_input(False)

        # Compute offsets
        self.offsets = self.compute_offsets(video1_path, video2_path)
        self.player1.offset = self.offsets[0]
        self.player2.offset = self.offsets[1]

        # Variables
        self.drag_start = (0, 0)
        self.user_is_seeking = False

        self.controls_visible = True
        self.hide_controls_after = (
            3000  # Time in milliseconds to wait before hiding controls
        )
        self.hide_controls_job = None

        # Create UI elements
        self.create_ui()

        # Load videos
        self.load_videos(video1_path, video2_path)

        # Start mouse listener (for pynput)
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click, on_move=self.on_mouse_move, on_scroll=self.on_scroll
        )
        self.mouse_listener.start()

        # Ensure proper resource cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_control_panel_area(self, frame):
        """
        Returns the area of the control panel based on the given frame.
        """
        x, y = self.get_rel_coords(frame.winfo_rootx(), frame.winfo_rooty())
        width = frame.winfo_width()
        height = frame.winfo_height()
        return x, y, width, height

    def is_inside_any_control_panel(self, x, y):
        """
        Checks if the given coordinates are inside any of the control panels.
        """
        x, y = self.get_rel_coords(x, y)
        return (
            self.is_inside(x, y, self.get_control_panel_area(self.control_panel))
            or self.is_inside(x, y, self.get_control_panel_area(self.control_panel1))
            or self.is_inside(x, y, self.get_control_panel_area(self.control_panel2))
        )

    def create_ui(self):
        """
        Creates the UI elements for the synchronized video player.
        """
        # Video panel for video 1
        self.player1.panel = tk.Frame(
            self.root,
            bg="red",
            width=self.player1.area()[2],
            height=self.player1.area()[3],
        )
        self.player1.panel.place(x=self.player1.area()[0], y=self.player1.area()[1])

        # Video panel for video 2
        self.player2.panel = tk.Frame(
            self.root,
            bg="blue",
            width=self.player2.area()[2],
            height=self.player2.area()[3],
        )
        self.player2.panel.place(x=self.player2.area()[0], y=self.player2.area()[1])

        # Control panel for video 1
        self.control_panel1, self.volume_slider1 = self.create_video_controls(
            self.player1, "Video 1"
        )

        # Control panel for video 2
        self.control_panel2, self.volume_slider2 = self.create_video_controls(
            self.player2, "Video 2"
        )

        # Main control panel
        self.control_panel = tk.Frame(self.root)

        self.play_button = tk.Button(
            self.control_panel,
            text="Play/Pause Both Videos",
            command=self.play_pause_both,
        )
        self.play_button.pack(side=tk.LEFT)

        self.stop_button = tk.Button(self.control_panel, text="Stop", command=self.stop)
        self.stop_button.pack(side=tk.LEFT)

        # Time label for seek bar (min:sec display)
        self.time_label = tk.Label(self.control_panel, text="0:00 / 0:00")
        self.time_label.pack(side=tk.LEFT)

        # Seek bar (shared for both videos)
        self.seek_bar = tk.Scale(
            self.control_panel,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=400,
            command=self.on_seek_bar_move,
            showvalue=False,
        )
        self.seek_bar.pack(side=tk.LEFT)

        # Bind mouse events to handle user interaction with the seek bar
        self.seek_bar.bind("<ButtonPress-1>", self.on_seek_bar_press)
        self.seek_bar.bind("<ButtonRelease-1>", self.on_seek_bar_release)

        self.control_panel.pack()

        # Start the loop to update the seek bar
        self.update_seek_bar_loop()

    def create_video_controls(self, player, label_text):
        """
        Creates control panel for a video player.
        """
        control_panel = tk.Frame(self.root)
        volume_label = tk.Label(control_panel, text=f"Volume {label_text}")
        volume_label.pack(side=tk.LEFT)
        volume_slider = tk.Scale(
            control_panel,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=lambda value: player.set_volume(value),
        )
        volume_slider.set(50)  # Set default volume
        volume_slider.pack(side=tk.LEFT)

        play_button = tk.Button(
            control_panel,
            text=f"Play/Pause {label_text}",
            command=lambda: self.play_pause_single(player.player),
        )
        play_button.pack(side=tk.LEFT)

        frame_button = tk.Button(
            control_panel,
            text=f"Pause {label_text} for frame",
            command=lambda: self.pause_for_frame(player.player),
        )
        frame_button.pack(side=tk.LEFT)

        control_panel.pack()
        return control_panel, volume_slider

    def on_click(self, x, y, button, pressed):
        """
        Handles mouse click events.
        """
        if not self.is_within_app_window(x, y):
            return

        # Get the root window's position on the screen
        x_relative, y_relative = self.get_rel_coords(x, y)

        if pressed and button == mouse.Button.left:
            # Return if the click is on the control panel
            if self.is_inside_any_control_panel(x, y):
                return

            if self.is_inside(x_relative, y_relative, self.player2.area()):
                is_edge, self.player2.resize_sides = self.get_side(
                    x_relative, y_relative, self.player2.area()
                )
                if is_edge:
                    self.player2.is_being_resized = True
                    self.drag_start = (x_relative, y_relative)
                    self.player2.drag_start_x = self.player2.x
                    self.player2.drag_start_y = self.player2.y
                    self.player2.drag_start_w = self.player2.w
                    self.player2.drag_start_h = self.player2.h
                else:
                    self.player2.is_being_dragged = True
                    self.drag_start = (x_relative, y_relative)
                    self.player2.drag_start_x = self.player2.x
                    self.player2.drag_start_y = self.player2.y

            elif self.is_inside(x_relative, y_relative, self.player1.area()):
                is_edge, self.player1.resize_sides = self.get_side(
                    x_relative, y_relative, self.player1.area()
                )
                if is_edge:
                    self.player1.is_being_resized = True
                    self.drag_start = (x_relative, y_relative)
                    self.player1.drag_start_x = self.player1.x
                    self.player1.drag_start_y = self.player1.y
                    self.player1.drag_start_w = self.player1.w
                    self.player1.drag_start_h = self.player1.h
                else:
                    self.player1.is_being_dragged = True
                    self.drag_start = (x_relative, y_relative)
                    self.player1.drag_start_x = self.player1.x
                    self.player1.drag_start_y = self.player1.y

        else:
            self.release_dragging()

    def release_dragging(self):
        """
        Releases dragging and resizing of the video players.
        """
        self.player1.is_being_dragged = False
        self.player1.is_being_resized = False
        self.player1.set_area(self.player1.panel)

        self.player2.is_being_dragged = False
        self.player2.is_being_resized = False
        self.player2.set_area(self.player2.panel)

    def on_mouse_move(self, x, y):
        """
        Handles mouse move events.
        """
        if x is None or y is None:
            return

        if not self.is_within_app_window(x, y):
            self.release_dragging()
            return

        x_relative, y_relative = self.get_rel_coords(x, y)

        # Show controls if they are hidden
        if not self.controls_visible:
            self.show_controls()

        # Cancel any previous scheduled hiding
        if self.hide_controls_job is not None:
            self.root.after_cancel(self.hide_controls_job)

        # Schedule the controls to be hidden after inactivity
        self.hide_controls_job = self.root.after(
            self.hide_controls_after, self.hide_controls
        )

        if self.player1.is_being_dragged:
            self.drag_player(self.player1, x_relative, y_relative)

        if self.player2.is_being_dragged:
            self.drag_player(self.player2, x_relative, y_relative)

        if self.player1.is_being_resized:
            self.resize_player(self.player1, x_relative, y_relative)

        if self.player2.is_being_resized:
            self.resize_player(self.player2, x_relative, y_relative)

    def on_scroll(self, x, y, dx, dy):
        """
        Handles mouse scroll events for volume control.
        """
        if not self.is_within_app_window(x, y):
            return

        # Return if the click is on the control panel
        if self.is_inside_any_control_panel(x, y):
            return

        x_relative, y_relative = self.get_rel_coords(x, y)

        if self.is_inside(x_relative, y_relative, self.player2.area()):
            new_volume = self.player2.player.audio_get_volume() + dy
            self.player2.set_volume(new_volume)
            self.volume_slider2.set(new_volume)
        elif self.is_inside(x_relative, y_relative, self.player1.area()):
            new_volume = self.player1.player.audio_get_volume() + dy
            self.player1.set_volume(new_volume)
            self.volume_slider1.set(new_volume)

    def is_within_app_window(self, x, y):
        """
        Checks if the given screen coordinates are within the application window.
        """
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        width = self.root.winfo_width()
        height = self.root.winfo_height()

        return root_x <= x <= root_x + width and root_y <= y <= root_y + height

    def hide_controls(self):
        """
        Hides the control panels.
        """
        self.control_panel1.pack_forget()
        self.control_panel2.pack_forget()
        self.control_panel.pack_forget()
        self.controls_visible = False

    def show_controls(self):
        """
        Shows the control panels.
        """
        self.control_panel1.pack()
        self.control_panel2.pack()
        self.control_panel.pack()
        self.controls_visible = True

    def drag_player(self, player, x_current, y_current):
        """
        Drags the player to a new position.
        """
        dx = x_current - self.drag_start[0]
        dy = y_current - self.drag_start[1]
        new_x = player.drag_start_x + dx
        new_y = player.drag_start_y + dy
        player.panel.place(x=new_x, y=new_y)
        player.set_area(player.panel)

    def resize_player(self, player, x_current, y_current):
        """
        Resizes the player.
        """
        dx = x_current - self.drag_start[0]
        dy = y_current - self.drag_start[1]

        # Initialize new positions and sizes with starting values
        new_x = player.drag_start_x
        new_y = player.drag_start_y
        new_w = player.drag_start_w
        new_h = player.drag_start_h

        # Horizontal resizing
        if player.resize_sides[0]:  # Left edge
            new_x = player.drag_start_x + dx
            new_w = player.drag_start_w - dx
        elif player.resize_sides[2]:  # Right edge
            new_w = player.drag_start_w + dx

        # Vertical resizing
        if player.resize_sides[1]:  # Top edge
            new_y = player.drag_start_y + dy
            new_h = player.drag_start_h - dy
        elif player.resize_sides[3]:  # Bottom edge
            new_h = player.drag_start_h + dy

        # Apply constraints if needed (e.g., minimum width/height)
        if new_w < MIN_WIDTH:
            new_w = MIN_WIDTH
            if player.resize_sides[0]:  # Adjust position if resizing from left
                new_x = player.drag_start_x + (player.drag_start_w - MIN_WIDTH)
        if new_h < MIN_HEIGHT:
            new_h = MIN_HEIGHT
            if player.resize_sides[1]:  # Adjust position if resizing from top
                new_y = player.drag_start_y + (player.drag_start_h - MIN_HEIGHT)

        player.panel.place(x=new_x, y=new_y, width=new_w, height=new_h)
        player.set_area(player.panel)

    def is_inside(self, x, y, area):
        """
        Checks if a point is inside a given area.
        """
        x1, y1, w, h = area
        return x1 <= x <= x1 + w and y1 <= y <= y1 + h

    def get_side(self, x, y, area):
        """
        Determines which side of the area the point is near for resizing.
        """
        x1, y1, w, h = area
        edges = [False, False, False, False]  # Left, Top, Right, Bottom

        # Left edge
        if x1 <= x <= x1 + EDGE_WIDTH and y1 <= y <= y1 + h:
            edges[0] = True
        # Top edge
        if x1 <= x <= x1 + w and y1 <= y <= y1 + EDGE_WIDTH:
            edges[1] = True
        # Right edge
        if x1 + w - EDGE_WIDTH <= x <= x1 + w and y1 <= y <= y1 + h:
            edges[2] = True
        # Bottom edge
        if x1 <= x <= x1 + w and y1 + h - EDGE_WIDTH <= y <= y1 + h:
            edges[3] = True

        return any(edges), edges

    def get_rel_coords(self, x, y):
        """
        Converts screen coordinates to window-relative coordinates.
        """
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        return x - root_x, y - root_y

    def pause_for_frame(self, player):
        """
        Pauses the video player for one frame.
        """
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

    def on_seek_bar_press(self, event):
        """
        Called when the seek bar is pressed.
        """
        self.user_is_seeking = True

    def on_seek_bar_release(self, event):
        """
        Called when the seek bar is released.
        """
        self.user_is_seeking = False
        self.perform_seek()

    def on_seek_bar_move(self, value):
        """
        Called when the seek bar is moved.
        """
        if self.user_is_seeking:
            self.seek_bar.set(int(float(value)))  # Ensure the value is an integer

    def perform_seek(self):
        """
        Performs the seek operation on both video players.
        """
        try:
            value = self.seek_bar.get()
            # Set time directly in seconds
            time_ms = value * 1000  # Convert seconds back to milliseconds
            self.player1.player.set_time(time_ms)
            self.player2.player.set_time(time_ms)
        except Exception as e:
            print(f"Error performing seek: {e}")

    def update_seek_bar_loop(self):
        """
        Updates the seek bar periodically.
        """
        try:
            if not self.user_is_seeking:
                # Get current time of video1
                current_time = self.player1.player.get_time()  # in ms
                total_length = self.player1.player.get_length()  # in ms

                if total_length > 0:
                    # Convert times to seconds
                    total_length_sec = total_length // 1000  # Convert to seconds
                    current_time_sec = current_time // 1000  # Convert to seconds

                    # Update the seek bar's range and position
                    self.seek_bar.config(
                        from_=0, to=total_length_sec
                    )  # Set the range based on video length
                    self.seek_bar.set(current_time_sec)

                    # Update the time label (min:sec / min:sec)
                    current_time_str = self.format_time(current_time)
                    total_length_str = self.format_time(total_length)
                    self.time_label.config(
                        text=f"{current_time_str} / {total_length_str}"
                    )

        except Exception as e:
            print(f"Error updating seek bar: {e}")

        # Schedule the next update after 1000 ms
        self.root.after(1000, self.update_seek_bar_loop)

    def format_time(self, milliseconds):
        """
        Formats time in milliseconds to a min:sec string.
        """
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"

    def compute_offsets(self, video1_path, video2_path):
        """
        Computes the synchronization offsets between two videos.
        """
        # Parameters for synchronization
        params = SyncDetectorSummarizerParams(
            fft_bin_size=1024,
            overlap=256,
            lowcut=100,
            highcut=4000,
            maxes_per_box=5,
            sample_rate=44100,
        )

        # Compute offsets
        offsets = simple_html5_simult_player_builder.get_video_offsets(
            video1_path, video2_path, params
        )
        print("Computed Offsets:")
        print(f"Video 1: {offsets[0]}s")
        print(f"Video 2: {offsets[1]}s")
        return offsets

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
            self.media1 = self.instance1.media_new(path1)
            self.player1.player.set_media(self.media1)
            self.media2 = self.instance2.media_new(path2)
            self.player2.player.set_media(self.media2)

            # Set video output windows
            handle1 = self.get_handle(self.player1.panel)
            handle2 = self.get_handle(self.player2.panel)

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

            # Set initial volume
            self.player1.player.audio_set_volume(self.volume_slider1.get())
            self.player2.player.audio_set_volume(self.volume_slider2.get())

            # Update play button text
            self.play_button.config(text="Play")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load videos: {e}")

    def play_pause_single(self, player):
        """
        Toggles play/pause for a single player.
        """
        player.pause()

    def play_pause_both(self):
        """
        Toggles play/pause for both players.
        """
        if self.player1.player.is_playing() and self.player2.player.is_playing():
            self.player1.player.pause()
            self.player2.player.pause()
            self.play_button.config(text="Play")
        else:
            self.player1.player.play()
            self.player2.player.play()
            self.play_button.config(text="Pause")

    def stop(self):
        """
        Stops both players.
        """
        self.player1.player.stop()
        self.player2.player.stop()
        self.play_button.config(text="Play")

    def sync_videos(self):
        """
        Synchronizes the videos based on their offsets.
        """
        base_time = self.player1.player.get_time() / 1000.0  # Convert to seconds
        position1 = base_time
        position2 = base_time + (self.player2.offset - self.player1.offset)

        self.player1.player.set_time(int(position1 * 1000))
        self.player2.player.set_time(int(position2 * 1000))

    def get_handle(self, video_panel):
        """
        Gets the window handle for the video panel.
        """
        return video_panel.winfo_id()

    def on_closing(self):
        """
        Handles the window closing event.
        """
        # Release VLC instances
        self.player1.player.stop()
        self.player2.player.stop()
        self.player1.instance.release()
        self.player2.instance.release()

        # Stop the mouse listener
        self.mouse_listener.stop()

        # Destroy the root window
        self.root.destroy()

        # Exit the program
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script_name.py video1_path video2_path")
        sys.exit(1)

    video1_path = sys.argv[1]
    video2_path = sys.argv[2]

    root = tk.Tk()
    player = SyncedPlayer(root, video1_path, video2_path)
    root.mainloop()
