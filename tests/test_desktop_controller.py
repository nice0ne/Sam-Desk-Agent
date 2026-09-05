import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from src.core.safety import SafetySupervisor
from src.desktop.controller import DesktopActionController
from src.desktop.mouse_keyboard import MouseKeyboardController
from src.desktop.uia_actions import UIAController
from src.desktop.vision_actions import VisionController


def test_mouse_keyboard_controller_init():
    with patch("pyautogui.FAILSAFE", False), patch("pyautogui.PAUSE", 0.1):
        ctrl = MouseKeyboardController()
        import pyautogui
        assert pyautogui.FAILSAFE is True
        assert pyautogui.PAUSE == 0.05


def test_mouse_keyboard_actions():
    ctrl = MouseKeyboardController()
    with patch("pyautogui.click") as mock_click:
        ctrl.click(100, 200, "left")
        mock_click.assert_called_once_with(x=100, y=200, button="left")

    with patch("pyautogui.moveTo") as mock_move, \
         patch("pyautogui.mouseDown") as mock_down, \
         patch("pyautogui.mouseUp") as mock_up:
        ctrl.drag(10, 20, 30, 40, duration=0.5)
        mock_move.assert_any_call(10, 20)
        mock_down.assert_called_once()
        mock_move.assert_any_call(30, 40, duration=0.5)
        mock_up.assert_called_once()

    with patch("pyautogui.write") as mock_write, patch("pyperclip.copy") as mock_copy, patch("pyautogui.hotkey") as mock_hotkey:
        ctrl.type_text("short text", use_clipboard=False)
        mock_write.assert_called_once_with("short text", interval=0.01)
        mock_copy.assert_not_called()

        mock_write.reset_mock()
        mock_copy.reset_mock()
        # long text (> 40 chars)
        long_str = "a" * 50
        ctrl.type_text(long_str, use_clipboard=False)
        mock_copy.assert_called_once_with(long_str)
        mock_hotkey.assert_called_with("ctrl", "v")
        mock_write.assert_not_called()

        mock_copy.reset_mock()
        mock_hotkey.reset_mock()
        # forced clipboard
        ctrl.type_text("clipboard force", use_clipboard=True)
        mock_copy.assert_called_once_with("clipboard force")
        mock_hotkey.assert_called_with("ctrl", "v")

    with patch("pyautogui.hotkey") as mock_hotkey:
        ctrl.hotkey(["ctrl", "shift", "esc"])
        mock_hotkey.assert_called_once_with("ctrl", "shift", "esc")


def test_uia_controller():
    ctrl = UIAController()
    # Test clean fallback when pywinauto is not installed or raises an exception
    res = ctrl.click_element_by_name("NonExistent")
    assert res is False

    # Test when pywinauto is available and succeeds
    mock_pywinauto = MagicMock()
    mock_element = MagicMock()
    mock_element.exists.return_value = True
    mock_desktop = MagicMock()
    mock_desktop.window.return_value = mock_element
    mock_pywinauto.Desktop.return_value = mock_desktop

    with patch.dict("sys.modules", {"pywinauto": mock_pywinauto}):
        res = ctrl.click_element_by_name("Notepad")
        assert res is True
        mock_element.click_input.assert_called_once()

    # Test when pywinauto element does not exist
    mock_element.exists.return_value = False
    with patch.dict("sys.modules", {"pywinauto": mock_pywinauto}):
        res = ctrl.click_element_by_name("Notepad")
        assert res is False



def test_vision_controller():
    ctrl = VisionController()
    norm_x, norm_y = ctrl.normalize_coordinate(500.0, 500.0, 1920, 1080)
    assert norm_x == 960
    assert norm_y == 540

    with patch("mss.mss") as mock_mss:
        mock_sct = MagicMock()
        mock_mss.return_value.__enter__.return_value = mock_sct
        mock_sct.monitors = [None, {"top": 0, "left": 0, "width": 100, "height": 100}]
        mock_grab = MagicMock()
        mock_grab.size = (100, 100)
        mock_grab.bgra = b"\x00" * (100 * 100 * 4)
        mock_sct.grab.return_value = mock_grab

        img = ctrl.capture_screen()
        assert isinstance(img, Image.Image)


def test_controller_delegation_to_os():
    safety = SafetySupervisor()
    controller = DesktopActionController(safety_supervisor=safety)

    with patch.object(controller.os_ctrl, "adjust_volume", return_value=0.5) as mock_vol:
        res = controller.execute_action("adjust_system_volume", {"level": 0.5})
        assert res["status"] == "success"
        assert res["level"] == 0.5
        mock_vol.assert_called_once_with(0.0, 0.5)

    with patch.object(controller.os_ctrl, "launch_app", return_value={"status": "success", "pid": 1234, "message": "App 'notepad' launched."}) as mock_launch:
        res = controller.execute_action("launch_application", {"app_name": "notepad", "args": ["file.txt"]})
        assert res["status"] == "success"
        assert res["pid"] == 1234
        mock_launch.assert_called_once_with("notepad", ["file.txt"])

    with patch.object(controller.os_ctrl, "close_app", return_value=True) as mock_close:
        res = controller.execute_action("close_application", {"target": "notepad", "force": True})
        assert res["status"] == "success"
        assert res["closed"] is True
        mock_close.assert_called_once_with("notepad", True)

    with patch.object(controller.os_ctrl, "focus_window", return_value=True) as mock_focus:
        res = controller.execute_action("focus_window", {"title_pattern": "notepad"})
        assert res["status"] == "success"
        assert res["focused"] is True
        mock_focus.assert_called_once_with("notepad")


def test_controller_safety_interruption():
    safety = SafetySupervisor()
    safety.trigger_panic("Emergency")
    controller = DesktopActionController(safety_supervisor=safety)

    res = controller.execute_action("launch_application", {"app_name": "notepad"})
    assert res["status"] == "cancelled"
    assert "aborted" in res["message"].lower()


def test_controller_mock_mouse_keyboard_vision_uia():
    safety = SafetySupervisor()
    controller = DesktopActionController(safety_supervisor=safety)

    # mouse_click
    with patch.object(controller.mk_ctrl, "click") as mock_click:
        res = controller.execute_action("mouse_click", {"x": 150, "y": 250, "button": "right"})
        assert res["status"] == "success"
        assert res["x"] == 150
        assert res["y"] == 250
        mock_click.assert_called_once_with(150, 250, "right")

    # mouse_drag
    with patch.object(controller.mk_ctrl, "drag") as mock_drag:
        res = controller.execute_action("mouse_drag", {"start_x": 10, "start_y": 20, "end_x": 30, "end_y": 40})
        assert res["status"] == "success"
        assert res["action"] == "drag"
        mock_drag.assert_called_once_with(10, 20, 30, 40)

    # type_keyboard
    with patch.object(controller.mk_ctrl, "type_text") as mock_type:
        res = controller.execute_action("type_keyboard", {"text": "hello world", "use_clipboard": True})
        assert res["status"] == "success"
        assert res["typed_length"] == 11
        mock_type.assert_called_once_with("hello world", True)

    # press_hotkey
    with patch.object(controller.mk_ctrl, "hotkey") as mock_hotkey:
        res = controller.execute_action("press_hotkey", {"keys": ["ctrl", "c"]})
        assert res["status"] == "success"
        assert res["hotkey"] == ["ctrl", "c"]
        mock_hotkey.assert_called_once_with(["ctrl", "c"])

    # click_ui_element
    with patch.object(controller.uia_ctrl, "click_element_by_name", return_value=True) as mock_uia:
        res = controller.execute_action("click_ui_element", {"name": "File"})
        assert res["status"] == "success"
        assert res["clicked"] is True
        mock_uia.assert_called_once_with("File")

    # unknown tool
    res = controller.execute_action("unknown_tool", {})
    assert res["status"] == "error"
    assert "unknown tool" in res["message"].lower()

    # error handling
    with patch.object(controller.mk_ctrl, "click", side_effect=ValueError("Invalid coord")):
        res = controller.execute_action("mouse_click", {"x": "bad", "y": 20})
        assert res["status"] == "error"
        assert "bad" in res["message"] or "Invalid coord" in res["message"]
