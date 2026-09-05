import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from src.ui import HUDState, FloatingHUD, SystemTrayApp
from src.ui.tray import create_icon_image


def test_hud_state_enum_values():
    assert HUDState.IDLE == "idle"
    assert HUDState.LISTENING == "listening"
    assert HUDState.THINKING == "thinking"
    assert HUDState.EXECUTING == "executing"
    assert HUDState.PANIC == "panic"


def test_floating_hud_initial_state():
    hud = FloatingHUD()
    state, message = hud.get_current_state()
    assert state == HUDState.IDLE
    assert message != ""
    assert not hud.is_visible
    hud.destroy()


def test_floating_hud_state_updates():
    hud = FloatingHUD()
    try:
        hud.update_state(HUDState.LISTENING, "Mendengarkan...")
        assert hud.get_current_state() == (HUDState.LISTENING, "Mendengarkan...")

        hud.update_state(HUDState.THINKING, "Sedang berpikir...")
        assert hud.get_current_state() == (HUDState.THINKING, "Sedang berpikir...")

        hud.update_state(HUDState.EXECUTING, "Membuka browser...")
        assert hud.get_current_state() == (HUDState.EXECUTING, "Membuka browser...")

        hud.update_state(HUDState.PANIC, "Emergency stop!")
        assert hud.get_current_state() == (HUDState.PANIC, "Emergency stop!")

        # Test string input support
        hud.update_state("idle", "Sam Siap")
        assert hud.get_current_state() == (HUDState.IDLE, "Sam Siap")

        # Test set_status alias
        hud.set_status(HUDState.LISTENING, "Halo")
        assert hud.get_current_state() == (HUDState.LISTENING, "Halo")
    finally:
        hud.destroy()


def test_floating_hud_visibility():
    hud = FloatingHUD()
    try:
        assert not hud.is_visible
        hud.show()
        assert hud.is_visible
        hud.hide()
        assert not hud.is_visible
    finally:
        hud.destroy()


def test_floating_hud_stop_callback():
    on_stop = MagicMock()
    hud = FloatingHUD(on_stop_clicked=on_stop)
    try:
        hud.trigger_stop()
        on_stop.assert_called_once()
    finally:
        hud.destroy()


def test_floating_hud_headless_fallback():
    hud = FloatingHUD(enable_gui=False)
    assert not hud.is_visible
    hud.show()
    assert hud.is_visible
    hud.update_state(HUDState.THINKING, "Headless mode")
    assert hud.get_current_state() == (HUDState.THINKING, "Headless mode")
    hud.hide()
    assert not hud.is_visible


def test_create_icon_image():
    img = create_icon_image("green")
    assert isinstance(img, Image.Image)
    assert img.size == (64, 64)
    assert img.mode in ("RGBA", "RGB")

    img_yellow = create_icon_image("yellow", width=32, height=32)
    assert img_yellow.size == (32, 32)


def test_system_tray_menu_structure():
    tray = SystemTrayApp()
    menu = tray.build_menu()
    assert isinstance(menu, dict)
    assert "status" in menu
    assert menu["status"] == "active"
    assert "menu_items" in menu
    assert isinstance(menu["menu_items"], list)
    assert any("Jeda" in item for item in menu["menu_items"])
    assert any("Keluar" in item for item in menu["menu_items"])


def test_system_tray_toggle_pause_callback():
    on_toggle = MagicMock()
    tray = SystemTrayApp(on_toggle_pause=on_toggle)

    assert tray.is_paused is False
    assert tray.status == "active"

    # First toggle: pause
    result = tray.toggle_pause()
    assert result is True
    assert tray.is_paused is True
    assert tray.status == "paused"
    on_toggle.assert_called_with(True)

    menu = tray.build_menu()
    assert menu["status"] == "paused"
    assert any("Lanjutkan" in item for item in menu["menu_items"])

    # Second toggle: resume
    result = tray.toggle_pause()
    assert result is False
    assert tray.is_paused is False
    assert tray.status == "active"
    on_toggle.assert_called_with(False)


def test_system_tray_on_exit_callback():
    on_exit = MagicMock()
    tray = SystemTrayApp(on_exit=on_exit)
    tray.stop()
    on_exit.assert_called_once()


def test_system_tray_start_and_stop():
    with patch("pystray.Icon.run_detached") as mock_run_detached, \
         patch("pystray.Icon.stop") as mock_stop:
        tray = SystemTrayApp()
        tray.start(detached=True)
        mock_run_detached.assert_called_once()

        tray.stop()
        mock_stop.assert_called_once()


def test_system_tray_settings_and_memory_callbacks():
    on_settings = MagicMock()
    on_memory = MagicMock()
    tray = SystemTrayApp(on_settings=on_settings, on_view_memory=on_memory)

    tray._on_tray_settings_click()
    on_settings.assert_called_once()

    tray._on_tray_memory_click()
    on_memory.assert_called_once()


def test_settings_window_load_and_save(tmp_path):
    from src.ui.settings_window import SettingsWindow
    cfg_file = tmp_path / "test_config.yaml"
    on_save = MagicMock()

    win = SettingsWindow(on_save_callback=on_save)
    win.config_path = cfg_file

    data = win.load_config()
    assert isinstance(data, dict)

    save_result = win.save_config({"voice": {"hotkey": "<ctrl>+space"}})
    assert save_result is True
    assert cfg_file.exists()
    on_save.assert_called_once_with({"voice": {"hotkey": "<ctrl>+space"}})


def test_memory_viewer_window_data(tmp_path):
    from src.ui.memory_window import MemoryViewerWindow
    from src.memory.db import DatabaseManager
    from src.memory.skill_store import SkillStore

    db_path = str(tmp_path / "test_ui_memory.db")
    db = DatabaseManager(db_path)
    db.init_db()
    store = SkillStore(db)
    store.set_preference("theme", "dark")
    store.save_skill("test skill", "description", [{"tool": "launch_app"}])

    viewer = MemoryViewerWindow(db_manager=db, skill_store=store)
    assert viewer.db_manager is not None
    assert viewer.skill_store is not None
