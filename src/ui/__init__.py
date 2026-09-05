"""UI module for Sam-Desk-Agent: System Tray and Floating HUD."""

from src.ui.hud import HUDState, FloatingHUD, FloatingHUDWindow
from src.ui.tray import SystemTrayApp, create_icon_image

__all__ = [
    "HUDState",
    "FloatingHUD",
    "FloatingHUDWindow",
    "SystemTrayApp",
    "create_icon_image",
]
