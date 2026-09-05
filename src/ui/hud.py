"""Floating HUD module for Sam-Desk-Agent.

Provides an on-top, transparent, frameless status capsule showing the agent's
current state and offering a quick emergency stop control.
"""

from enum import Enum
from typing import Callable, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class HUDState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
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
        HUDState.PANIC: "🛑",
    }

    def __init__(
        self,
        on_stop_clicked: Optional[Callable[[], None]] = None,
        enable_gui: bool = True,
    ):
        self.on_stop_clicked = on_stop_clicked
        self.enable_gui = enable_gui
        self._state: HUDState = HUDState.IDLE
        self._message: str = "Sam Siap"
        self._visible: bool = False

        self._root = None
        self._label = None
        self._btn = None

        if self.enable_gui:
            self._init_gui()

    def _init_gui(self) -> None:
        """Initialize GUI framework (Tkinter primary with PyQt6 support)."""
        # Try Tkinter (native Python on Windows)
        try:
            import tkinter as tk

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

        if self._label and self._root:
            try:
                icon = self.STATE_ICONS.get(self._state, "🎙️")
                self._label.config(text=f"{icon}  {self._message}")
                self._root.update_idletasks()
            except Exception:
                pass

    def set_status(self, state: HUDState | str, message: str = "") -> None:
        """Alias for update_state for interface compatibility."""
        self.update_state(state, message)

    def show(self) -> None:
        """Display the HUD window."""
        self._visible = True
        if self._root:
            try:
                self._root.deiconify()
                self._root.update_idletasks()
            except Exception:
                pass

    def hide(self) -> None:
        """Hide the HUD window."""
        self._visible = False
        if self._root:
            try:
                self._root.withdraw()
                self._root.update_idletasks()
            except Exception:
                pass

    def get_current_state(self) -> Tuple[HUDState, str]:
        """Return the current (HUDState, message) tuple."""
        return (self._state, self._message)

    def trigger_stop(self) -> None:
        """Trigger the stop callback."""
        if callable(self.on_stop_clicked):
            self.on_stop_clicked()

    def destroy(self) -> None:
        """Clean up GUI resources."""
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
            self._label = None
            self._btn = None

    def __del__(self):
        self.destroy()


# Compatibility alias
FloatingHUDWindow = FloatingHUD
