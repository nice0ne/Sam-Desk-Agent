# Sam-Desk-Agent 🎙️⚡

> **Hands-free Windows AI Desktop Assistant** powered by voice recognition, multi-provider LLM orchestration, and smart layered OS automation.

---

[🇬🇧 English](README.md) • [🇮🇩 Bahasa Indonesia](README.id.md)

---

## 🌟 Overview

**Sam-Desk-Agent** is an intelligent desktop companion designed for Windows 10 & 11. It listens for your voice commands via a global hotkey, interprets user intent using modern AI models (GLM, OpenAI, DeepSeek, Ollama, etc.), and executes multi-step actions across your operating system—from opening apps and focusing windows to typing text, browsing the web, and adjusting system volume.

---

## 🚀 Key Features

### 🎙️ 1. Voice-Driven Interaction (Push-to-Talk)
- **Global Hotkey Activation**: Press `<Alt> + <Space>` from anywhere in Windows to trigger listening.
- **Dual STT Engine**:
  - **Google Web Speech API**: Fast, lightweight, free, and highly accurate for Indonesian (`id-ID`) and English (`en-US`) without requiring heavy local model downloads.
  - **Faster-Whisper**: Local offline transcription fallback.
- **Natural Edge-TTS**: Expressive voice feedback powered by Microsoft Edge Neural Voices with full-sentence playback support.

### 🧠 2. Multi-AI Provider Support
- **Broad Model Compatibility**: Seamlessly connect to:
  - **GLM (ZhipuAI)**: `glm-4-plus`, `glm-4-flash`, etc.
  - **OpenAI**: `gpt-4o`, `gpt-4o-mini`, etc.
  - **DeepSeek**: `deepseek-chat`, `deepseek-reasoner`.
  - **Ollama**: Local models (`llama3`, `qwen2.5`, etc.).
  - **Custom OpenAI-Compatible Endpoints**: Any standard `/chat/completions` API.
- **Zero-Dependency Native HTTP Fallback**: Directly connects using Python's standard library (`urllib`), so the application runs even without the `openai` SDK package installed.
- **⚡ AI Connection Tester**: Test your API Key, Base URL, and Model directly from the graphical Settings window with round-trip latency reporting (ms) and instant error diagnostics (401, 404, 429).

### 🖥️ 3. Smart Window Management & Auto-Focus
- **Automatic Foreground Focus**: When opening applications like Notepad or File Explorer, Sam automatically brings the window to the front.
- **Windows Foreground Lock Bypass**: Utilizes Win32 API (`AttachThreadInput`, `VK_MENU` simulation, window restoration) to ensure newly launched windows gain active keyboard focus so subsequent typing actions never get lost in the background.
- **App & Window Alias Recognition**: Automatically handles localized titles, UWP app wrappers, and process aliases (e.g., File Explorer, Notepad, Calculator, VS Code, Chrome).

### ⚡ 4. Layered Desktop Automation
- **Layer 1 (OS & Shell)**: Fast direct execution for launching/closing applications, focusing windows, and controlling master volume (`pycaw`).
- **Layer 2 (UI Automation)**: Native Windows control inspection and element interaction.
- **Layer 3 (Vision & PyAutoGUI Fallback)**: High-speed multi-monitor screenshot capture (`mss`) and coordinate-based mouse clicking and dragging.

### 🌐 5. Integrated Web Search & Digital Tools
- Integrated DuckDuckGo search tool allows Sam to retrieve real-time data from the internet (e.g., recipes, documentation, weather) and type the summary directly into your open applications.

### 💾 6. SQLite Memory & Self-Learning
- Caches successful multi-step action sequences in a local SQLite database (`data/sam_memory.db`).
- Subsequent identical requests execute instantly with **zero API token cost**.
- Built-in guardrails prevent single-action skills from intercepting compound instructions.

### 🛑 7. Multi-Layer Fail-Safe Safety
- **Panic Stop**: Press `Esc` 3 times in rapid succession to immediately terminate all running actions.
- **Corner Fail-Safe**: Moving mouse cursor to the top-left corner `(0, 0)` instantly triggers PyAutoGUI failsafe.
- **HUD Emergency Button**: Clickable Stop icon on the floating screen capsule.

---

## 📋 System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version 3.10, 3.11, or 3.12
- **Audio**: Working Microphone and Speaker/Headphones

---

## 🛠️ Installation & Setup

### 1. Clone the Repository
```powershell
git clone https://github.com/nice0ne/Sam-Desk-Agent.git
cd Sam-Desk-Agent
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Your AI Provider
You can configure settings via the GUI after launching, or edit `config/config.yaml` directly:

```yaml
voice:
  hotkey: "<alt>+<space>"
  stt_provider: "google"        # "google" or "whisper"
  stt_language: "id-ID"         # "id-ID", "en-US", etc.
  tts_voice: "id-ID-ArdiNeural"

brain:
  provider: "glm"               # "glm", "openai", "deepseek", "ollama", "custom"
  model: "glm-4-flash"          # e.g., "glm-4-plus", "gpt-4o", "deepseek-chat"
  base_url: "https://open.bigmodel.cn/api/paas/v4/"
  api_key: "YOUR_API_KEY_HERE"  # Or set via environment variable
```

---

## 🎮 Running Sam-Desk-Agent

Launch the application:
```powershell
.\.venv\Scripts\python -m src.main
```

Once running, Sam lives unobtrusively in your **Windows System Tray** (notification area) with a semi-transparent **Floating HUD** on your screen.

---

## ⌨️ Controls & Shortcuts

| Action | Shortcut / Method | Description |
| :--- | :--- | :--- |
| **Push-to-Talk** | `<Alt> + <Space>` | Activate microphone and speak your command |
| **Panic Stop** | `Esc` (3x quickly) | Immediately cancel all active executions |
| **Corner Failsafe** | Move mouse to `(0,0)` | Emergency mouse abort |
| **Settings Window** | Right-click Tray ➔ **Pengaturan** | Configure Hotkey, AI Provider, API Key, and STT |
| **Memory Viewer** | Right-click Tray ➔ **Lihat Memori** | Inspect cached skills and learned commands |
| **Exit** | Right-click Tray ➔ **Keluar** | Gracefully quit the application |

---

## 🗣️ Example Voice Commands

| Example Voice Prompt | What Sam Does |
| :--- | :--- |
| *"Buka notepad dan ketikkan halo"* | Launches Notepad, focuses window to foreground, and types "halo". |
| *"Buka explorer"* | Opens Windows File Explorer and brings it to the front. |
| *"Naikkan volume 30%"* | Increases Windows master system volume by 30%. |
| *"Buka kalkulator"* | Launches Windows Calculator app. |
| *"Buka notepad, cari resep rendang di internet, lalu ketikkan"* | Searches DuckDuckGo for the recipe, opens Notepad, and pastes the result. |
| *"Fokus ke explorer"* | Brings existing File Explorer window to foreground. |

---

## 🧪 Running Automated Tests

Run the complete test suite (99 unit & integration tests):
```powershell
.\.venv\Scripts\python -m pytest -v
```

---

## 📂 Project Structure

```text
Sam-Desk-Agent/
├── config/
│   └── config.yaml          # Application configuration
├── data/
│   └── sam_memory.db        # SQLite database for learned skills & memory
├── src/
│   ├── brain/               # LLM client, prompt templates, tool registry
│   ├── core/                # Event bus, lifecycle, safety supervisor
│   ├── desktop/             # OS Controller, mouse/keyboard, window focus
│   ├── memory/              # SQLite skill store and learning engine
│   ├── tools/               # DuckDuckGo search, system info
│   ├── ui/                  # Floating HUD, system tray, settings GUI
│   ├── voice/               # STT engine, Edge-TTS, hotkey listener
│   └── main.py              # Application entry point
├── tests/                   # Pytest test suite (99 tests)
├── README.md                # English Documentation
├── README.id.md             # Indonesian Documentation
└── requirements.txt         # Project dependencies
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
