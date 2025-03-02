import sys
import tkinter as tk
from pynput import mouse
import settings
import ctypes
import ctypes.wintypes


def is_inside(x, y, area):
    """
    Checks if a point is inside a given area.
    """
    x1, y1, w, h = area
    return x1 <= x <= x1 + w and y1 <= y <= y1 + h


def get_side(x, y, area):
    """
    Determines which side of the area the point is near for resizing.
    """
    x1, y1, w, h = area
    edges = [False, False, False, False]  # Left, Top, Right, Bottom

    # Left edge
    if x1 <= x <= x1 + settings.EDGE_WIDTH and y1 <= y <= y1 + h:
        edges[0] = True
    # Top edge
    if x1 <= x <= x1 + w and y1 <= y <= y1 + settings.EDGE_WIDTH:
        edges[1] = True
    # Right edge
    if x1 + w - settings.EDGE_WIDTH <= x <= x1 + w and y1 <= y <= y1 + h:
        edges[2] = True
    # Bottom edge
    if x1 <= x <= x1 + w and y1 + h - settings.EDGE_WIDTH <= y <= y1 + h:
        edges[3] = True

    return any(edges), edges


class UIManager:
    """
    This class manages the tkinter UI, including the control panels,
    event handling for user interactions, layout, and volume/seek controls.
    """

    def __init__(self, root, player1, player2, sync_manager, event_manager):
        self.seek_bar = None
        self.time_label = None
        self.stop_button = None
        self.play_button = None
        self.volume_slider1 = None
        self.volume_slider2 = None
        self.control_panel = None
        self.control_panel1 = None
        self.control_panel2 = None

        self.root = root
        self.player1 = player1
        self.player2 = player2
        self.sync_manager = sync_manager
        self.event_manager = event_manager

        # Variables
        self.controls_visible = True
        self.hide_controls_after = settings.HIDE_CONTROLS_AFTER
        self.hide_controls_job = None

        self.drag_start = (0, 0)
        self.user_is_seeking = False

        # Create UI elements
        self.create_ui()

        # Subscribe to the 'play_pause_state_changed' event
        self.event_manager.subscribe(
            "play_pause_state_changed", self.update_play_button
        )

        # Start the loop to update the seek bar
        self.update_seek_bar_loop()

        # Start mouse listener (for pynput)
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click, on_move=self.on_mouse_move, on_scroll=self.on_scroll
        )
        self.mouse_listener.start()

        # Bind key events to the root window
        self.root.bind("<Key>", self.on_key_press)
        self.root.focus_set()  # Ensure the root window has focus

    def on_key_press(self, event):
        """
        Handles key press events.
        """
        key = event.keysym.lower()
        if key in ("space", "k"):
            # Pause/play both videos
            self.event_manager.trigger("play_pause_both")
        elif key == "left":
            # Seek backward 5 seconds
            self.event_manager.trigger("seek_relative", -5)
        elif key == "right":
            # Seek forward 5 seconds
            self.event_manager.trigger("seek_relative", 5)
        elif key == "j":
            # Seek backward 10 seconds
            self.event_manager.trigger("seek_relative", -10)
        elif key == "l":
            # Seek forward 10 seconds
            self.event_manager.trigger("seek_relative", 10)
        elif key == "v":
            # Cycle subtitles in video 2
            self.event_manager.trigger("cycle_subtitles", player_id=2)
        elif key == "b":
            # Cycle audio tracks in video 2
            self.event_manager.trigger("cycle_audio_tracks", player_id=2)

    def create_ui(self):
        """
        Creates the UI elements for the synchronized video player.
        """
        # Control panel for video 1
        self.control_panel1, self.volume_slider1 = self.create_video_controls("Video 1", player_id=1)

        # Control panel for video 2
        self.control_panel2, self.volume_slider2 = self.create_video_controls("Video 2", player_id=2)

        # Main control panel
        self.control_panel = tk.Frame(self.root)

        self.play_button = tk.Button(
            self.control_panel,
            text="Play",
            command=lambda: self.event_manager.trigger("play_pause_both"),
        )
        self.play_button.pack(side=tk.LEFT)

        self.stop_button = tk.Button(
            self.control_panel, text="Stop", command=self.sync_manager.stop
        )
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

    def create_video_controls(self, label_text, player_id):
        control_panel = tk.Frame(self.root)
        volume_label = tk.Label(control_panel, text=f"Volume {label_text}")
        volume_label.pack(side=tk.LEFT)
        volume_slider = tk.Scale(
            control_panel,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=lambda value: self.event_manager.trigger(
                "volume_changed", player_id, int(value)
            ),
        )
        volume_slider.set(settings.DEFAULT_VOLUME)
        volume_slider.pack(side=tk.LEFT)

        play_button = tk.Button(
            control_panel,
            text=f"Play/Pause {label_text}",
            command=lambda: self.event_manager.trigger("play_pause_single", player_id),
        )
        play_button.pack(side=tk.LEFT)

        frame_button = tk.Button(
            control_panel,
            text=f"Pause {label_text} for frame",
            command=lambda: self.event_manager.trigger("pause_for_frame", player_id),
        )
        frame_button.pack(side=tk.LEFT)

        control_panel.pack()
        return control_panel, volume_slider

    def update_play_button(self, text):
        """
        Updates the main play button text.
        """
        self.play_button.config(text=text)

    def is_mouse_over_app(self, x, y):
        """
        Determines if the point (x, y) is over the SyncPlayer window or any of its children.
        """
        user32 = ctypes.windll.user32
        point = ctypes.wintypes.POINT(x, y)
        hwnd_at_point = user32.WindowFromPoint(point)

        # Check if the hwnd_at_point is either the root or a child of the root
        root_hwnd = self.root.winfo_id()
        is_child = user32.IsChild(root_hwnd, hwnd_at_point)

        return (hwnd_at_point == root_hwnd) or is_child

    def on_click(self, x, y, button, pressed):
        """
        Handles mouse click events.
        """
        if pressed and button == mouse.Button.left:
            if not self.is_mouse_over_app(x, y):
                return

            # Get the root window's relative coordinates
            x_relative, y_relative = self.get_rel_coords(x, y)

            # Return if the click is on the control panel
            if self.is_inside_any_control_panel(x, y):
                return

            # Nested helper to handle drag or resize logic for a given player
            def handle_drag_or_resize(player):
                is_edge, player.resize_sides = get_side(x_relative, y_relative, player.area())
                # Set a common drag start point and initial drag coordinates
                self.drag_start = (x_relative, y_relative)
                player.drag_start_x = player.x
                player.drag_start_y = player.y
                if is_edge:
                    player.is_being_resized = True
                    player.drag_start_w = player.w
                    player.drag_start_h = player.h
                else:
                    player.is_being_dragged = True

            # Determine which player's area was clicked and apply the logic.
            if is_inside(x_relative, y_relative, self.player2.area()):
                handle_drag_or_resize(self.player2)
            elif is_inside(x_relative, y_relative, self.player1.area()):
                handle_drag_or_resize(self.player1)

        else:
            # Always release dragging, even if the mouse is outside the window.
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

        x_relative, y_relative = self.get_rel_coords(x, y)

        if self.is_mouse_over_app(x, y):
            self.wake_controls()

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
        if not self.is_mouse_over_app(x, y):
            return

        # Return if the click is on the control panel
        if self.is_inside_any_control_panel(x, y):
            return

        x_relative, y_relative = self.get_rel_coords(x, y)

        if is_inside(x_relative, y_relative, self.player2.area()):
            new_volume = self.player2.player.audio_get_volume() + dy
            self.player2.set_volume(new_volume)
            self.volume_slider2.set(new_volume)
        elif is_inside(x_relative, y_relative, self.player1.area()):
            new_volume = self.player1.player.audio_get_volume() + dy
            self.player1.set_volume(new_volume)
            self.volume_slider1.set(new_volume)

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

    def wake_controls(self):
        """
        Wakes up the control panels and resets the timer.
        """
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

        self.event_manager.trigger("video_dragged", player)

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
        if new_w < settings.MIN_WIDTH:
            new_w = settings.MIN_WIDTH
            if player.resize_sides[0]:  # Adjust position if resizing from left
                new_x = player.drag_start_x + (player.drag_start_w - settings.MIN_WIDTH)
        if new_h < settings.MIN_HEIGHT:
            new_h = settings.MIN_HEIGHT
            if player.resize_sides[1]:  # Adjust position if resizing from top
                new_y = player.drag_start_y + (
                        player.drag_start_h - settings.MIN_HEIGHT
                )

        player.panel.place(x=new_x, y=new_y, width=new_w, height=new_h)
        player.set_area(player.panel)

        self.event_manager.trigger("video_resized", player)

    def get_rel_coords(self, x, y):
        """
        Converts screen coordinates to window-relative coordinates.
        """
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        return x - root_x, y - root_y

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
        self.sync_manager.perform_seek(self.seek_bar.get())

    def on_seek_bar_move(self, value):
        """
        Called when the seek bar is moved.
        """
        if self.user_is_seeking:
            self.seek_bar.set(int(float(value)))  # Ensure the value is an integer

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

    @staticmethod
    def format_time(milliseconds):
        """
        Formats time in milliseconds to a min:sec string.
        """
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"

    def is_inside_any_control_panel(self, x, y):
        """
        Checks if the given coordinates are inside any of the control panels.
        """
        x, y = self.get_rel_coords(x, y)
        return (
                is_inside(x, y, self.get_control_panel_area(self.control_panel))
                or is_inside(x, y, self.get_control_panel_area(self.control_panel1))
                or is_inside(x, y, self.get_control_panel_area(self.control_panel2))
        )

    def get_control_panel_area(self, frame):
        """
        Returns the area of the control panel based on the given frame.
        """
        x, y = self.get_rel_coords(frame.winfo_rootx(), frame.winfo_rooty())
        width = frame.winfo_width()
        height = frame.winfo_height()
        return x, y, width, height

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
