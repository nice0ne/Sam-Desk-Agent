import pytest
from unittest.mock import MagicMock, patch
from src.desktop.os_actions import OSController

def test_os_controller_instantiation():
    controller = OSController()
    assert controller is not None

def test_volume_clamping():
    controller = OSController()
    assert controller._clamp_volume(-0.5) == 0.0
    assert controller._clamp_volume(1.5) == 1.0
    assert controller._clamp_volume(0.65) == 0.65
    assert controller._clamp_volume(0.6543) == 0.65
    assert controller._clamp_volume(0.0) == 0.0
    assert controller._clamp_volume(1.0) == 1.0

def test_launch_app():
    controller = OSController()
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        result = controller.launch_app("notepad", ["file.txt"])
        mock_popen.assert_called_once_with(["notepad", "file.txt"], shell=True)
        assert result["status"] == "success"
        assert result["pid"] == 12345
        assert "notepad" in result["message"]

def test_launch_app_failure():
    controller = OSController()
    with patch("subprocess.Popen", side_effect=Exception("Execution failed")):
        result = controller.launch_app("invalid_app")
        assert result["status"] == "error"
        assert "Execution failed" in result["message"]

def test_get_open_windows_fallback_when_win32gui_missing():
    controller = OSController()
    with patch.dict("sys.modules", {"win32gui": None}):
        windows = controller.get_open_windows()
        assert isinstance(windows, list)

def test_focus_window():
    controller = OSController()
    with patch.object(controller, "get_open_windows", return_value=[{"hwnd": 101, "title": "Untitled - Notepad"}]):
        with patch.dict("sys.modules", {"win32gui": MagicMock(), "win32con": MagicMock()}):
            import win32gui
            focused = controller.focus_window("notepad")
            assert focused is True
            win32gui.SetForegroundWindow.assert_called_once_with(101)

def test_focus_window_not_found():
    controller = OSController()
    with patch.object(controller, "get_open_windows", return_value=[{"hwnd": 101, "title": "Calculator"}]):
        focused = controller.focus_window("notepad")
        assert focused is False

def test_close_app_window_graceful():
    controller = OSController()
    with patch.object(controller, "get_open_windows", return_value=[{"hwnd": 202, "title": "Untitled - Notepad"}]):
        with patch.dict("sys.modules", {"win32gui": MagicMock(), "win32con": MagicMock()}):
            import win32gui, win32con
            closed = controller.close_app("notepad", force=False)
            assert closed is True
            win32gui.PostMessage.assert_called_once_with(202, win32con.WM_CLOSE, 0, 0)

def test_close_app_by_process_terminate():
    controller = OSController()
    with patch.object(controller, "get_open_windows", return_value=[]):
        mock_proc = MagicMock()
        mock_proc.info = {"name": "notepad.exe", "pid": 5432}
        with patch("psutil.process_iter", return_value=[mock_proc]):
            closed = controller.close_app("notepad", force=False)
            assert closed is True
            mock_proc.terminate.assert_called_once()

def test_close_app_by_process_force():
    controller = OSController()
    with patch.object(controller, "get_open_windows", return_value=[]):
        mock_proc = MagicMock()
        mock_proc.info = {"name": "notepad.exe", "pid": 5432}
        with patch("psutil.process_iter", return_value=[mock_proc]):
            closed = controller.close_app("notepad", force=True)
            assert closed is True
            mock_proc.kill.assert_called_once()

def test_adjust_volume_fallback():
    controller = OSController()
    # Without pycaw installed, adjust_volume should use fallback calculation
    vol = controller.adjust_volume(target_level=0.7)
    assert vol == 0.7

    vol_delta = controller.adjust_volume(delta=0.1)
    assert vol_delta == 0.6


def test_focus_window_alias_and_process_match():
    controller = OSController()
    mock_windows = [
        {"hwnd": 501, "title": "Windows (C:) - File Explorer", "proc_name": "explorer.exe", "class_name": "CabinetWClass"},
        {"hwnd": 502, "title": "", "proc_name": "notepad.exe", "class_name": "Notepad"},
    ]
    with patch.object(controller, "get_open_windows", return_value=mock_windows):
        with patch.object(controller, "force_foreground_window", return_value=True) as mock_force:
            # Match explorer by alias/class/proc
            assert controller.focus_window("explorer") is True
            mock_force.assert_called_with(501)

            # Match notepad by proc name
            assert controller.focus_window("notepad") is True
            mock_force.assert_called_with(502)


def test_launch_app_with_auto_focus():
    controller = OSController()
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc

        with patch.object(controller, "focus_window", return_value=True) as mock_focus:
            res = controller.launch_app("notepad", auto_focus=True)
            assert res["status"] == "success"
            assert res["pid"] == 9999
            assert res["focused"] is True
            mock_focus.assert_called_once_with("notepad")

