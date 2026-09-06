import os
import time
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

    APP_WINDOW_PATTERNS: Dict[str, Dict[str, List[str]]] = {
        "notepad": {
            "proc_names": ["notepad.exe"],
            "title_keywords": ["notepad", "catatan", "untitled", "tanpa judul"],
            "class_names": ["notepad", "richeditd2dpt"],
        },
        "explorer": {
            "proc_names": ["explorer.exe"],
            "title_keywords": ["file explorer", "penjelajah berkas", "this pc", "home", "quick access", "dokumen", "unduhan", "desktop"],
            "class_names": ["cabinetwclass", "explorewclass"],
        },
        "calc": {
            "proc_names": ["calculatorapp.exe", "calculator.exe", "calc.exe"],
            "title_keywords": ["calculator", "kalkulator"],
            "class_names": ["applicationframewindow"],
        },
        "chrome": {
            "proc_names": ["chrome.exe"],
            "title_keywords": ["chrome", "google chrome"],
            "class_names": ["chrome_widgetwin_1"],
        },
        "edge": {
            "proc_names": ["msedge.exe"],
            "title_keywords": ["edge", "microsoft edge"],
            "class_names": ["chrome_widgetwin_1"],
        },
        "cmd": {
            "proc_names": ["cmd.exe"],
            "title_keywords": ["command prompt", "cmd.exe", "administrator:"],
            "class_names": ["consolewindowclass"],
        },
        "powershell": {
            "proc_names": ["powershell.exe", "pwsh.exe"],
            "title_keywords": ["powershell", "windows powershell"],
            "class_names": ["consolewindowclass"],
        },
        "code": {
            "proc_names": ["code.exe"],
            "title_keywords": ["visual studio code", " - code"],
            "class_names": [],
        },
    }

    def _ensure_desktop_access(self) -> None:
        """Ensure current thread is attached to the interactive desktop (WinSta0\\Default)."""
        try:
            import ctypes
            u32 = ctypes.windll.user32
            hwinsta = u32.OpenWindowStationW("WinSta0", False, 0x2000000)
            if hwinsta:
                u32.SetProcessWindowStation(hwinsta)
            hdesk = u32.OpenDesktopW("Default", 0, False, 0x2000000)
            if hdesk:
                u32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    def force_foreground_window(self, hwnd: int) -> bool:
        """Forces a window into the foreground, restoring from minimized and bypassing Windows foreground lock."""
        try:
            import win32gui
            import win32con

            if not hwnd:
                return False

            self._ensure_desktop_access()

            # 1. Unminimize / restore window if minimized or iconic
            try:
                if hasattr(win32gui, "IsIconic") and win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            except Exception:
                pass

            # 2. Simulate Alt key down/up (bypasses Windows SPI_SETFOREGROUNDLOCKTIMEOUT)
            try:
                import ctypes
                VK_MENU = 0x12
                KEYEVENTF_KEYUP = 0x0002
                ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
            except Exception:
                pass

            # 3. AttachThreadInput trick to grant focus rights across threads
            attached = False
            try:
                import ctypes
                import win32process
                fore_hwnd = win32gui.GetForegroundWindow()
                fore_tid, _ = win32process.GetWindowThreadProcessId(fore_hwnd)
                cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()
                if fore_tid != 0 and fore_tid != cur_tid:
                    ctypes.windll.user32.AttachThreadInput(cur_tid, fore_tid, True)
                    attached = True
            except Exception:
                pass

            try:
                if hasattr(win32gui, "BringWindowToTop"):
                    win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
            finally:
                if attached:
                    try:
                        ctypes.windll.user32.AttachThreadInput(cur_tid, fore_tid, False)
                    except Exception:
                        pass

            time.sleep(0.08)
            return True
        except Exception:
            return False

    def launch_app(self, name: str, args: Optional[List[str]] = None, auto_focus: bool = True) -> Dict[str, Any]:
        """Launches an application via subprocess.Popen and brings its window to the foreground."""
        cmd: List[str] = [name]
        if args:
            cmd.extend(args)
        try:
            proc = subprocess.Popen(cmd, shell=True)

            focused = False
            if auto_focus:
                from pathlib import Path
                app_target = Path(name).stem.lower()
                for _ in range(8):
                    time.sleep(0.1)
                    if self.focus_window(app_target):
                        focused = True
                        break

            return {
                "status": "success",
                "pid": proc.pid,
                "focused": focused,
                "message": f"App '{name}' launched."
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_open_windows(self) -> List[Dict[str, Any]]:
        """Enumerates visible top-level windows with rich metadata (hwnd, title, pid, proc_name, class_name)."""
        windows: List[Dict[str, Any]] = []
        try:
            import win32gui
            if win32gui is None:
                return windows

            self._ensure_desktop_access()

            import win32process

            def enum_handler(hwnd: int, extra: List[Dict[str, Any]]) -> None:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip()
                    cls_name = win32gui.GetClassName(hwnd).strip() if hasattr(win32gui, "GetClassName") else ""
                    if cls_name.lower() in ["progman", "shell_traywnd", "dummy"]:
                        return

                    pid = None
                    proc_name = ""
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        proc = psutil.Process(pid)
                        proc_name = proc.name()
                    except Exception:
                        pass

                    if title or cls_name.lower() in ["cabinetwclass", "explorewclass", "notepad"]:
                        extra.append({
                            "hwnd": hwnd,
                            "title": title,
                            "pid": pid,
                            "proc_name": proc_name,
                            "class_name": cls_name,
                        })

            win32gui.EnumWindows(enum_handler, windows)
        except (ImportError, Exception):
            pass
        return windows

    def focus_window(self, title_pattern: str) -> bool:
        """Searches open windows by title, process name, or app alias and brings the matching window to foreground."""
        pattern = title_pattern.lower().strip()
        if pattern.endswith(".exe"):
            pattern = pattern[:-4]

        pattern_info = self.APP_WINDOW_PATTERNS.get(pattern, {})
        target_procs = pattern_info.get("proc_names", [])
        target_keys = pattern_info.get("title_keywords", [])
        target_classes = pattern_info.get("class_names", [])

        windows = self.get_open_windows()
        for win in windows:
            title = win["title"].lower()
            proc = win.get("proc_name", "").lower()
            cls = win.get("class_name", "").lower()

            is_match = False
            if pattern in title:
                is_match = True
            elif any(k in title for k in target_keys if k):
                is_match = True
            elif cls and cls in target_classes:
                is_match = True
            elif proc and (proc in target_procs or pattern in proc):
                is_match = True

            if is_match:
                if self.force_foreground_window(win["hwnd"]):
                    return True
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
