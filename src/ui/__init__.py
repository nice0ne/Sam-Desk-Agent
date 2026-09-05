"""UI module for Sam-Desk-Agent: System Tray and Floating HUD."""

from src.ui.hud import HUDState, FloatingHUD, FloatingHUDWindow
from src.ui.tray import SystemTrayApp, create_icon_image
from src.ui.settings_window import SettingsWindow
from src.ui.memory_window import MemoryViewerWindow

__all__ = [
    "HUDState",
    "FloatingHUD",
    "FloatingHUDWindow",
    "SystemTrayApp",
    "create_icon_image",
    "SettingsWindow",
    "MemoryViewerWindow",
]
