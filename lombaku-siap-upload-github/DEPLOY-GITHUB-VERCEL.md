# Panduan Upload Lombaku ke GitHub & Deploy ke Vercel

Proyek **Lombaku** sudah dilengkapi seluruh file khusus agar siap langsung di-upload ke **GitHub** dan di-deploy ke **Vercel**:

- `vercel.json` — Konfigurasi Vercel Fluid Compute & routing Flask (`app.py`).
- `requirements.txt` — Daftar paket Python (`Flask`, `Werkzeug`, `openpyxl`) yang otomatis diinstall Vercel saat build.
- `.gitignore` — Mencegah file sementara (`__pycache__`, `venv`, `data/lombaku.db`, `.env`) ikut ter-upload ke GitHub.
- `.env.example` — Contoh Environment Variables untuk keamanan produksi.
- `push_github.bat` — Shortcut Windows untuk push ke GitHub lewat Git.

---

## Bagian 1 — Upload Proyek ke GitHub

### Cara A: Menggunakan `push_github.bat` (Tercepat jika Git sudah terpasang)

1. Login ke [GitHub.com](https://github.com) lalu klik **New Repository**.
2. Beri nama repository, misalnya `lombaku`, biarkan kosong (jangan centang *Add a README*), lalu klik **Create repository**.
3. Salin URL repository (contoh: `https://github.com/username-anda/lombaku.git`).
4. Klik dua kali file **`push_github.bat`** di folder proyek, lalu tempel URL repository saat diminta.

### Cara B: Menggunakan Terminal / PowerShell

```powershell
cd C:\Users\UserL\.gemini\antigravity\scratch\lombaku-liquid-glass
git init
git branch -M main
git add .
git commit -m "Initial commit Lombaku Liquid Glass"
git remote add origin https://github.com/USERNAME-ANDA/lombaku.git
git push -u origin main
```

### Cara C: Tanpa Git (Upload Langsung via Browser)
1. Buat repository baru di GitHub.
2. Klik **uploading an existing file**.
3. Tarik semua file & folder dari `lombaku-liquid-glass` **KECUALI** folder `data/`, `__pycache__/`, dan `venv/`.
4. Klik **Commit changes**.

---

## Bagian 2 — Deploy ke Vercel (Gratis & Otomatis)

1. Buka [vercel.com](https://vercel.com) dan login menggunakan akun **GitHub** Anda.
2. Klik **Add New... → Project**.
3. Pilih repository **`lombaku`** yang baru Anda upload, lalu klik **Import**.
4. Pada bagian **Framework Preset**, biarkan default (**Other** atau **Flask** jika terdeteksi otomatis — `vercel.json` sudah mengatur entrypoint `app.py`).
5. Buka bagian **Environment Variables** dan tambahkan 3 variabel berikut agar login panitia aman:
   - `SECRET_KEY` = isi teks acak panjang (misal: `lombaku-sman1-rahasia-2026-xyz`)
   - `ADMIN_USERNAME` = `admin` *(atau username pilihan Anda)*
   - `ADMIN_PASSWORD` = password panitia pilihan Anda
6. Klik **Deploy** dan tunggu ±1 menit hingga proses build Python selesai.
7. Setelah selesai, Anda akan langsung mendapatkan link publik seperti `https://lombaku-xxxx.vercel.app` yang bisa dibuka dari HP maupun laptop!

---

## Catatan Penting Tentang Database SQLite di Vercel

- Secara otomatis, `config.py` mendeteksi environment Vercel (`VERCEL=1`) dan menyimpan file SQLite sementara di `/tmp/lombaku_data/lombaku.db` (karena filesystem utama serverless Vercel bersifat *read-only*).
- **Sangat cocok untuk demo, presentasi, dan uji coba online**: seluruh fitur (event, pendaftaran, shuffle bracket, update skor, hingga download Excel `.xlsx`) langsung berjalan mulus di Vercel.
- **Perhatian untuk operasional lomba sekolah sungguhan**: karena folder `/tmp` di Vercel bersifat sementara (*ephemeral* dan dapat ter-reset saat serverless instance tidur/redeploy), untuk penyimpanan permanen jangka panjang di cloud Anda dapat:
  1. Menjalankan Lombaku di komputer/server lokal sekolah (SQLite di folder `data/lombaku.db` **100% permanen**), **atau**
  2. Menghubungkan database cloud permanen seperti **Turso (SQLite Cloud)** atau **Neon Postgres** melalui **Vercel Marketplace**.
