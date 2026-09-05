import os
import subprocess
import psutil
from typing import List, Dict, Optional, Any

class OSController:
    """Controller for OS-level actions, window management, process management, and volume controls."""

    def __init__(self) -> None:
        self._init_dpi_awareness()

    def _init_dpi_awareness(self) -> None:
        """Sets DPI awareness V2 via ctypes.windll.shcore.SetProcessDpiAwareness(2)."""
        try:
            import ctypes
            # Per-Monitor DPI Aware V2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    def _clamp_volume(self, val: float) -> float:
        """Clamps volume between 0.0 and 1.0, rounded to 2 decimal places."""
        return max(0.0, min(1.0, round(float(val), 2)))

    def launch_app(self, name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Launches an application via subprocess.Popen with shell=True."""
        cmd: List[str] = [name]
        if args:
            cmd.extend(args)
        try:
            proc = subprocess.Popen(cmd, shell=True)
            return {"status": "success", "pid": proc.pid, "message": f"App '{name}' launched."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_open_windows(self) -> List[Dict[str, Any]]:
        """Enumerates visible windows with titles via win32gui (with fallback if win32gui not present)."""
        windows: List[Dict[str, Any]] = []
        try:
            import win32gui
            if win32gui is None:
                return windows

            def enum_handler(hwnd: int, extra: List[Dict[str, Any]]) -> None:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        extra.append({"hwnd": hwnd, "title": title})

            win32gui.EnumWindows(enum_handler, windows)
        except (ImportError, Exception):
            pass
        return windows

    def focus_window(self, title_pattern: str) -> bool:
        """Searches window titles and calls SetForegroundWindow."""
        pattern = title_pattern.lower()
        windows = self.get_open_windows()
        for win in windows:
            if pattern in win["title"].lower():
                try:
                    import win32gui
                    import win32con
                    hwnd = win["hwnd"]
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return True
                except Exception:
                    continue
        return False

    def close_app(self, target_title_or_proc: str, force: bool = False) -> bool:
        """Closes window gracefully or terminates process via psutil."""
        target = target_title_or_proc.lower()
        # 1. Try closing window gracefully
        windows = self.get_open_windows()
        for win in windows:
            if target in win["title"].lower():
                try:
                    import win32gui
                    import win32con
                    win32gui.PostMessage(win["hwnd"], win32con.WM_CLOSE, 0, 0)
                    return True
                except Exception:
                    pass

        # 2. Try process matching
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                proc_name = proc.info.get('name') or ''
                if target in proc_name.lower():
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue
        return False

    def adjust_volume(self, delta: float = 0.0, target_level: Optional[float] = None) -> float:
        """Adjusts master volume using pycaw if available, or fallback clamp calculation."""
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            current = volume.GetMasterVolumeLevelScalar()

            if target_level is not None:
                new_vol = self._clamp_volume(target_level)
            else:
                new_vol = self._clamp_volume(current + delta)

            volume.SetMasterVolumeLevelScalar(new_vol, None)
            return new_vol
        except Exception:
            # Fallback mock for testing or systems without sound endpoint
            return self._clamp_volume(target_level if target_level is not None else 0.5 + delta)
