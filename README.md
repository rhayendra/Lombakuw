# Lombaku — Liquid Glass School Competition Platform

Aplikasi web berbasis **Python (Flask + SQLite + Openpyxl)** untuk mengelola seluruh kegiatan perlombaan sekolah: mulai dari informasi event, juknis, pendaftaran individu & tim, manajemen panitia, bracket turnamen interaktif, hingga ekspor laporan Excel (`.xlsx`).

## Fitur Utama

- **Liquid Glass UI** — Tampilan modern semi-transparan dengan ambient lighting, floating navigation, animasi halus, dan responsif untuk desktop, tablet, maupun HP.
- **3 Event Utama Default** — *Bulan Bahasa*, *PORAK*, dan *17 Agustus* (lengkap dengan data demo siap presentasi dan dapat diubah panitia).
- **Sistem Registrasi Tervalidasi Backend**:
  - 1 siswa hanya boleh mendaftar 1 cabang lomba per event (dicek berdasarkan NIS baik individu maupun anggota tim).
  - Wajib membuka & menyetujui Tab Juknis sebelum formulir aktif.
  - Auto-lock pendaftaran berdasarkan status event dan jadwal batas waktu.
  - Form Tim dinamis mengikuti minimal/maksimal anggota dan aturan wajib satu kelas.
- **Interactive Tournament Bracket**:
  - Otomatis membentuk babak penyisihan, perempat final, semifinal, hingga final (termasuk slot **BYE** otomatis).
  - Tombol **SHUFFLE** dengan animasi dan sound effect.
  - Kunci / buka kunci bracket oleh panitia.
  - Update skor, status `LIVE`, dan pemindahan pemenang otomatis ke babak berikutnya.
- **Export Data Excel (`.xlsx`)** — Ekspor semua event, event tertentu, atau cabang lomba tertentu lengkap dengan sheet ringkasan.
- **Sound Effect UI Halus** — Berbasis Web Audio API (tanpa file audio tambahan) dengan tombol **Sound ON/OFF**.

---

## Cara Menjalankan di Komputer Lokal

Pastikan **Python 3.9+** sudah terpasang.

### 1. Masuk ke folder proyek
```powershell
cd C:\Users\UserL\.gemini\antigravity\scratch\lombaku-liquid-glass
```

### 2. (Opsional tapi disarankan) Buat virtual environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install dependensi
```powershell
pip install -r requirements.txt
```

### 4. Jalankan aplikasi
```powershell
python app.py
```

### 5. Buka di Browser
- **Halaman Siswa / Beranda**: `http://127.0.0.1:5000`
- **Login Panitia / Admin**: `http://127.0.0.1:5000/admin/login`
  - Username default: `admin`
  - Password default: `admin123`

Database SQLite (`data/lombaku.db`) dan data demo akan otomatis dibuat saat pertama kali aplikasi dijalankan.

---

## Struktur Proyek

```text
lombaku/
├── app.py                 # Entry point utama Flask
├── config.py              # Konfigurasi aplikasi & path database
├── requirements.txt       # Daftar library Python (Flask, Werkzeug, openpyxl)
├── database/
│   ├── db.py              # Koneksi & skema tabel SQLite
│   └── seed.py            # Pengisi data demo presentasi
├── services/
│   ├── auth.py            # Hash password & autentikasi session panitia
│   ├── events.py          # Logika event, cabang lomba & pengecekan jadwal auto-lock
│   ├── registration.py    # Validasi pendaftaran individu & tim di backend
│   ├── bracket.py         # Generator bracket, BYE, shuffle, skor & advance winner
│   └── exporter.py        # Generator file Excel (.xlsx) menggunakan openpyxl
├── routes/
│   ├── public.py          # Halaman siswa (Home, Events, Register, Bracket, Info — full Jinja2)
│   ├── admin.py           # Halaman panitia (Dashboard, Participants, Management, Bracket, Export, Settings)
│   └── api.py             # Endpoint JSON API tambahan (opsional)
├── templates/             # Template HTML Jinja2 server-rendered (public, partial bracket & admin)
└── static/
    ├── css/liquid-glass.css
    ├── js/                # Hanya 2 helper ringan: ui.js (~80 baris) & sound.js (Web Audio)
    └── img/logo.svg
```
