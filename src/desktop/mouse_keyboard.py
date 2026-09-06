import time
from typing import List, Optional
import pyautogui
import pyperclip


class MouseKeyboardController:
    """Controls mouse movements, clicks, drags, keyboard typing, and hotkeys."""

    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05

    def click(self, x: int, y: int, button: str = 'left') -> None:
        """Click at the specified screen coordinates."""
        pyautogui.click(x=x, y=y, button=button)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> None:
        """Drag mouse cursor from start coordinates to end coordinates."""
        pyautogui.moveTo(start_x, start_y)
        pyautogui.mouseDown()
        pyautogui.moveTo(end_x, end_y, duration=duration)
        pyautogui.mouseUp()

    def type_text(self, text: str, use_clipboard: bool = False) -> None:
        """Type text using keyboard simulation or clipboard paste for long text / special characters."""
        time.sleep(0.1)
        old_failsafe = pyautogui.FAILSAFE
        try:
            pyautogui.FAILSAFE = False
            if use_clipboard or len(text) > 40:
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
            else:
                pyautogui.write(text, interval=0.01)
        finally:
            pyautogui.FAILSAFE = old_failsafe

    def hotkey(self, keys: List[str]) -> None:
        """Press a combination of keys simultaneously."""
        pyautogui.hotkey(*keys)
