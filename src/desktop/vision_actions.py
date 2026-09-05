from typing import Tuple
import mss
from PIL import Image


class VisionController:
    """Screen capture and coordinate mapping utility."""

    def capture_screen(self) -> Image.Image:
        """Capture the primary monitor screen and return as a PIL Image."""
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # primary monitor
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img

    def normalize_coordinate(
        self, norm_x: float, norm_y: float, screen_width: int, screen_height: int
    ) -> Tuple[int, int]:
        """Convert normalized (0-1000) coordinates to actual screen pixel coordinates."""
        actual_x = int((norm_x / 1000.0) * screen_width)
        actual_y = int((norm_y / 1000.0) * screen_height)
        return (actual_x, actual_y)
