"""Settings Window for Sam-Desk-Agent.

Provides a graphical user interface to configure voice hotkeys, STT/TTS models,
AI providers, API keys, and safety settings, saving directly to config/config.yaml.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Callable
import tkinter as tk
from tkinter import ttk, messagebox


def get_config_path() -> Path:
    base_dir = Path(__file__).resolve().parent.parent.parent
    return base_dir / "config" / "config.yaml"


class SettingsWindow:
    """Settings GUI Dialog for Sam-Desk-Agent."""

    def __init__(self, on_save_callback: Optional[Callable[[dict], None]] = None, master: Optional[tk.Tk] = None):
        self.on_save_callback = on_save_callback
        self.config_path = get_config_path()
        self.config_data = self.load_config()
        self.master = master
        self.root: Optional[tk.Toplevel | tk.Tk] = None

    def load_config(self) -> dict:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {
            "app": {"name": "Sam-Desk-Agent", "language": "id-ID"},
            "voice": {
                "hotkey": "<alt>+space",
                "panic_key": "esc",
                "stt_model": "base",
                "tts_voice": "id-ID-ArdiNeural"
            },
            "brain": {
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "max_sub_actions": 10
            },
            "safety": {
                "panic_esc_press_count": 3
            }
        }

    def save_config(self, new_config: dict) -> bool:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(new_config, f, default_flow_style=False, sort_keys=False)
            self.config_data = new_config
            if self.on_save_callback:
                self.on_save_callback(new_config)
            return True
        except Exception as e:
            if self.root:
                messagebox.showerror("Error", f"Gagal menyimpan konfigurasi: {e}")
            return False

    def show(self) -> None:
        """Display the Settings window."""
        if self.root is not None and self.root.winfo_exists():
            self.root.lift()
            return

        if self.master:
            self.root = tk.Toplevel(self.master)
        else:
            self.root = tk.Tk()

        self.root.title("Pengaturan - Sam-Desk-Agent")
        self.root.geometry("520x540")
        self.root.minsize(480, 480)
        self.root.attributes("-topmost", True)

        # Style configuration
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        main_frame = ttk.Frame(self.root, padding="15 15 15 15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame,
            text="⚙️ Pengaturan Sam-Desk-Agent",
            font=("Segoe UI", 13, "bold")
        )
        title_label.pack(anchor=tk.W, pady=(0, 15))

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Suara & Pemicu
        tab_voice = ttk.Frame(notebook, padding="12")
        notebook.add(tab_voice, text="🎙️ Suara & Hotkey")

        ttk.Label(tab_voice, text="Hotkey Push-to-Talk:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=6)
        self.var_hotkey = tk.StringVar(value=self.config_data.get("voice", {}).get("hotkey", "<alt>+space"))
        ttk.Entry(tab_voice, textvariable=self.var_hotkey, width=25).grid(row=0, column=1, sticky=tk.W, padx=10)

        ttk.Label(tab_voice, text="Model STT (Whisper):", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.var_stt_model = tk.StringVar(value=self.config_data.get("voice", {}).get("stt_model", "base"))
        stt_combo = ttk.Combobox(tab_voice, textvariable=self.var_stt_model, values=["tiny", "base", "small", "medium"], width=23, state="readonly")
        stt_combo.grid(row=1, column=1, sticky=tk.W, padx=10)

        ttk.Label(tab_voice, text="Suara TTS (Edge-TTS):", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=6)
        self.var_tts_voice = tk.StringVar(value=self.config_data.get("voice", {}).get("tts_voice", "id-ID-ArdiNeural"))
        tts_combo = ttk.Combobox(tab_voice, textvariable=self.var_tts_voice, values=[
            "id-ID-ArdiNeural",
            "id-ID-GadisNeural",
            "en-US-GuyNeural",
            "en-US-JennyNeural"
        ], width=23, state="readonly")
        tts_combo.grid(row=2, column=1, sticky=tk.W, padx=10)

        # Tab 2: AI & Brain
        tab_brain = ttk.Frame(notebook, padding="12")
        notebook.add(tab_brain, text="🧠 AI & Model")

        ttk.Label(tab_brain, text="AI Provider:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=6)
        self.var_provider = tk.StringVar(value=self.config_data.get("brain", {}).get("provider", "gemini"))
        provider_combo = ttk.Combobox(tab_brain, textvariable=self.var_provider, values=["gemini", "openai"], width=23, state="readonly")
        provider_combo.grid(row=0, column=1, sticky=tk.W, padx=10)

        ttk.Label(tab_brain, text="Nama Model:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.var_model = tk.StringVar(value=self.config_data.get("brain", {}).get("model", "gemini-2.5-flash"))
        ttk.Entry(tab_brain, textvariable=self.var_model, width=25).grid(row=1, column=1, sticky=tk.W, padx=10)

        ttk.Label(tab_brain, text="Batas Sub-Aksi (Budget):", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=6)
        self.var_budget = tk.StringVar(value=str(self.config_data.get("brain", {}).get("max_sub_actions", 10)))
        ttk.Entry(tab_brain, textvariable=self.var_budget, width=25).grid(row=2, column=1, sticky=tk.W, padx=10)

        ttk.Label(tab_brain, text="API Key (Env: GEMINI_API_KEY):", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=6)
        self.var_api_key = tk.StringVar(value=os.environ.get("GEMINI_API_KEY", ""))
        api_entry = ttk.Entry(tab_brain, textvariable=self.var_api_key, width=25, show="*")
        api_entry.grid(row=3, column=1, sticky=tk.W, padx=10)

        # Tab 3: Keamanan
        tab_safety = ttk.Frame(notebook, padding="12")
        notebook.add(tab_safety, text="🛡️ Keamanan")

        ttk.Label(tab_safety, text="Tombol Panic:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=6)
        self.var_panic_key = tk.StringVar(value=self.config_data.get("voice", {}).get("panic_key", "esc"))
        ttk.Entry(tab_safety, textvariable=self.var_panic_key, width=20, state="readonly").grid(row=0, column=1, sticky=tk.W, padx=10)

        ttk.Label(tab_safety, text="Tekan Esc Beruntun:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=6)
        self.var_esc_count = tk.StringVar(value=str(self.config_data.get("safety", {}).get("panic_esc_press_count", 3)))
        ttk.Entry(tab_safety, textvariable=self.var_esc_count, width=20).grid(row=1, column=1, sticky=tk.W, padx=10)

        ttk.Label(
            tab_safety,
            text="* Geser mouse ke pojok kiri atas monitor juga otomatis memutus kendali mouse.",
            foreground="#666666",
            wraplength=380
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=15)

        # Bottom buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        btn_save = ttk.Button(btn_frame, text="💾 Simpan & Terapkan", command=self._on_save_click)
        btn_save.pack(side=tk.RIGHT, padx=5)

        btn_close = ttk.Button(btn_frame, text="Tutup", command=self.root.destroy)
        btn_close.pack(side=tk.RIGHT)

        if not self.master:
            self.root.mainloop()

    def _on_save_click(self) -> None:
        try:
            budget_val = int(self.var_budget.get())
        except ValueError:
            budget_val = 10

        try:
            esc_val = int(self.var_esc_count.get())
        except ValueError:
            esc_val = 3

        new_config = dict(self.config_data)
        new_config.setdefault("voice", {})
        new_config["voice"]["hotkey"] = self.var_hotkey.get().strip()
        new_config["voice"]["stt_model"] = self.var_stt_model.get().strip()
        new_config["voice"]["tts_voice"] = self.var_tts_voice.get().strip()

        new_config.setdefault("brain", {})
        new_config["brain"]["provider"] = self.var_provider.get().strip()
        new_config["brain"]["model"] = self.var_model.get().strip()
        new_config["brain"]["max_sub_actions"] = budget_val

        new_config.setdefault("safety", {})
        new_config["safety"]["panic_esc_press_count"] = esc_val

        api_key_val = self.var_api_key.get().strip()
        if api_key_val:
            os.environ["GEMINI_API_KEY"] = api_key_val
            os.environ["OPENAI_API_KEY"] = api_key_val

        if self.save_config(new_config):
            messagebox.showinfo("Sukses", "Pengaturan berhasil disimpan dan diterapkan!")
            if self.root:
                self.root.destroy()
