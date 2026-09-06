import os
import sys
import time
import asyncio
import threading
import queue
from pathlib import Path
import yaml

from src.core.event_bus import EventBus
from src.core.safety import SafetySupervisor
from src.desktop.controller import DesktopActionController
from src.brain.agent import AgentBrain
from src.brain.llm_client import LLMClient
from src.memory.db import DatabaseManager
from src.memory.skill_store import SkillStore
from src.voice.hotkey import GlobalHotkeyListener, normalize_hotkey_string
from src.voice.recorder import AudioRecorder
from src.voice.stt_engine import STTEngine
from src.voice.tts_engine import TTSEngine
from src.ui.hud import FloatingHUD, HUDState
from src.ui.tray import SystemTrayApp
from src.ui import setup_tcl_tk_env


def load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {
        "voice": {
            "hotkey": "<alt>+<space>",
            "stt_model": "base",
            "tts_voice": "id-ID-ArdiNeural"
        },
        "brain": {
            "provider": "glm",
            "model": "glm-4-flash",
            "max_sub_actions": 10
        }
    }


class SamDeskAgentApp:
    def __init__(self):
        setup_tcl_tk_env()
        self.config = load_config()
        self.running = False
        self._main_thread = threading.current_thread()
        self._ui_queue: queue.Queue = queue.Queue()
        self._settings_win = None
        self._memory_win = None

        # Main Tkinter root (hidden on main thread)
        try:
            import tkinter as tk
            self.root = tk.Tk()
            self.root.withdraw()
        except Exception:
            self.root = None

        # Core components
        self.event_bus = EventBus()
        self.safety = SafetySupervisor(self.event_bus)
        self.desktop = DesktopActionController(self.safety)
        self.db = DatabaseManager()
        self.db.init_db()
        self.skill_store = SkillStore(self.db)

        # Multi-AI Provider Brain
        brain_cfg = self.config.get("brain", {})
        self.llm_client = LLMClient(
            provider=brain_cfg.get("provider", "glm"),
            model=brain_cfg.get("model"),
            base_url=brain_cfg.get("base_url"),
            api_key=brain_cfg.get("api_key"),
            max_sub_actions=brain_cfg.get("max_sub_actions", 10),
        )
        self.brain = AgentBrain(self.desktop, self.skill_store, llm_client=self.llm_client)

        # Voice components
        self.recorder = AudioRecorder()
        v_cfg = self.config.get("voice", {})
        self.stt = STTEngine(
            provider=v_cfg.get("stt_provider", "google"),
            model_size=v_cfg.get("stt_model", "base"),
            device=v_cfg.get("stt_device", "cpu"),
            compute_type=v_cfg.get("stt_compute_type", "int8"),
            language=v_cfg.get("stt_language", self.config.get("app", {}).get("language", "id-ID")),
            google_api_key=v_cfg.get("stt_google_api_key"),
        )
        self.tts = TTSEngine(default_voice=v_cfg.get("tts_voice", "id-ID-ArdiNeural"))

        # UI components
        self.hud = FloatingHUD(on_stop_clicked=self.on_stop_clicked, master=self.root)
        self.tray = SystemTrayApp(
            on_toggle_pause=self.on_toggle_pause,
            on_exit=self.stop,
            on_settings=self.open_settings_window,
            on_view_memory=self.open_memory_window,
        )

        # Hotkey listener
        hotkey_str = self.config.get("voice", {}).get("hotkey", "<alt>+<space>")
        self.hotkey_listener = GlobalHotkeyListener(
            on_trigger=self.on_hotkey_pressed,
            safety_supervisor=self.safety,
            hotkey_str=hotkey_str
        )

    def post_to_ui(self, fn, *args, **kwargs):
        """Safely execute or schedule a callable onto the main GUI thread."""
        if self.root is None:
            fn(*args, **kwargs)
            return
        if threading.current_thread() == self._main_thread:
            try:
                fn(*args, **kwargs)
            except Exception as e:
                print(f"[UI] Direct execution error: {e}")
        else:
            self._ui_queue.put((fn, args, kwargs))

    def _poll_ui_queue(self):
        """Process queued UI tasks from background threads on the main loop."""
        while not self._ui_queue.empty():
            try:
                fn, args, kwargs = self._ui_queue.get_nowait()
                fn(*args, **kwargs)
            except Exception as e:
                print(f"[UI] Error executing task on main thread: {e}")
        if self.root and self.running:
            try:
                self.root.after(50, self._poll_ui_queue)
            except Exception:
                pass

    def on_stop_clicked(self):
        print("[Sam] Tombol Stop diklik! Menghentikan aksi aktif...")
        self.safety.trigger_panic("Emergency Stop clicked on HUD")
        self.hud.update_state(HUDState.PANIC, "Eksekusi Dihentikan!")

    def on_toggle_pause(self, is_paused: bool):
        if is_paused:
            print("[Sam] Agent dijeda.")
            self.hud.update_state(HUDState.IDLE, "Sam Dijeda")
        else:
            print("[Sam] Agent aktif kembali.")
            self.hud.update_state(HUDState.IDLE, "Sam Siap")

    def open_settings_window(self):
        self.post_to_ui(self._do_open_settings)

    def _do_open_settings(self):
        print("[Sam] Membuka jendela Pengaturan...")
        try:
            from src.ui.settings_window import SettingsWindow
            if self._settings_win is None or self._settings_win.root is None or not self._settings_win.root.winfo_exists():
                self._settings_win = SettingsWindow(on_save_callback=self._on_settings_saved, master=self.root)
                self._settings_win.show()
            else:
                self._settings_win.root.lift()
                self._settings_win.root.focus_force()
        except Exception as e:
            print(f"[Error] Gagal membuka Pengaturan: {e}")

    def _on_settings_saved(self, new_config: dict):
        print("[Sam] Pengaturan baru berhasil disimpan dan diterapkan.")
        self.config = new_config
        if "voice" in new_config:
            voice_cfg = new_config["voice"]
            if "tts_voice" in voice_cfg:
                self.tts.default_voice = voice_cfg["tts_voice"]
            if "stt_provider" in voice_cfg:
                self.stt.provider = voice_cfg["stt_provider"]
            if "stt_language" in voice_cfg:
                self.stt.language = voice_cfg["stt_language"]
            if "stt_model" in voice_cfg:
                self.stt.model_size = voice_cfg["stt_model"]
            if "hotkey" in voice_cfg:
                new_hotkey = normalize_hotkey_string(voice_cfg["hotkey"])
                if new_hotkey != self.hotkey_listener.hotkey_str:
                    self.hotkey_listener.stop()
                    self.hotkey_listener.hotkey_str = new_hotkey
                    self.hotkey_listener.start()
        if "brain" in new_config:
            b_cfg = new_config["brain"]
            self.llm_client = LLMClient(
                provider=b_cfg.get("provider", "glm"),
                model=b_cfg.get("model"),
                base_url=b_cfg.get("base_url"),
                api_key=b_cfg.get("api_key"),
                max_sub_actions=b_cfg.get("max_sub_actions", 10),
            )
            self.brain.llm_client = self.llm_client

    def open_memory_window(self):
        self.post_to_ui(self._do_open_memory)

    def _do_open_memory(self):
        print("[Sam] Membuka jendela Memori & Pembelajaran...")
        try:
            from src.ui.memory_window import MemoryViewerWindow
            if self._memory_win is None or self._memory_win.root is None or not self._memory_win.root.winfo_exists():
                self._memory_win = MemoryViewerWindow(db_manager=self.db, skill_store=self.skill_store, master=self.root)
                self._memory_win.show()
            else:
                self._memory_win.root.lift()
                self._memory_win.root.focus_force()
        except Exception as e:
            print(f"[Error] Gagal membuka Memori: {e}")

    def on_hotkey_pressed(self):
        if self.safety.is_cancelled():
            self.safety.reset()

        threading.Thread(target=self._process_voice_interaction, daemon=True).start()

    def _process_voice_interaction(self):
        try:
            print("\n[Voice] Hotkey aktif! Mendengarkan...")
            self.hud.show()
            self.hud.update_state(HUDState.LISTENING, "Mendengarkan suara...")

            # 1. Capture audio
            audio_data = self.recorder.record_chunk(duration_sec=3.5)

            # 2. Transcribe
            self.hud.update_state(HUDState.THINKING, "Memproses ucapan...")
            user_text = self.stt.transcribe(audio_data)
            print(f"[Voice] Hasil Transkripsi: '{user_text}'")

            if not user_text:
                self.hud.update_state(HUDState.IDLE, "Tidak ada suara terdeteksi.")
                time.sleep(1.5)
                self.hud.hide()
                return

            self.hud.update_state(HUDState.THINKING, f"'{user_text}'")
            print(f"[Sam] Menganalisis perintah: '{user_text}'...")

            # 3. Process command via AgentBrain
            self.hud.update_state(HUDState.EXECUTING, "Mengeksekusi perintah...")
            res = self.brain.process_command(user_text)

            actions = res.get("actions", [])
            if actions:
                print(f"[Sam] Menjalankan {len(actions)} aksi: {actions}")
            else:
                print("[Sam] Tidak ada aksi sistem tambahan.")

            # 4. Voice response
            voice_text = res.get("response") if isinstance(res, dict) and res.get("response") else "Perintah Anda telah selesai dijalankan."
            print(f"[Sam] Respon: '{voice_text}'")

            hud_text = voice_text[:40] + ("..." if len(voice_text) > 40 else "")
            self.hud.update_state(HUDState.SPEAKING, hud_text)
            try:
                asyncio.run(self.tts.speak(voice_text))
            except Exception as tts_err:
                print(f"[TTS Error] {tts_err}")

            self.hud.update_state(HUDState.IDLE, "Selesai.")
            time.sleep(1.0)
            self.hud.hide()

        except Exception as e:
            print(f"[Error] {e}")
            self.hud.update_state(HUDState.PANIC, f"Error: {e}")
            time.sleep(2)
            self.hud.hide()

    def start(self):
        self.running = True
        hotkey_display = self.config.get("voice", {}).get("hotkey", "<alt>+<space>")
        print("==================================================")
        print("  SAM-DESK-AGENT AKTIF DI SISTEM TRAY WINDOWS     ")
        print("==================================================")
        print(f"[*] Tekan '{hotkey_display}' untuk berbicara.")
        print("[*] Tekan 'Esc' 3 kali cepat untuk Panic Stop.")
        print("[*] Buka System Tray untuk menu atau keluar.")
        print("==================================================")

        self.hotkey_listener.start()
        self.tray.start(detached=True)

        if self.root:
            self.root.after(50, self._poll_ui_queue)
            try:
                self.root.mainloop()
            except KeyboardInterrupt:
                self.stop()
        else:
            try:
                while self.running:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        self.post_to_ui(self._do_stop)

    def _do_stop(self):
        if not self.running:
            return
        print("\n[*] Menutup Sam-Desk-Agent...")
        self.running = False
        self.hotkey_listener.stop()
        self.tray.stop()
        if self.hud:
            self.hud.hide()
            self.hud.destroy()
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass
            self.root = None
        sys.exit(0)


def main():
    app = SamDeskAgentApp()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()

