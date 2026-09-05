import os
import sys
import time
import asyncio
import threading
from pathlib import Path
import yaml

from src.core.event_bus import EventBus
from src.core.safety import SafetySupervisor
from src.desktop.controller import DesktopActionController
from src.brain.agent import AgentBrain
from src.memory.db import DatabaseManager
from src.memory.skill_store import SkillStore
from src.voice.hotkey import GlobalHotkeyListener
from src.voice.recorder import AudioRecorder
from src.voice.stt_engine import STTEngine
from src.voice.tts_engine import TTSEngine
from src.ui.hud import FloatingHUD, HUDState
from src.ui.tray import SystemTrayApp


def load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "voice": {
            "hotkey": "<alt>+space",
            "stt_model": "base",
            "tts_voice": "id-ID-ArdiNeural"
        }
    }


class SamDeskAgentApp:
    def __init__(self):
        self.config = load_config()
        self.running = False

        # Core components
        self.event_bus = EventBus()
        self.safety = SafetySupervisor(self.event_bus)
        self.desktop = DesktopActionController(self.safety)
        self.db = DatabaseManager()
        self.db.init_db()
        self.skill_store = SkillStore(self.db)
        self.brain = AgentBrain(self.desktop, self.skill_store)

        # Voice components
        self.recorder = AudioRecorder()
        self.stt = STTEngine(model_size=self.config.get("voice", {}).get("stt_model", "base"))
        self.tts = TTSEngine(default_voice=self.config.get("voice", {}).get("tts_voice", "id-ID-ArdiNeural"))

        # UI components
        self.hud = FloatingHUD(on_stop_clicked=self.on_stop_clicked)
        self.tray = SystemTrayApp(
            on_toggle_pause=self.on_toggle_pause,
            on_exit=self.stop,
            on_settings=self.open_settings_window,
            on_view_memory=self.open_memory_window,
        )

        # Hotkey listener
        hotkey_str = self.config.get("voice", {}).get("hotkey", "<alt>+space")
        self.hotkey_listener = GlobalHotkeyListener(
            on_trigger=self.on_hotkey_pressed,
            safety_supervisor=self.safety,
            hotkey_str=hotkey_str
        )

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
        print("[Sam] Membuka jendela Pengaturan...")
        def _launch():
            try:
                from src.ui.settings_window import SettingsWindow
                win = SettingsWindow(on_save_callback=self._on_settings_saved)
                win.show()
            except Exception as e:
                print(f"[Error] Gagal membuka Pengaturan: {e}")

        threading.Thread(target=_launch, daemon=True).start()

    def _on_settings_saved(self, new_config: dict):
        print("[Sam] Pengaturan baru berhasil disimpan dan diterapkan.")
        self.config = new_config
        if "voice" in new_config and "tts_voice" in new_config["voice"]:
            self.tts.default_voice = new_config["voice"]["tts_voice"]

    def open_memory_window(self):
        print("[Sam] Membuka jendela Memori & Pembelajaran...")
        def _launch():
            try:
                from src.ui.memory_window import MemoryViewerWindow
                win = MemoryViewerWindow(db_manager=self.db, skill_store=self.skill_store)
                win.show()
            except Exception as e:
                print(f"[Error] Gagal membuka Memori: {e}")

        threading.Thread(target=_launch, daemon=True).start()

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

            # 3. Check memory / execute via AgentBrain
            cached_skill = self.brain.find_matching_skill(user_text)
            if cached_skill:
                print(f"[Brain] Menemukan alur di memori: {len(cached_skill)} langkah.")
                self.hud.update_state(HUDState.EXECUTING, "Menjalankan resep memori...")
                results = self.brain.execute_plan(cached_skill)
            else:
                # Direct tool dispatch fallback
                print(f"[Brain] Memproses perintah langsung: {user_text}")
                self.hud.update_state(HUDState.EXECUTING, "Mengeksekusi perintah...")
                results = self.brain.process_command(user_text)

            self.hud.update_state(HUDState.IDLE, "Selesai.")

            # 4. Voice response
            asyncio.run(self.tts.speak("Perintah Anda telah selesai dijalankan."))
            time.sleep(1.5)
            self.hud.hide()

        except Exception as e:
            print(f"[Error] {e}")
            self.hud.update_state(HUDState.PANIC, f"Error: {e}")
            time.sleep(2)
            self.hud.hide()

    def start(self):
        self.running = True
        print("==================================================")
        print("  SAM-DESK-AGENT AKTIF DI SISTEM TRAY WINDOWS     ")
        print("==================================================")
        print(f"[*] Tekan '{self.config.get('voice', {}).get('hotkey', '<alt>+space')}' untuk berbicara.")
        print("[*] Tekan 'Esc' 3 kali cepat untuk Panic Stop.")
        print("[*] Buka System Tray untuk menu atau keluar.")
        print("==================================================")

        self.hotkey_listener.start()
        self.tray.start()

    def stop(self):
        print("\n[*] Menutup Sam-Desk-Agent...")
        self.running = False
        self.hotkey_listener.stop()
        self.tray.stop()
        self.hud.hide()
        sys.exit(0)


def main():
    app = SamDeskAgentApp()
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()


if __name__ == "__main__":
    main()
