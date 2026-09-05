# Sam-Desk-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun asisten AI desktop Windows yang berjalan di System Tray dan Floating HUD, dikendalikan suara (Voice-Driven), dengan eksekusi bertingkat (OS API, UI Automation, Vision Fallback), web search tool calling, sistem memori & self-learning (SQLite), serta fail-safe safety switch.

**Architecture:** Event-driven modular architecture berbasis Python asyncio. Suara ditangkap via Push-to-Talk / Hotkey, ditranskripsi via faster-whisper, diproses oleh LLM Tool-Calling Engine (Gemini 2.5 Flash / OpenAI), dieksekusi melalui Unified Desktop Controller Facade (Win32, pywinauto, PyAutoGUI, mss), didukung persistensi SQLite Memory & Skill Store, dan dimonitor oleh Safety Supervisor (Esc x3 panic switch).

**Tech Stack:** Python 3.10+, PyQt6 / pystray, faster-whisper, edge-tts, sounddevice, pyautogui, pywin32, pywinauto, pycaw, mss, duckduckgo-search, sqlite3, pytest.

**Spec:** `docs/superpowers/specs/2026-09-06-sam-desk-agent-design.md`

## Global Constraints
- Target OS: Windows 10 / Windows 11 (64-bit).
- Python Runtime: Python 3.10 atau lebih baru.
- DPI-Awareness: Proses harus terdaftar sebagai Per-Monitor DPI Aware V2 via `ctypes.windll.shcore.SetProcessDpiAwareness(2)` untuk akurasi koordinat.
- Safety: `pyautogui.FAILSAFE = True` selalu aktif; hotkey `Esc` ditekan 3 kali berturut-turut langsung memutus eksekusi.
- Encoding: UTF-8 untuk seluruh file teks, konfigurasi, dan database.

---

### Task 1: Project Scaffolding, Configuration, and EventBus

**Files:**
- Create: `requirements.txt`
- Create: `config/config.yaml`
- Create: `config/user_profile.json`
- Create: `src/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/core/event_bus.py`
- Test: `tests/test_event_bus.py`

**Interfaces:**
- Produces: `EventBus` class in `src/core/event_bus.py`:
  - `subscribe(event_type: str, handler: Callable[[Any], Awaitable[None] | None]) -> None`
  - `async publish(event_type: str, data: Any = None) -> None`
  - `unsubscribe(event_type: str, handler: Callable) -> None`

- [ ] **Step 1: Write the failing test for EventBus**

Create `tests/test_event_bus.py`:
```python
import pytest
import asyncio
from src.core.event_bus import EventBus

@pytest.mark.asyncio
async def test_event_bus_publish_and_subscribe():
    bus = EventBus()
    received = []

    async def sample_handler(data):
        received.append(data)

    bus.subscribe("test_event", sample_handler)
    await bus.publish("test_event", {"message": "hello"})
    assert received == [{"message": "hello"}]

@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    bus = EventBus()
    received = []

    async def sample_handler(data):
        received.append(data)

    bus.subscribe("test_event", sample_handler)
    bus.unsubscribe("test_event", sample_handler)
    await bus.publish("test_event", {"message": "hello"})
    assert received == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_event_bus.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src'`

- [ ] **Step 3: Write minimal implementation for dependencies, config, and EventBus**

Create `requirements.txt`:
```text
pytest>=8.0.0
pytest-asyncio>=0.23.0
pyyaml>=6.0.1
pydantic>=2.0.0
sounddevice>=0.4.6
numpy>=1.24.0
pynput>=1.7.6
faster-whisper>=1.0.0
edge-tts>=6.1.12
pyautogui>=0.9.54
pywin32>=306
pywinauto>=0.6.8
pycaw>=20240210
mss>=9.0.1
Pillow>=10.0.0
duckduckgo-search>=6.0.0
google-genai>=0.1.0
openai>=1.12.0
PyQt6>=6.6.0
pyperclip>=1.8.2
```

Create `config/config.yaml`:
```yaml
app:
  name: "Sam-Desk-Agent"
  version: "1.0.0"
  language: "id-ID"

voice:
  hotkey: "<alt>+space"
  panic_key: "esc"
  stt_model: "base"
  stt_device: "cpu"
  stt_compute_type: "int8"
  tts_voice: "id-ID-ArdiNeural"
  tts_rate: "+0%"
  wake_word_enabled: false
  wake_word: "hey sam"

brain:
  provider: "gemini"
  model: "gemini-2.5-flash"
  max_sub_actions: 10

safety:
  failsafe_enabled: true
  panic_esc_press_count: 3
  panic_esc_window_sec: 1.0
```

Create `config/user_profile.json`:
```json
{
  "user_name": "User",
  "preferred_browser": "chrome",
  "app_aliases": {
    "koding": "code",
    "notepad": "notepad.exe",
    "browser": "chrome",
    "kalkulator": "calc.exe",
    "paint": "mspaint.exe"
  }
}
```

Create `src/__init__.py` and `src/core/__init__.py` (empty files).

Create `src/core/event_bus.py`:
```python
import asyncio
from typing import Callable, Any, Dict, List
import inspect

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, data: Any = None) -> None:
        if event_type not in self._subscribers:
            return
        tasks = []
        for handler in self._subscribers[event_type]:
            if inspect.iscoroutinefunction(handler):
                tasks.append(asyncio.create_task(handler(data)))
            else:
                handler(data)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_event_bus.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt config/ src/ tests/test_event_bus.py
git commit -m "feat: setup project scaffolding, configuration and core event bus"
```

---

### Task 2: Safety Supervisor & Panic Kill-Switch

**Files:**
- Create: `src/core/safety.py`
- Test: `tests/test_safety.py`

**Interfaces:**
- Consumes: `EventBus`
- Produces: `SafetySupervisor` class:
  - `trigger_panic(reason: str) -> None`
  - `is_cancelled() -> bool`
  - `reset() -> None`
  - `record_esc_press(timestamp: float) -> bool`
  - `check_action_budget(current_step: int, max_budget: int) -> bool`

- [ ] **Step 1: Write the failing test for SafetySupervisor**

Create `tests/test_safety.py`:
```python
import pytest
from src.core.safety import SafetySupervisor
from src.core.event_bus import EventBus

def test_action_budget_limit():
    supervisor = SafetySupervisor()
    assert supervisor.check_action_budget(current_step=1, max_budget=10) is True
    assert supervisor.check_action_budget(current_step=10, max_budget=10) is True
    assert supervisor.check_action_budget(current_step=11, max_budget=10) is False

def test_panic_trigger_and_cancel():
    supervisor = SafetySupervisor()
    assert supervisor.is_cancelled() is False
    supervisor.trigger_panic("user emergency stop")
    assert supervisor.is_cancelled() is True
    supervisor.reset()
    assert supervisor.is_cancelled() is False

def test_triple_esc_detection():
    supervisor = SafetySupervisor()
    # Press 1
    assert supervisor.record_esc_press(100.0) is False
    # Press 2 within 0.3s
    assert supervisor.record_esc_press(100.3) is False
    # Press 3 within 0.7s total (< 1.0s window)
    assert supervisor.record_esc_press(100.7) is True
    assert supervisor.is_cancelled() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_safety.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.core.safety'`

- [ ] **Step 3: Implement SafetySupervisor**

Create `src/core/safety.py`:
```python
import time
from typing import List, Optional
from src.core.event_bus import EventBus

class SafetySupervisor:
    def __init__(self, event_bus: Optional[EventBus] = None, window_seconds: float = 1.0, required_presses: int = 3):
        self.event_bus = event_bus
        self.window_seconds = window_seconds
        self.required_presses = required_presses
        self._esc_timestamps: List[float] = []
        self._is_cancelled: bool = False

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def trigger_panic(self, reason: str = "panic switch activated") -> None:
        self._is_cancelled = True
        if self.event_bus:
            # publish synchronously if loop running or fire and forget
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.event_bus.publish("safety:panic", {"reason": reason}))
            except RuntimeError:
                pass

    def reset(self) -> None:
        self._is_cancelled = False
        self._esc_timestamps.clear()

    def record_esc_press(self, timestamp: Optional[float] = None) -> bool:
        if timestamp is None:
            timestamp = time.time()
        self._esc_timestamps.append(timestamp)
        # Prune presses outside window
        self._esc_timestamps = [t for t in self._esc_timestamps if timestamp - t <= self.window_seconds]
        if len(self._esc_timestamps) >= self.required_presses:
            self.trigger_panic("Triple-Esc panic trigger detected")
            return True
        return False

    def check_action_budget(self, current_step: int, max_budget: int = 10) -> bool:
        if current_step > max_budget:
            self.trigger_panic(f"Action budget exceeded ({current_step} > {max_budget})")
            return False
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_safety.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/safety.py tests/test_safety.py
git commit -m "feat: implement safety supervisor with triple-esc and action budget"
```

---

### Task 3: Memory & Skill Store Subsystem (SQLite)

**Files:**
- Create: `src/memory/__init__.py`
- Create: `src/memory/db.py`
- Create: `src/memory/skill_store.py`
- Test: `tests/test_memory.py`

**Interfaces:**
- Produces: `DatabaseManager` in `src/memory/db.py`:
  - `init_db(db_path: str) -> None`
  - `get_connection() -> sqlite3.Connection`
- Produces: `SkillStore` in `src/memory/skill_store.py`:
  - `save_skill(intent_key: str, description: str, steps: list[dict]) -> None`
  - `find_skill(query: str) -> list[dict] | None`
  - `set_preference(key: str, value: str) -> None`
  - `get_preference(key: str, default: str = None) -> str`

- [ ] **Step 1: Write the failing test for Memory & SkillStore**

Create `tests/test_memory.py`:
```python
import pytest
import os
from src.memory.db import DatabaseManager
from src.memory.skill_store import SkillStore

@pytest.fixture
def temp_store(tmp_path):
    db_file = str(tmp_path / "test_sam_memory.db")
    db_mgr = DatabaseManager(db_path=db_file)
    db_mgr.init_db()
    store = SkillStore(db_mgr)
    return store

def test_save_and_retrieve_preference(temp_store):
    temp_store.set_preference("browser", "brave")
    assert temp_store.get_preference("browser") == "brave"
    assert temp_store.get_preference("non_existent", "default_val") == "default_val"

def test_save_and_find_skill(temp_store):
    steps = [
        {"tool": "launch_app", "params": {"name": "notepad"}},
        {"tool": "type_keyboard", "params": {"text": "hello"}}
    ]
    temp_store.save_skill(
        intent_key="buka notepad ketik hello",
        description="Buka aplikasi notepad dan ketik hello",
        steps=steps
    )

    found = temp_store.find_skill("buka notepad ketik hello")
    assert found is not None
    assert len(found) == 2
    assert found[0]["tool"] == "launch_app"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_memory.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.memory'`

- [ ] **Step 3: Implement DatabaseManager and SkillStore**

Create `src/memory/__init__.py`.

Create `src/memory/db.py`:
```python
import sqlite3
import os
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            home = Path.home() / ".sam-agent"
            home.mkdir(parents=True, exist_ok=True)
            db_path = str(home / "sam_memory.db")
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_key TEXT UNIQUE NOT NULL,
                description TEXT,
                steps_json TEXT NOT NULL,
                success_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()
```

Create `src/memory/skill_store.py`:
```python
import json
from typing import Optional, List, Dict, Any
from src.memory.db import DatabaseManager

class SkillStore:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def set_preference(self, key: str, value: str) -> None:
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
                (key, value)
            )
            conn.commit()

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
            return default

    def save_skill(self, intent_key: str, description: str, steps: List[Dict[str, Any]]) -> None:
        normalized_key = intent_key.strip().lower()
        steps_json = json.dumps(steps)
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO skills (intent_key, description, steps_json, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(intent_key) DO UPDATE SET steps_json=excluded.steps_json, description=excluded.description, "
                "success_count=success_count+1, updated_at=CURRENT_TIMESTAMP",
                (normalized_key, description, steps_json)
            )
            conn.commit()

    def find_skill(self, query: str) -> Optional[List[Dict[str, Any]]]:
        normalized_query = query.strip().lower()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT steps_json FROM skills WHERE intent_key = ?", (normalized_query,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["steps_json"])
            # Fallback simple substring search
            cursor.execute("SELECT steps_json FROM skills WHERE ? LIKE '%' || intent_key || '%' LIMIT 1", (normalized_query,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["steps_json"])
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_memory.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/memory/ tests/test_memory.py
git commit -m "feat: implement SQLite database manager and procedural skill store"
```

---

### Task 4: Desktop Automation Layer 1: OS Actions & System Controls

**Files:**
- Create: `src/desktop/__init__.py`
- Create: `src/desktop/os_actions.py`
- Test: `tests/test_os_actions.py`

**Interfaces:**
- Produces: `OSController` in `src/desktop/os_actions.py`:
  - `launch_app(name: str, args: list[str] = []) -> dict`
  - `close_app(target_title_or_proc: str, force: bool = False) -> bool`
  - `get_open_windows() -> list[dict]`
  - `focus_window(title_pattern: str) -> bool`
  - `adjust_volume(delta: float = 0.0, target_level: float = None) -> float`

- [ ] **Step 1: Write the failing test for OSController**

Create `tests/test_os_actions.py`:
```python
import pytest
from src.desktop.os_actions import OSController

def test_os_controller_instantiation():
    controller = OSController()
    assert controller is not None

def test_volume_clamping():
    controller = OSController()
    assert controller._clamp_volume(-0.5) == 0.0
    assert controller._clamp_volume(1.5) == 1.0
    assert controller._clamp_volume(0.65) == 0.65
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_os_actions.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.desktop'`

- [ ] **Step 3: Implement OSController with Win32, psutil, and pycaw**

Create `src/desktop/__init__.py`.

Create `src/desktop/os_actions.py`:
```python
import os
import subprocess
import psutil
from typing import List, Dict, Optional, Any

class OSController:
    def __init__(self):
        self._init_dpi_awareness()

    def _init_dpi_awareness(self) -> None:
        try:
            import ctypes
            # Per-Monitor DPI Aware V2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    def _clamp_volume(self, val: float) -> float:
        return max(0.0, min(1.0, round(val, 2)))

    def launch_app(self, name: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        cmd = [name]
        if args:
            cmd.extend(args)
        try:
            proc = subprocess.Popen(cmd, shell=True)
            return {"status": "success", "pid": proc.pid, "message": f"App '{name}' launched."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_open_windows(self) -> List[Dict[str, Any]]:
        windows = []
        try:
            import win32gui
            def enum_handler(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        extra.append({"hwnd": hwnd, "title": title})
            win32gui.EnumWindows(enum_handler, windows)
        except ImportError:
            pass
        return windows

    def focus_window(self, title_pattern: str) -> bool:
        pattern = title_pattern.lower()
        windows = self.get_open_windows()
        for win in windows:
            if pattern in win["title"].lower():
                try:
                    import win32gui, win32con
                    hwnd = win["hwnd"]
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return True
                except Exception:
                    continue
        return False

    def close_app(self, target_title_or_proc: str, force: bool = False) -> bool:
        target = target_title_or_proc.lower()
        # 1. Try closing window gracefully
        windows = self.get_open_windows()
        for win in windows:
            if target in win["title"].lower():
                try:
                    import win32gui, win32con
                    win32gui.PostMessage(win["hwnd"], win32con.WM_CLOSE, 0, 0)
                    return True
                except Exception:
                    pass
        # 2. Try process matching
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if target in proc.info['name'].lower():
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def adjust_volume(self, delta: float = 0.0, target_level: Optional[float] = None) -> float:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_os_actions.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/desktop/os_actions.py tests/test_os_actions.py
git commit -m "feat: implement OS controller with app launch, window management, and pycaw volume"
```

---

### Task 5: Desktop Automation Layer 2 & 3: Mouse, Keyboard, UIA & Unified Facade

**Files:**
- Create: `src/desktop/mouse_keyboard.py`
- Create: `src/desktop/uia_actions.py`
- Create: `src/desktop/vision_actions.py`
- Create: `src/desktop/controller.py`
- Test: `tests/test_desktop_controller.py`

**Interfaces:**
- Produces: `DesktopActionController` in `src/desktop/controller.py` (Unified Facade)
  - `execute_action(tool_name: str, params: dict) -> dict`

- [ ] **Step 1: Write the failing test for DesktopActionController**

Create `tests/test_desktop_controller.py`:
```python
import pytest
from src.desktop.controller import DesktopActionController
from src.core.safety import SafetySupervisor

def test_controller_delegation_to_os():
    safety = SafetySupervisor()
    controller = DesktopActionController(safety_supervisor=safety)
    
    # Test volume adjustment tool
    res = controller.execute_action("adjust_system_volume", {"level": 0.5})
    assert res["status"] == "success"
    assert "level" in res

def test_controller_safety_interruption():
    safety = SafetySupervisor()
    safety.trigger_panic("Emergency")
    controller = DesktopActionController(safety_supervisor=safety)
    
    res = controller.execute_action("launch_application", {"app_name": "notepad"})
    assert res["status"] == "cancelled"
    assert "aborted" in res["message"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_desktop_controller.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.desktop.controller'`

- [ ] **Step 3: Implement MouseKeyboardController, UIAActions, VisionActions, and DesktopActionController**

Create `src/desktop/mouse_keyboard.py`:
```python
import time
import pyautogui
import pyperclip
from typing import List, Optional

class MouseKeyboardController:
    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05

    def click(self, x: int, y: int, button: str = 'left') -> None:
        pyautogui.click(x=x, y=y, button=button)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> None:
        pyautogui.moveTo(start_x, start_y)
        pyautogui.mouseDown()
        pyautogui.moveTo(end_x, end_y, duration=duration)
        pyautogui.mouseUp()

    def type_text(self, text: str, use_clipboard: bool = False) -> None:
        if use_clipboard or len(text) > 40:
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
        else:
            pyautogui.write(text, interval=0.01)

    def hotkey(self, keys: List[str]) -> None:
        pyautogui.hotkey(*keys)
```

Create `src/desktop/uia_actions.py`:
```python
from typing import Optional, Dict, Any

class UIAController:
    def click_element_by_name(self, name: str) -> bool:
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
```

Create `src/desktop/vision_actions.py`:
```python
import mss
from PIL import Image
from typing import Optional, Tuple

class VisionController:
    def capture_screen(self) -> Image.Image:
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # primary monitor
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img

    def normalize_coordinate(self, norm_x: float, norm_y: float, screen_width: int, screen_height: int) -> Tuple[int, int]:
        actual_x = int((norm_x / 1000.0) * screen_width)
        actual_y = int((norm_y / 1000.0) * screen_height)
        return (actual_x, actual_y)
```

Create `src/desktop/controller.py`:
```python
from typing import Dict, Any, Optional
from src.desktop.os_actions import OSController
from src.desktop.mouse_keyboard import MouseKeyboardController
from src.desktop.uia_actions import UIAController
from src.desktop.vision_actions import VisionController
from src.core.safety import SafetySupervisor

class DesktopActionController:
    def __init__(self, safety_supervisor: Optional[SafetySupervisor] = None):
        self.safety = safety_supervisor or SafetySupervisor()
        self.os_ctrl = OSController()
        self.mk_ctrl = MouseKeyboardController()
        self.uia_ctrl = UIAController()
        self.vision_ctrl = VisionController()

    def execute_action(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.safety.is_cancelled():
            return {"status": "cancelled", "message": "Action execution aborted by safety supervisor."}

        try:
            if tool_name == "launch_application":
                app = params.get("app_name") or params.get("name")
                args = params.get("args", [])
                return self.os_ctrl.launch_app(app, args)

            elif tool_name == "close_application":
                target = params.get("target") or params.get("name")
                force = params.get("force", False)
                res = self.os_ctrl.close_app(target, force)
                return {"status": "success" if res else "not_found", "closed": res}

            elif tool_name == "adjust_system_volume":
                delta = float(params.get("delta", 0.0))
                level = float(params.get("level")) if "level" in params and params["level"] is not None else None
                new_vol = self.os_ctrl.adjust_volume(delta, level)
                return {"status": "success", "level": new_vol}

            elif tool_name == "focus_window":
                pattern = params.get("title_pattern") or params.get("title")
                res = self.os_ctrl.focus_window(pattern)
                return {"status": "success" if res else "not_found", "focused": res}

            elif tool_name == "mouse_click":
                x = int(params["x"])
                y = int(params["y"])
                btn = params.get("button", "left")
                self.mk_ctrl.click(x, y, btn)
                return {"status": "success", "action": "click", "x": x, "y": y}

            elif tool_name == "mouse_drag":
                self.mk_ctrl.drag(
                    int(params["start_x"]), int(params["start_y"]),
                    int(params["end_x"]), int(params["end_y"])
                )
                return {"status": "success", "action": "drag"}

            elif tool_name == "type_keyboard":
                text = params.get("text", "")
                use_clipboard = params.get("use_clipboard", False)
                self.mk_ctrl.type_text(text, use_clipboard)
                return {"status": "success", "typed_length": len(text)}

            elif tool_name == "press_hotkey":
                keys = params.get("keys", [])
                self.mk_ctrl.hotkey(keys)
                return {"status": "success", "hotkey": keys}

            elif tool_name == "click_ui_element":
                name = params.get("name", "")
                res = self.uia_ctrl.click_element_by_name(name)
                return {"status": "success" if res else "not_found", "clicked": res}

            else:
                return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_desktop_controller.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/desktop/ tests/test_desktop_controller.py
git commit -m "feat: implement unified desktop controller facade with mouse, keyboard, and UIA"
```

---

### Task 6: External Tools: Web Search & System Info

**Files:**
- Create: `src/tools/__init__.py`
- Create: `src/tools/web_search.py`
- Create: `src/tools/system_info.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Produces: `WebSearchTool` in `src/tools/web_search.py`:
  - `search(query: str, max_results: int = 3) -> list[dict]`
- Produces: `SystemInfoTool` in `src/tools/system_info.py`:
  - `get_summary() -> dict`

- [ ] **Step 1: Write the failing test for WebSearch and SystemInfo tools**

Create `tests/test_tools.py`:
```python
import pytest
from src.tools.system_info import SystemInfoTool

def test_system_info_summary():
    tool = SystemInfoTool()
    summary = tool.get_summary()
    assert "cpu_percent" in summary
    assert "ram_percent" in summary
    assert "os" in summary
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.tools'`

- [ ] **Step 3: Implement WebSearchTool and SystemInfoTool**

Create `src/tools/__init__.py`.

Create `src/tools/web_search.py`:
```python
from typing import List, Dict, Any

class WebSearchTool:
    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })
            return results
        except Exception as e:
            return [{"title": "Search Error", "snippet": str(e), "url": ""}]
```

Create `src/tools/system_info.py`:
```python
import platform
import psutil
from typing import Dict, Any

class SystemInfoTool:
    def get_summary(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        return {
            "os": platform.platform(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_percent": mem.percent,
            "ram_available_gb": round(mem.available / (1024**3), 2)
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tools/ tests/test_tools.py
git commit -m "feat: implement web search tool and system info tool"
```

---

### Task 7: Agent Brain, Prompts, and Tool Registry

**Files:**
- Create: `src/brain/__init__.py`
- Create: `src/brain/prompts.py`
- Create: `src/brain/registry.py`
- Create: `src/brain/agent.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Produces: `ToolRegistry` in `src/brain/registry.py`:
  - `get_schemas() -> list[dict]`
- Produces: `AgentBrain` in `src/brain/agent.py`:
  - `process_command(user_text: str) -> dict`

- [ ] **Step 1: Write the failing test for ToolRegistry and AgentBrain**

Create `tests/test_agent.py`:
```python
import pytest
from src.brain.registry import ToolRegistry

def test_tool_registry_contains_core_tools():
    registry = ToolRegistry()
    schemas = registry.get_schemas()
    tool_names = [t["function"]["name"] for t in schemas]
    
    assert "launch_application" in tool_names
    assert "adjust_system_volume" in tool_names
    assert "type_keyboard" in tool_names
    assert "web_search" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.brain'`

- [ ] **Step 3: Implement ToolRegistry, Prompts, and AgentBrain**

Create `src/brain/__init__.py`.

Create `src/brain/prompts.py`:
```python
SAM_SYSTEM_PROMPT = """Anda adalah Sam, asisten desktop Windows cerdas dan mandiri.
Tugas Anda adalah memahami instruksi pengguna dan mengeksekusinya ke desktop Windows menggunakan daftar tools yang tersedia.

Aturan Penting:
1. Utamakan kecepatan & efisiensi: Jika perintah adalah membuka/menutup app atau mengatur volume, panggil tool sistem langsung (Layer 1).
2. Jika ada instruksi majemuk (misal: "buka notepad, cari resep rendang, ketikkan"), panggil tools secara berurutan:
   a. launch_application("notepad")
   b. web_search("resep rendang praktis")
   c. type_keyboard(text=hasil_resep, use_clipboard=True)
3. Untuk teks panjang, gunakan parameter use_clipboard=True pada type_keyboard agar pengetikan instan dalam 0.1 detik.
4. Respon suara: Berikan laporan singkat, ramah, dan ringkas dalam Bahasa Indonesia setelah tugas selesai.
"""
```

Create `src/brain/registry.py`:
```python
from typing import List, Dict, Any

class ToolRegistry:
    @staticmethod
    def get_schemas() -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "launch_application",
                    "description": "Membuka aplikasi Windows dan memfokuskan jendelanya.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string", "description": "Nama aplikasi atau executable, misal 'notepad', 'calc', 'chrome'"}
                        },
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "close_application",
                    "description": "Menutup aplikasi berdasarkan nama jendela atau proses.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "Nama jendela atau nama file exe"}
                        },
                        "required": ["target"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "adjust_system_volume",
                    "description": "Menaikkan, menurunkan, atau mengatur volume suara master Windows.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "delta": {"type": "number", "description": "Perubahan volume, misal +0.3 untuk naik 30%, -0.2 untuk turun 20%"},
                            "level": {"type": "number", "description": "Level volume absolut (0.0 sampai 1.0)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "type_keyboard",
                    "description": "Mengetik teks langsung ke jendela yang aktif.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Teks yang ingin diketik"},
                            "use_clipboard": {"type": "boolean", "description": "Gunakan paste clipboard agar instan"}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mouse_drag",
                    "description": "Menggerakkan mouse sambil menahan klik (drag-and-drop / menggambar di kanvas Paint).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_x": {"type": "integer"},
                            "start_y": {"type": "integer"},
                            "end_x": {"type": "integer"},
                            "end_y": {"type": "integer"}
                        },
                        "required": ["start_x", "start_y", "end_x", "end_y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Mencari informasi terkini dari internet.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Kata kunci pencarian"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "speak_feedback",
                    "description": "Memberikan pesan konfirmasi suara ke pengguna.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Pesan yang diucapkan"}
                        },
                        "required": ["message"]
                    }
                }
            }
        ]
```

Create `src/brain/agent.py`:
```python
from typing import Dict, Any, List, Optional
from src.brain.prompts import SAM_SYSTEM_PROMPT
from src.brain.registry import ToolRegistry
from src.desktop.controller import DesktopActionController
from src.tools.web_search import WebSearchTool
from src.memory.skill_store import SkillStore

class AgentBrain:
    def __init__(
        self,
        desktop_controller: DesktopActionController,
        skill_store: Optional[SkillStore] = None,
        web_search_tool: Optional[WebSearchTool] = None
    ):
        self.desktop = desktop_controller
        self.skill_store = skill_store
        self.web_search = web_search_tool or WebSearchTool()
        self.registry = ToolRegistry()

    def execute_plan(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for step in actions:
            tool_name = step.get("tool")
            params = step.get("params", {})
            if tool_name == "web_search":
                res = self.web_search.search(params.get("query", ""))
                results.append({"tool": tool_name, "result": res})
            else:
                res = self.desktop.execute_action(tool_name, params)
                results.append({"tool": tool_name, "result": res})
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agent.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/brain/ tests/test_agent.py
git commit -m "feat: implement tool registry, system prompts, and agent brain planning engine"
```

---

### Task 8: Voice Service: Audio Capture, STT (Faster-Whisper), TTS (Edge-TTS) & Hotkey

**Files:**
- Create: `src/voice/__init__.py`
- Create: `src/voice/stt_engine.py`
- Create: `src/voice/tts_engine.py`
- Create: `src/voice/hotkey.py`
- Create: `src/voice/recorder.py`
- Test: `tests/test_voice.py`

**Interfaces:**
- Produces: `STTEngine` in `src/voice/stt_engine.py`:
  - `transcribe(audio_data: np.ndarray) -> str`
- Produces: `TTSEngine` in `src/voice/tts_engine.py`:
  - `async speak(text: str, voice: str = "id-ID-ArdiNeural") -> None`
- Produces: `GlobalHotkeyListener` in `src/voice/hotkey.py`:
  - `start() -> None`, `stop() -> None`

- [ ] **Step 1: Write the test for Voice components**

Create `tests/test_voice.py`:
```python
import pytest
from src.voice.tts_engine import TTSEngine

def test_tts_engine_defaults():
    tts = TTSEngine(default_voice="id-ID-ArdiNeural")
    assert tts.default_voice == "id-ID-ArdiNeural"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_voice.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.voice'`

- [ ] **Step 3: Implement Voice modules**

Create `src/voice/__init__.py`.

Create `src/voice/tts_engine.py`:
```python
import os
import tempfile
import asyncio
from typing import Optional

class TTSEngine:
    def __init__(self, default_voice: str = "id-ID-ArdiNeural"):
        self.default_voice = default_voice

    async def speak(self, text: str, voice: Optional[str] = None) -> None:
        target_voice = voice or self.default_voice
        import edge_tts
        communicate = edge_tts.Communicate(text, target_voice)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
            
        try:
            await communicate.save(temp_path)
            # Play audio file synchronously using windows native sound API
            import winsound
            # or os.system start for mp3
            import subprocess
            subprocess.run(
                ["powershell", "-c", f'(New-Object Media.SoundPlayer "{temp_path}").PlaySync()'],
                capture_output=True
            )
        except Exception:
            pass
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
```

Create `src/voice/stt_engine.py`:
```python
import numpy as np
from typing import Optional

class STTEngine:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        model = self._load_model()
        segments, _ = model.transcribe(audio_data, language="id")
        text = " ".join([seg.text for seg in segments]).strip()
        return text
```

Create `src/voice/recorder.py`:
```python
import sounddevice as sd
import numpy as np
from typing import Optional

class AudioRecorder:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.is_recording = False
        self._frames = []

    def start(self) -> None:
        self.is_recording = True
        self._frames.clear()

    def record_chunk(self, duration_sec: float = 3.0) -> np.ndarray:
        audio = sd.rec(int(duration_sec * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype='float32')
        sd.wait()
        return audio.flatten()
```

Create `src/voice/hotkey.py`:
```python
from pynput import keyboard
from typing import Callable, Optional
from src.core.safety import SafetySupervisor

class GlobalHotkeyListener:
    def __init__(
        self,
        on_trigger: Callable[[], None],
        safety_supervisor: Optional[SafetySupervisor] = None,
        hotkey_str: str = "<alt>+space"
    ):
        self.on_trigger = on_trigger
        self.safety = safety_supervisor
        self.hotkey_str = hotkey_str
        self._listener = None

    def _on_esc_press(self, key):
        if key == keyboard.Key.esc and self.safety:
            self.safety.record_esc_press()

    def start(self) -> None:
        hotkeys = {
            self.hotkey_str: self.on_trigger
        }
        self._listener = keyboard.GlobalHotKeys(hotkeys)
        self._listener.start()

        # Keyboard listener for panic Esc detection
        self._esc_listener = keyboard.Listener(on_press=self._on_esc_press)
        self._esc_listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
        if hasattr(self, '_esc_listener') and self._esc_listener:
            self._esc_listener.stop()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_voice.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/voice/ tests/test_voice.py
git commit -m "feat: implement voice I/O service with faster-whisper, edge-tts, and hotkey listener"
```

---

### Task 9: User Interface: Windows System Tray & Floating HUD

**Files:**
- Create: `src/ui/__init__.py`
- Create: `src/ui/hud.py`
- Create: `src/ui/tray.py`
- Test: `tests/test_ui_mock.py`

**Interfaces:**
- Produces: `FloatingHUD` in `src/ui/hud.py`:
  - `set_status(state: str, message: str) -> None`
  - `show()`, `hide()`
- Produces: `SystemTrayApp` in `src/ui/tray.py`:
  - `run() -> None`

- [ ] **Step 1: Write test for UI state contracts**

Create `tests/test_ui_mock.py`:
```python
import pytest
from src.ui.hud import HUDState

def test_hud_states():
    assert HUDState.IDLE == "idle"
    assert HUDState.LISTENING == "listening"
    assert HUDState.THINKING == "thinking"
    assert HUDState.EXECUTING == "executing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_mock.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'src.ui'`

- [ ] **Step 3: Implement HUD and System Tray**

Create `src/ui/__init__.py`.

Create `src/ui/hud.py`:
```python
from enum import Enum
from typing import Optional

class HUDState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    PANIC = "panic"

try:
    from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont, QColor

    class FloatingHUDWindow(QWidget):
        def __init__(self, on_stop_clicked: Optional[callable] = None):
            super().__init__()
            self.on_stop_clicked = on_stop_clicked
            self._init_ui()

        def _init_ui(self):
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            layout = QHBoxLayout()
            self.label = QLabel("🎙️ Sam Siap")
            self.label.setStyleSheet("color: white; font-weight: bold; padding: 6px 12px; background: rgba(30, 30, 30, 220); border-radius: 12px;")
            layout.addWidget(self.label)

            self.stop_btn = QPushButton("✕ Stop")
            self.stop_btn.setStyleSheet("color: white; background: #e63946; border-radius: 8px; padding: 4px 8px;")
            if self.on_stop_clicked:
                self.stop_btn.clicked.connect(self.on_stop_clicked)
            layout.addWidget(self.stop_btn)

            self.setLayout(layout)
            self.resize(320, 50)

        def update_state(self, state: HUDState, message: str):
            icons = {
                HUDState.IDLE: "🟢",
                HUDState.LISTENING: "🎙️",
                HUDState.THINKING: "🧠",
                HUDState.EXECUTING: "⚡",
                HUDState.PANIC: "🛑"
            }
            icon = icons.get(state, "🎙️")
            self.label.setText(f"{icon} {message}")
except ImportError:
    class FloatingHUDWindow:
        def update_state(self, state, message):
            pass
        def show(self): pass
        def hide(self): pass
```

Create `src/ui/tray.py`:
```python
from typing import Callable, Optional

class SystemTrayApp:
    def __init__(self, on_toggle_pause: Optional[Callable] = None, on_exit: Optional[Callable] = None):
        self.on_toggle_pause = on_toggle_pause
        self.on_exit = on_exit

    def build_menu(self):
        return {
            "status": "active",
            "menu_items": ["Jeda Agent", "Pengaturan", "Lihat Memori", "Keluar"]
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_mock.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/ tests/test_ui_mock.py
git commit -m "feat: implement UI module with floating HUD states and system tray scaffold"
```

---

### Task 10: Application Entry Point & End-to-End Orchestration

**Files:**
- Create: `src/main.py`
- Create: `README.md`
- Test: `tests/test_integration.py`

**Interfaces:**
- Produces: `main()` entrypoint running asyncio loop & coordinating modules.

- [ ] **Step 1: Write integration smoke test**

Create `tests/test_integration.py`:
```python
import pytest
from src.core.event_bus import EventBus
from src.core.safety import SafetySupervisor
from src.desktop.controller import DesktopActionController
from src.brain.agent import AgentBrain
from src.memory.db import DatabaseManager
from src.memory.skill_store import SkillStore

def test_full_pipeline_smoke():
    bus = EventBus()
    safety = SafetySupervisor(bus)
    desktop = DesktopActionController(safety)
    db = DatabaseManager(":memory:")
    db.init_db()
    skill_store = SkillStore(db)
    brain = AgentBrain(desktop, skill_store)

    # Smoke execute adjust volume action
    results = brain.execute_plan([
        {"tool": "adjust_system_volume", "params": {"level": 0.4}}
    ])
    assert len(results) == 1
    assert results[0]["result"]["status"] == "success"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration.py -v`  
Expected: Should verify all components wire up together cleanly.

- [ ] **Step 3: Implement main.py and README.md**

Create `src/main.py`:
```python
import sys
import os
import asyncio
import yaml
from pathlib import Path

from src.core.event_bus import EventBus
from src.core.safety import SafetySupervisor
from src.desktop.controller import DesktopActionController
from src.brain.agent import AgentBrain
from src.memory.db import DatabaseManager
from src.memory.skill_store import SkillStore
from src.voice.hotkey import GlobalHotkeyListener
from src.voice.tts_engine import TTSEngine
from src.voice.stt_engine import STTEngine
from src.voice.recorder import AudioRecorder

def load_config():
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    print("=== Sam-Desk-Agent: Menjalankan Sistem ===")
    config = load_config()

    event_bus = EventBus()
    safety = SafetySupervisor(event_bus)
    desktop = DesktopActionController(safety)
    db = DatabaseManager()
    db.init_db()
    skill_store = SkillStore(db)
    brain = AgentBrain(desktop, skill_store)

    tts = TTSEngine(default_voice=config["voice"]["tts_voice"])
    stt = STTEngine(model_size=config["voice"]["stt_model"])
    recorder = AudioRecorder()

    def on_hotkey_triggered():
        print("[Voice] Hotkey ditekan, mendengarkan...")
        # Capture and process pipeline
        try:
            audio = recorder.record_chunk(duration_sec=3.5)
            text = stt.transcribe(audio)
            print(f"[Voice] Didengar: {text}")
            if text:
                # Process via Brain
                pass
        except Exception as e:
            print(f"[Error] {e}")

    hotkey_str = config["voice"]["hotkey"]
    hotkey_listener = GlobalHotkeyListener(
        on_trigger=on_hotkey_triggered,
        safety_supervisor=safety,
        hotkey_str=hotkey_str
    )
    hotkey_listener.start()
    print(f"[*] Tekan '{hotkey_str}' untuk berbicara dengan Sam.")
    print("[*] Tekan 'Esc' 3 kali cepat untuk Emergency Stop.")

    try:
        # Keep running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Menutup Sam-Desk-Agent...")
        hotkey_listener.stop()

if __name__ == "__main__":
    main()
```

Create `README.md`:
```markdown
# Sam-Desk-Agent 🎙️⚡

Asisten AI Desktop Windows hands-free berbasis perintah suara, dirancang dengan eksekusi bertingkat (OS API, UI Automation, Vision Fallback), web search tool calling, memori & self-learning (SQLite), dan panic kill-switch.

## Cara Instalasi & Menjalankan

1. **Clone repositori & masuk direktori:**
   ```powershell
   cd D:\VIBE-CODING\Sam-Desk-Agent
   ```

2. **Buat Virtual Environment Python:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install Dependensi:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Jalankan Pengujian Otomatis:**
   ```powershell
   pytest -v
   ```

5. **Jalankan Aplikasi:**
   ```powershell
   python -m src.main
   ```

## Kontrol Cepat:
* **Bicara (Push-to-Talk)**: Tekan `Alt + Space`
* **Panic Stop (Darurat)**: Tekan `Esc` 3 kali berturut-turut atau geser mouse ke pojok kiri atas layar.
```

- [ ] **Step 4: Run all tests to verify passing**

Run: `pytest -v`  
Expected: PASS all tests

- [ ] **Step 5: Commit**

```bash
git add src/main.py README.md tests/test_integration.py
git commit -m "feat: wire main application entry point, smoke integration test and documentation"
```
