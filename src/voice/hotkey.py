import logging
from typing import Callable, Optional
from src.core.safety import SafetySupervisor

logger = logging.getLogger(__name__)


def normalize_hotkey_string(hotkey_str: str) -> str:
    """Normalize a hotkey string to ensure special multi-character keys are bracketed for pynput.

    Examples:
        "<alt>+space" -> "<alt>+<space>"
        "alt+space" -> "<alt>+<space>"
        "<ctrl>+<shift>+s" -> "<ctrl>+<shift>+s"
    """
    if not hotkey_str:
        return "<alt>+<space>"
    parts = [p.strip().lower() for p in hotkey_str.split("+") if p.strip()]
    norm_parts = []
    for p in parts:
        if len(p) > 1 and not (p.startswith("<") and p.endswith(">")):
            norm_parts.append(f"<{p}>")
        else:
            norm_parts.append(p)
    return "+".join(norm_parts)


class GlobalHotkeyListener:
    def __init__(
        self,
        on_trigger: Callable[[], None],
        safety_supervisor: Optional[SafetySupervisor] = None,
        hotkey_str: str = "<alt>+<space>"
    ):
        self.on_trigger = on_trigger
        self.safety = safety_supervisor
        self.hotkey_str = normalize_hotkey_string(hotkey_str)
        self._hotkey_listener = None
        self._esc_listener = None
        self.is_running = False

    @property
    def _listener(self):
        return self._hotkey_listener

    @_listener.setter
    def _listener(self, val):
        self._hotkey_listener = val

    def _on_esc_press(self, key) -> None:
        try:
            from pynput import keyboard
            if key == keyboard.Key.esc and self.safety:
                self.safety.record_esc_press()
        except Exception as e:
            logger.error(f"Error handling Esc key press: {e}")

    def start(self) -> None:
        if self.is_running:
            return
        try:
            from pynput import keyboard
            hotkeys = {
                self.hotkey_str: self.on_trigger
            }
            self._hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
            self._hotkey_listener.daemon = True
            self._hotkey_listener.start()

            self._esc_listener = keyboard.Listener(on_press=self._on_esc_press)
            self._esc_listener.daemon = True
            self._esc_listener.start()
            self.is_running = True
        except Exception as e:
            logger.warning(f"Could not start GlobalHotkeyListener: {e}")

    def stop(self) -> None:
        if self._hotkey_listener:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None

        if self._esc_listener:
            try:
                self._esc_listener.stop()
            except Exception:
                pass
            self._esc_listener = None

        self.is_running = False
