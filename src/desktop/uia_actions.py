from typing import Optional, Dict, Any


class UIAController:
    """Windows UI Automation controller using pywinauto."""

    def click_element_by_name(self, name: str) -> bool:
        """Find an element matching name/title via UIA and click it.

        Returns True on success, False if element not found or pywinauto is unavailable.
        """
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            element = desktop.window(title_re=f".*{name}.*")
            if element.exists(timeout=0.5):
                element.click_input()
                return True
        except Exception:
            pass
        return False
