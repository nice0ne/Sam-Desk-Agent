"""System tray application module for Sam-Desk-Agent.

Provides a Windows taskbar tray icon with dynamic status indicators (Active/Paused),
context menu, and pause/resume and exit callbacks.
"""

from typing import Callable, Optional, Dict, Any
import logging
from PIL import Image, ImageDraw

try:
    import pystray
    from pystray import Menu, MenuItem
except ImportError:
    pystray = None
    Menu = None
    MenuItem = None

logger = logging.getLogger(__name__)


def create_icon_image(color: str = "green", width: int = 64, height: int = 64) -> Image.Image:
    """Generate a small PIL circle icon with the specified color.
    
    Args:
        color: Color name or hex string (e.g. 'green', 'yellow', '#2ecc71').
        width: Image width in pixels.
        height: Image height in pixels.
        
    Returns:
        PIL Image with circle graphic and transparent background.
    """
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = max(2, width // 16)
    draw.ellipse((margin, margin, width - margin, height - margin), fill=color)
    return image


class SystemTrayApp:
    """Windows System Tray integration for Sam-Desk-Agent using pystray."""

    create_icon_image = staticmethod(create_icon_image)

    def __init__(
        self,
        on_toggle_pause: Optional[Callable] = None,
        on_exit: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
        on_view_memory: Optional[Callable] = None,
    ):
        self.on_toggle_pause = on_toggle_pause
        self.on_exit = on_exit
        self.on_settings = on_settings
        self.on_view_memory = on_view_memory
        self.is_paused: bool = False
        self._running: bool = False
        self._icon_image = create_icon_image("green")

        self.icon: Optional[Any] = None
        if pystray is not None:
            try:
                self.icon = pystray.Icon(
                    name="SamDeskAgent",
                    icon=self._icon_image,
                    title="Sam Desk Agent (Active)",
                    menu=self._create_pystray_menu(),
                )
            except Exception as e:
                logger.warning("Could not initialize pystray icon: %s", e)
                self.icon = None

    @property
    def status(self) -> str:
        """Current agent status string ('active' or 'paused')."""
        return "paused" if self.is_paused else "active"

    def _get_toggle_label(self, item=None) -> str:
        return "Lanjutkan Agent" if self.is_paused else "Jeda Agent"

    def _create_pystray_menu(self):
        if pystray is None:
            return None
        return Menu(
            MenuItem(self._get_toggle_label, self._on_tray_toggle_click),
            MenuItem("Pengaturan", self._on_tray_settings_click),
            MenuItem("Lihat Memori", self._on_tray_memory_click),
            MenuItem("Keluar", self._on_tray_exit_click),
        )

    def _on_tray_toggle_click(self, icon=None, item=None) -> None:
        self.toggle_pause()

    def _on_tray_settings_click(self, icon=None, item=None) -> None:
        if callable(self.on_settings):
            try:
                self.on_settings()
            except Exception as e:
                logger.error("Error invoking on_settings: %s", e)

    def _on_tray_memory_click(self, icon=None, item=None) -> None:
        if callable(self.on_view_memory):
            try:
                self.on_view_memory()
            except Exception as e:
                logger.error("Error invoking on_view_memory: %s", e)

    def _on_tray_exit_click(self, icon=None, item=None) -> None:
        self.stop()

    def toggle_pause(self, paused: Optional[bool] = None) -> bool:
        """Toggle or set agent paused state.
        
        Args:
            paused: If provided, explicitly set paused status. Otherwise toggles.
            
        Returns:
            Current paused boolean state.
        """
        if paused is None:
            self.is_paused = not self.is_paused
        else:
            self.is_paused = bool(paused)

        color = "yellow" if self.is_paused else "green"
        self._icon_image = create_icon_image(color)
        status_label = "Paused" if self.is_paused else "Active"

        if self.icon is not None:
            try:
                self.icon.icon = self._icon_image
                self.icon.title = f"Sam Desk Agent ({status_label})"
                if hasattr(self.icon, "update_menu"):
                    self.icon.update_menu()
            except Exception:
                pass

        if callable(self.on_toggle_pause):
            try:
                self.on_toggle_pause(self.is_paused)
            except TypeError:
                self.on_toggle_pause()

        return self.is_paused

    def build_menu(self) -> Dict[str, Any]:
        """Build dictionary representation of system tray menu structure.
        
        Returns:
            Dictionary with 'status' and 'menu_items' list.
        """
        toggle_label = "Lanjutkan Agent" if self.is_paused else "Jeda Agent"
        items = [toggle_label, "Pengaturan", "Lihat Memori", "Keluar"]
        return {
            "status": self.status,
            "menu_items": items,
            "items": items,
        }

    def start(self, detached: bool = True) -> None:
        """Start the system tray icon."""
        self._running = True
        if self.icon is not None:
            try:
                if detached:
                    self.icon.run_detached()
                else:
                    self.icon.run()
            except Exception as e:
                logger.warning("Failed starting tray icon: %s", e)

    def run(self) -> None:
        """Run system tray icon in blocking mode."""
        self.start(detached=False)

    def stop(self) -> None:
        """Stop system tray icon and trigger on_exit callback."""
        self._running = False
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
        if callable(self.on_exit):
            try:
                self.on_exit()
            except Exception:
                pass
