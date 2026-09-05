# Sam-Desk-Agent 🎙️⚡

Asisten AI Desktop Windows hands-free berbasis perintah suara, dirancang dengan eksekusi bertingkat (OS API, UI Automation, Vision Fallback), web search tool calling, memori & self-learning (SQLite), dan panic kill-switch.

---

## Fitur Utama

- 🎙️ **Voice-Driven Push-to-Talk**: Aktifkan instan dengan tombol pintas global (default: `Alt + Space`).
- ⚡ **Smart Layered Execution**:
  - **Layer 1 (OS/Shell)**: Buka/tutup aplikasi, fokus jendela, atur volume Windows via `pycaw`.
  - **Layer 2 (UI Automation)**: Deteksi kontrol tombol dan form Windows.
  - **Layer 3 (Vision Fallback)**: Screenshot multi-monitor super cepat via `mss` dan klik koordinat mouse.
- 🌐 **Web Search & Digital Tools**: Mampu mencari informasi internet secara real-time via DuckDuckGo tanpa membuka browser fisik.
- 💾 **SQLite Memory & Self-Learning**: Menyimpan resep alur kerja yang berhasil dan mengingat preferensi pengguna (*zero-token repeated execution*).
- 🛑 **Fail-Safe Safety Engine**:
  - **Panic Switch**: Menekan `Esc` 3 kali berturut-turut langsung membatalkan eksekusi seketika.
  - **Corner Fail-Safe**: Menggeser mouse ke sudut pojok kiri atas monitor memutus kendali mouse `pyautogui`.
  - **HUD Stop Button**: Tombol pembatalan darurat pada status capsule mengambang.
- 🖥️ **Windows System Tray & Floating HUD**: Berjalan hening di system tray dengan status pill transparan di layar monitor.

---

## Panduan Instalasi & Menjalankan

### 1. Prasyarat
- Windows 10 atau 11 (64-bit)
- Python 3.10+ terinstal

### 2. Setup Virtual Environment
```powershell
# Masuk ke direktori
cd D:\VIBE-CODING\Sam-Desk-Agent

# Buat virtual environment
python -m venv .venv

# Aktivasi virtual environment
.\.venv\Scripts\activate
```

### 3. Instalasi Dependensi
```powershell
pip install -r requirements.txt
```

### 4. Menjalankan Pengujian Otomatis (Testing Suite)
```powershell
.\.venv\Scripts\python -m pytest -v
```

### 5. Menjalankan Sam-Desk-Agent
```powershell
.\.venv\Scripts\python -m src.main
```

---

## Kontrol Pintas & Contoh Perintah Suara

| Tindakan | Kontrol |
| :--- | :--- |
| **Bicara (Push-to-Talk)** | Tekan `Alt + Space` |
| **Panic Stop (Darurat)** | Tekan `Esc` 3 kali cepat ATAU geser mouse ke pojok kiri atas |
| **Jeda / Keluar** | Klik kanan ikon Sam di System Tray (kanan bawah) |

### Contoh Perintah:
- *"Naikkan volume 30%"* / *"Kecilkan volume 20%"*
- *"Buka Notepad, cari data di internet tentang resep rendang, lalu ketikkan"*
- *"Buka Paint, gambar bentuk persegi"*
- *"Buka Excel, ketik hello"*
- *"Tutup Word"*
