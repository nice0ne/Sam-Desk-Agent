"""Floating HUD module for Sam-Desk-Agent.

Provides an on-top, transparent, frameless status capsule showing the agent's
current state and offering a quick emergency stop control.
"""

from enum import Enum
from typing import Callable, Optional, Tuple, Any
import logging
import threading
import queue

logger = logging.getLogger(__name__)


class HUDState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    SPEAKING = "speaking"
    PANIC = "panic"


class FloatingHUD:
    """Floating HUD pill window with status display and stop button.
    
    Supports transparent, frameless, on-top display using Tkinter or PyQt6
    with a graceful headless fallback when a graphical display is unavailable.
    """

    STATE_ICONS = {
        HUDState.IDLE: "🟢",
        HUDState.LISTENING: "🎙️",
        HUDState.THINKING: "🧠",
        HUDState.EXECUTING: "⚡",
        HUDState.SPEAKING: "🔊",
        HUDState.PANIC: "🛑",
    }

    def __init__(
        self,
        on_stop_clicked: Optional[Callable[[], None]] = None,
        enable_gui: bool = True,
        master: Optional[Any] = None,
    ):
        self.on_stop_clicked = on_stop_clicked
        self.enable_gui = enable_gui
        self.master = master
        self._state: HUDState = HUDState.IDLE
        self._message: str = "Sam Siap"
        self._visible: bool = False

        self._root = None
        self._label = None
        self._btn = None

        self._main_thread = threading.current_thread()
        self._ui_queue: queue.Queue = queue.Queue()

        if self.enable_gui:
            self._init_gui()
            self._schedule_poll()

    def _schedule_poll(self) -> None:
        if self._root:
            try:
                self._poll_id = self._root.after(30, self._poll_queue)
            except Exception:
                pass

    def _poll_queue(self) -> None:
        while not self._ui_queue.empty():
            try:
                fn, args, kwargs = self._ui_queue.get_nowait()
                fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in HUD UI queue: {e}")
        self._schedule_poll()

    def _post_ui(self, fn: Callable, *args, **kwargs) -> None:
        if threading.current_thread() == self._main_thread:
            try:
                fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error executing HUD UI task directly: {e}")
        else:
            self._ui_queue.put((fn, args, kwargs))

    def _init_gui(self) -> None:
        """Initialize GUI framework (Tkinter primary with PyQt6 support)."""
        # Try Tkinter (native Python on Windows)
        try:
            import tkinter as tk

            if self.master:
                root = tk.Toplevel(self.master)
            else:
                root = tk.Tk()
            root.title("Sam HUD")
            # Frameless and Always On Top
            root.overrideredirect(True)
            try:
                root.attributes("-topmost", True)
            except Exception:
                pass
            try:
                root.attributes("-alpha", 0.92)
            except Exception:
                pass

            bg_color = "#1e1e24"
            text_color = "#f8f9fa"
            root.configure(bg=bg_color)

            frame = tk.Frame(root, bg=bg_color, padx=12, pady=6)
            frame.pack(fill="both", expand=True)

            icon = self.STATE_ICONS.get(self._state, "🎙️")
            self._label = tk.Label(
                frame,
                text=f"{icon}  {self._message}",
                fg=text_color,
                bg=bg_color,
                font=("Segoe UI", 10, "bold"),
            )
            self._label.pack(side="left", padx=(0, 10))

            self._btn = tk.Button(
                frame,
                text="✕ Stop",
                command=self.trigger_stop,
                fg="white",
                bg="#e63946",
                activebackground="#c1121f",
                activeforeground="white",
                bd=0,
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=2,
                cursor="hand2",
            )
            self._btn.pack(side="right")

            try:
                screen_w = root.winfo_screenwidth()
                width = 340
                height = 42
                pos_x = max(0, (screen_w - width) // 2)
                pos_y = 20
                root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
            except Exception:
                pass

            root.withdraw()
            self._root = root
        except Exception as e:
            logger.warning("Could not initialize graphical HUD window: %s. Using headless fallback.", e)
            self._root = None

    @property
    def is_visible(self) -> bool:
        return self._visible

    def update_state(self, state: HUDState | str, message: str = "") -> None:
        """Update current HUD state and message."""
        if isinstance(state, str) and not isinstance(state, HUDState):
            try:
                state = HUDState(state.lower())
            except ValueError:
                pass
        self._state = state
        self._message = message

        def _do_update():
            if getattr(self, "_label", None) and getattr(self, "_root", None):
                try:
                    icon = self.STATE_ICONS.get(self._state, "🎙️")
                    self._label.config(text=f"{icon}  {self._message}")
                    self._root.update_idletasks()
                except Exception:
                    pass

        self._post_ui(_do_update)

    def set_status(self, state: HUDState | str, message: str = "") -> None:
        """Alias for update_state for interface compatibility."""
        self.update_state(state, message)

    def show(self) -> None:
        """Display the HUD window."""
        self._visible = True
        def _do_show():
            if getattr(self, "_root", None):
                try:
                    self._root.deiconify()
                    self._root.update_idletasks()
                except Exception:
                    pass
        self._post_ui(_do_show)

    def hide(self) -> None:
        """Hide the HUD window."""
        self._visible = False
        def _do_hide():
            if getattr(self, "_root", None):
                try:
                    self._root.withdraw()
                    self._root.update_idletasks()
                except Exception:
                    pass
        self._post_ui(_do_hide)

    def get_current_state(self) -> Tuple[HUDState, str]:
        """Return the current (HUDState, message) tuple."""
        return (self._state, self._message)

    def trigger_stop(self) -> None:
        """Trigger the stop callback."""
        if callable(self.on_stop_clicked):
            self.on_stop_clicked()

    def destroy(self) -> None:
        """Clean up GUI resources."""
        root = getattr(self, "_root", None)
        if root:
            try:
                poll_id = getattr(self, "_poll_id", None)
                if poll_id:
                    root.after_cancel(poll_id)
            except Exception:
                pass
            try:
                root.destroy()
            except Exception:
                pass
            self._root = None
            self._label = None
            self._btn = None

    def __del__(self):
        self.destroy()


# Compatibility alias
FloatingHUDWindow = FloatingHUD
