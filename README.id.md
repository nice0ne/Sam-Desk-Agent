# Sam-Desk-Agent 🎙️⚡

> **Asisten AI Desktop Windows Hands-free** berbasis perintah suara, integrasi multi-provider LLM, dan eksekusi otomasi OS bertingkat.

---

[🇬🇧 English](README.md) • [🇮🇩 Bahasa Indonesia](README.id.md)

---

## 🌟 Gambaran Umum

**Sam-Desk-Agent** adalah asisten desktop cerdas dan mandiri untuk Windows 10 & 11. Sam mendengarkan perintah suara Anda melalui tombol pintas global, memahami instruksi pengguna menggunakan model AI modern (GLM, OpenAI, DeepSeek, Ollama, dll.), serta mengeksekusi aksi bertahap langsung di sistem operasi—mulai dari membuka aplikasi dan memfokuskan jendela ke latar depan, mengetik teks, menjelajah internet, hingga mengatur volume Windows.

---

## 🚀 Fitur Utama

### 🎙️ 1. Interaksi Berbasis Suara (Push-to-Talk)
- **Aktivasi Hotkey Global**: Cukup tekan `<Alt> + <Space>` dari aplikasi apa pun untuk mulai mendengarkan.
- **Dua Pilihan Mesin STT (Speech-to-Text)**:
  - **Google Web Speech API**: Cepat, ringan, gratis, dan sangat akurat untuk Bahasa Indonesia (`id-ID`) dan Inggris (`en-US`) tanpa perlu mengunduh model lokal berukuran gigabyte.
  - **Faster-Whisper**: Opsi transkripsi offline lokal jika diperlukan.
- **Respon Suara Natural Edge-TTS**: Suara asisten AI berbahasa Indonesia yang ekspresif (*Neural Voice* Microsoft Edge) dengan pemutaran audio durasi penuh tanpa terpotong.

### 🧠 2. Dukungan Multi-AI Provider
- **Kompatibilitas Luas Berbagai AI**:
  - **GLM (ZhipuAI)**: `glm-4-plus`, `glm-4-flash`, dll.
  - **OpenAI**: `gpt-4o`, `gpt-4o-mini`, dll.
  - **DeepSeek**: `deepseek-chat`, `deepseek-reasoner`.
  - **Ollama**: Model lokal offline (`llama3`, `qwen2.5`, dll.).
  - **Endpoint Kustom OpenAI-Compatible**: Semua API standar dengan endpoint `/chat/completions`.
- **Mesin HTTP Native Zero-Dependency**: Panggilan API menggunakan pustaka standar Python (`urllib`) sehingga aplikasi dapat berjalan sempurna meskipun package SDK `openai` belum terinstal.
- **⚡ Fitur Tes Koneksi AI Langsung**: Uji API Key, Base URL, dan nama Model langsung dari menu Pengaturan GUI lengkap dengan indikator latensi (ms) dan diagnosa galat instan (401 invalid key, 404 model not found, 429 quota limit).

### 🖥️ 3. Manajemen Jendela Cerdas & Auto-Focus
- **Fokus Otomatis ke Layar Depan (*Foreground*)**: Saat membuka aplikasi seperti Notepad atau File Explorer, Sam otomatis menaikkan jendela aplikasi ke paling depan.
- **Bypass Windows Foreground Lock**: Memanfaatkan Win32 API (`AttachThreadInput`, simulasi `VK_MENU`, dan restorasi jendela) untuk memastikan jendela yang baru dibuka memperoleh fokus keyboard aktif sehingga pengetikan otomatis tidak tertinggal di latar belakang.
- **Pengenalan Alias & Class Aplikasi**: Mengenali judul jendela berbahasa Indonesia/Inggris, wrapper aplikasi UWP, dan nama proses (misal: File Explorer, Notepad, Kalkulator, VS Code, Chrome).

### ⚡ 4. Eksekusi Desktop Bertingkat (*Layered Execution*)
- **Layer 1 (OS & Shell)**: Eksekusi langsung super cepat untuk membuka/menutup aplikasi, fokus jendela, dan kontrol volume master Windows (`pycaw`).
- **Layer 2 (UI Automation)**: Inspeksi kontrol form dan tombol bawaan antarmuka Windows.
- **Layer 3 (Vision & PyAutoGUI Fallback)**: Tangkapan layar multi-monitor berkecepatan tinggi via `mss` serta klik dan drag koordinat mouse.

### 🌐 5. Pencarian Web & Integrasi Digital
- Dilengkapi tool DuckDuckGo Search untuk mencari data terkini di internet (resep masakan, dokumentasi, prakiraan cuaca, dll.) dan mengetikkan rangkumannya langsung ke dokumen Anda.

### 💾 6. Memori SQLite & Self-Learning
- Menyimpan alur tindakan yang berhasil ke dalam basis data SQLite lokal (`data/sam_memory.db`).
- Perintah identik yang pernah dipelajari akan dijalankan seketika dengan **biaya nol token API** (*zero-token execution*).
- Dilengkapi filter cerdas agar perintah majemuk tidak salah dieksekusi oleh memori tindakan tunggal.

### 🛑 7. Sistem Keamanan Bertingkat (*Fail-Safe*)
- **Panic Stop**: Tekan tombol `Esc` 3 kali berturut-turut untuk seketika membatalkan semua aksi yang sedang berjalan.
- **Corner Fail-Safe**: Gerakkan mouse ke pojok kiri atas monitor `(0, 0)` untuk memutus kontrol kursor `pyautogui`.
- **Tombol Darurat di HUD**: Tombol Stop yang dapat diklik langsung pada kapsul status mengambang di layar.

---

## 📋 Prasyarat Sistem

- **Sistem Operasi**: Windows 10 atau Windows 11 (64-bit)
- **Python**: Versi 3.10, 3.11, atau 3.12
- **Audio**: Mikrofon dan Speaker / Headset yang berfungsi

---

## 🛠️ Panduan Instalasi & Pengaturan

### 1. Clone Repository
```powershell
git clone https://github.com/nice0ne/Sam-Desk-Agent.git
cd Sam-Desk-Agent
```

### 2. Buat dan Aktifkan Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Pasang Dependensi
```powershell
pip install -r requirements.txt
```

### 4. Konfigurasi AI Provider
Anda dapat mengonfigurasi AI melalui menu Pengaturan di aplikasi, atau menyunting file `config/config.yaml` langsung:

```yaml
voice:
  hotkey: "<alt>+<space>"
  stt_provider: "google"        # "google" atau "whisper"
  stt_language: "id-ID"         # "id-ID", "en-US", dll.
  tts_voice: "id-ID-ArdiNeural"

brain:
  provider: "glm"               # "glm", "openai", "deepseek", "ollama", "custom"
  model: "glm-4-flash"          # misal: "glm-4-plus", "gpt-4o", "deepseek-chat"
  base_url: "https://open.bigmodel.cn/api/paas/v4/"
  api_key: "MASUKKAN_API_KEY_ANDA"
```

---

## 🎮 Menjalankan Sam-Desk-Agent

Jalankan perintah berikut di terminal:
```powershell
.\.venv\Scripts\python -m src.main
```

Setelah berjalan, Sam akan aktif secara senyap di **System Tray Windows** (pojok kanan bawah) disertai **Floating HUD** semi-transparan di layar monitor Anda.

---

## ⌨️ Kontrol Pintas & Menu

| Tindakan | Tombol / Cara | Keterangan |
| :--- | :--- | :--- |
| **Bicara (Push-to-Talk)** | `<Alt> + <Space>` | Mengaktifkan mikrofon dan mendengarkan instruksi |
| **Panic Stop (Darurat)** | `Esc` (3x cepat) | Membatalkan eksekusi tugas seketika |
| **Corner Failsafe** | Gerakkan mouse ke `(0,0)` | Menghentikan paksa kontrol mouse |
| **Menu Pengaturan** | Klik kanan Tray ➔ **Pengaturan** | Atur tombol pintas, AI Provider, API Key, dan STT |
| **Lihat Memori** | Klik kanan Tray ➔ **Lihat Memori** | Melihat daftar resep skill yang tersimpan di database |
| **Keluar** | Klik kanan Tray ➔ **Keluar** | Menutup dan menghentikan aplikasi |

---

## 🗣️ Contoh Perintah Suara

| Contoh Perintah Suara | Aksi yang Dilakukan Sam |
| :--- | :--- |
| *"Buka notepad dan ketikkan halo"* | Membuka Notepad, menaikkan jendela ke depan, dan mengetik "halo". |
| *"Buka explorer"* | Membuka File Explorer Windows dan memfokuskan jendelanya. |
| *"Naikkan volume 30%"* | Menaikkan volume sistem suara Windows sebesar 30%. |
| *"Buka kalkulator"* | Membuka aplikasi Kalkulator Windows. |
| *"Buka notepad, cari resep rendang di internet, lalu ketikkan"* | Mencari resep via DuckDuckGo, membuka Notepad, dan menyalin hasilnya ke dokumen. |
| *"Fokus ke explorer"* | Membawa jendela File Explorer yang sedang terbuka ke layar depan. |

---

## 🧪 Menjalankan Pengujian Otomatis (Testing Suite)

Jalankan seluruh pengujian unit & integrasi (99 tests lulus):
```powershell
.\.venv\Scripts\python -m pytest -v
```

---

## 📂 Struktur Direktori Proyek

```text
Sam-Desk-Agent/
├── config/
│   └── config.yaml          # Konfigurasi aplikasi
├── data/
│   └── sam_memory.db        # Database SQLite untuk memori & skill
├── src/
│   ├── brain/               # Klien LLM, template prompt, registry tools
│   ├── core/                # Event bus, lifecycle, supervisor keamanan
│   ├── desktop/             # OS Controller, mouse/keyboard, fokus jendela
│   ├── memory/              # Pengelola SQLite skill store & pembelajaran
│   ├── tools/               # DuckDuckGo search, ringkasan info sistem
│   ├── ui/                  # Floating HUD, system tray, jendela pengaturan
│   ├── voice/               # Mesin STT, Edge-TTS, hotkey listener
│   └── main.py              # Titik masuk utama aplikasi (entry point)
├── tests/                   # Kumpulan pengujian Pytest (99 tests)
├── README.md                # Dokumentasi Bahasa Inggris (Default)
├── README.id.md             # Dokumentasi Bahasa Indonesia
└── requirements.txt         # Daftar pustaka dependensi Python
```

---

## 📄 Lisensi

Didistribusikan di bawah Lisensi MIT. Lihat file `LICENSE` untuk informasi selengkapnya.
