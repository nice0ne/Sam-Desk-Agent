"""UI module for Sam-Desk-Agent: System Tray and Floating HUD."""

import os
import sys

def setup_tcl_tk_env() -> None:
    """Ensure TCL_LIBRARY and TK_LIBRARY are set properly on Windows environments with forward slashes."""
    if sys.platform == "win32":
        base = getattr(sys, "base_prefix", sys.prefix)
        tcl_dir = os.path.join(base, "tcl", "tcl8.6").replace("\\", "/")
        tk_dir = os.path.join(base, "tcl", "tk8.6").replace("\\", "/")
        if os.path.exists(tcl_dir):
            os.environ["TCL_LIBRARY"] = tcl_dir
        if os.path.exists(tk_dir):
            os.environ["TK_LIBRARY"] = tk_dir

setup_tcl_tk_env()

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
    "setup_tcl_tk_env",
]

