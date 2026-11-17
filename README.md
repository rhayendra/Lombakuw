# LombaKu — Portal Kompetisi & Kejuaraan Sekolah (Python + SQLite Edition)

Aplikasi **LombaKu** adalah portal digital perlombaan sekolah yang telah dibangun ulang sepenuhnya menggunakan **Python** dan database **SQLite (`sqlite3` Python Standard Library)** dengan antarmuka **Soft Pastel Modern Mobile-First UI**.

---

## 1. Struktur Proyek Modular

```text
lombaku/
├── app.py                   # Entry point utama server Python & routing HTTP/API
├── backend/                 # Paket logika backend Python modular
│   ├── __init__.py
│   ├── database.py          # Koneksi & tabel SQLite (sqlite3) + migrasi data otomatis
│   ├── models.py            # Logika bisnis event, kuota, jadwal, & profil peserta
│   ├── auth.py              # Autentikasi Peserta & Panitia + generator ID/Password
│   ├── bracket.py           # Algoritma pengacakan (Shuffle) & pemajuan bagan
│   └── excel_export.py      # Ekspor laporan Excel (.xlsx) multi-sheet
├── data/
│   ├── lombaku.db           # Database SQLite utama (otomatis dibuat saat server jalan)
│   └── db.json              # Data cadangan & seed awal
├── templates/               # Template Halaman HTML
│   ├── index.html           # Landing Page (Hero Scenic, Explore, Recommended, Jadwal & Bagan)
│   ├── daftar.html          # Halaman Event, Ilustrasi Kategori, Persyaratan & Form Daftar
│   └── peserta.html         # Dashboard Pengguna, Progres Lomba, Jadwal & Kartu Peserta
├── static/                  # Aset Frontend
│   ├── css/style.css        # Desain Soft Pastel Lavender/Sky Blue & Responsive Bottom Nav
│   └── js/app.js            # Interaksi pencarian, filter kategori, bagan & modal
└── requirements.txt         # Daftar dependensi Python ringan
```

---

## 2. Fitur Utama yang Tersedia

1. **Tiga Event Utama Sekolah**: *Bulan Bahasa*, *PORAK*, dan *17 Agustus* lengkap dengan ilustrasi berbeda sesuai kategori.
2. **Explore & Rekomendasi Lomba**: Pencarian instan dan filter pill kategori berwarna pastel.
3. **Mandatory Juknis View**: Peserta wajib membuka dan membaca persyaratan/juknis sebelum formulir pendaftaran terbuka.
4. **Single Registration per Event**: 1 siswa hanya diperbolehkan mendaftar 1 cabang lomba pada setiap event utama.
5. **Dukungan Lomba Individu & Kelompok (Tim)**: Validasi otomatis nama kelompok dan jumlah minimal anggota tim.
6. **Auto-Login & Kartu Peserta Digital**: Setelah mendaftar, peserta langsung masuk ke Dashboard Pengguna dan memperoleh Kartu Peserta ber-QR Code.
7. **Bagan Pertandingan Interaktif**: Mendukung *Shuffle* (acak otomatis), *BYE* otomatis, pemajuan pemenang tiap babak, hingga penentuan Juara Utama.
8. **Ruang Kontrol Panitia & Ekspor Excel (`.xlsx`)**:
   - Login Panitia: Username `panitia` | Password `panitia` (atau `lombaku2026`).
   - Kelola buka/tutup event, batas jadwal otomatis (*Schedule-Based Lock*), tambah cabang lomba, ubah juknis, tambah akun panitia, dan unduh rekap Excel (`.xlsx`).

---

## 3. Cara Instalasi & Menjalankan Aplikasi

### Prasyarat
- **Python 3.9+** sudah terpasang di komputer Anda (modul `sqlite3` sudah bawaan di dalam Python).

### Langkah Menjalankan (Windows PowerShell / CMD)
1. Buka terminal pada folder proyek, lalu buat atau aktifkan *virtual environment* (opsional namun disarankan):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Pasang paket pendukung ringan (`Flask` untuk web server dan `openpyxl` untuk styling laporan Excel):
   ```powershell
   pip install -r requirements.txt
   ```
3. Jalankan server aplikasi:
   ```powershell
   python app.py
   ```
   *(Atau klik dua kali file `jalankanserver.bat` / `start-lombaku.bat`)*.
4. Buka browser dan kunjungi:
   - **Beranda & Explore**: `http://127.0.0.1:5000`
   - **Halaman Event & Daftar**: `http://127.0.0.1:5000/daftar`
   - **Dashboard & Profil Pengguna**: `http://127.0.0.1:5000/peserta`
