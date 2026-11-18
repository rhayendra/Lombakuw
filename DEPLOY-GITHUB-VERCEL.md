# Panduan Deploy Lombaku ke GitHub + Vercel + Supabase (Permanen!)

Aplikasi **Lombaku** mendukung **Dual-Engine Database** secara otomatis:
- **Di Komputer Lokal** (tanpa `DATABASE_URL`): otomatis memakai **SQLite** (`data/lombaku.db`).
- **Di Vercel dengan Supabase** (ketika `DATABASE_URL` diisi): otomatis memakai **PostgreSQL Supabase** yang **100% permanen**!

Seluruh tabel (`admins`, `settings`, `events`, `competitions`, `registrations`, `team_members`, `matches`) dan data demo awal akan **dibuat secara otomatis** oleh Python saat aplikasi pertama kali diakses di Vercel.

---

## Langkah 1 — Buat Database Gratis di Supabase

1. Buka [supabase.com](https://supabase.com) lalu login (bisa pakai akun GitHub).
2. Klik **New Project**:
   - **Name**: `lombaku`
   - **Database Password**: buat password yang kuat dan **simpan baik-baik** *(hindari karakter simbol rumit seperti `@` atau `#` agar URL tidak perlu di-encode, cukup huruf + angka)*.
   - **Region**: pilih **Southeast Asia (Singapore)** agar cepat diakses dari Indonesia.
3. Klik **Create new project** dan tunggu ±1 menit hingga status aktif.
4. Setelah proyek siap, klik tombol **Connect** di bagian atas dashboard Supabase:
   - Pilih tab **Connection String** → **URI**.
   - **PENTING:** Pilih mode **Transaction Pooler** (port `6543`) atau **Session Pooler** (port `5432`) agar kompatibel dengan IPv4 serverless Vercel!
   - Salin URI tersebut, contohnya:
     ```text
     postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
     ```
   - Ganti `[YOUR-PASSWORD]` dengan password database yang Anda buat di langkah 2.

*(Opsional)* Jika ingin melihat atau menjalankan skema tabel secara manual di **Supabase → SQL Editor**, Anda bisa menyalin isi file `database/supabase_schema.sql`. Namun ini **tidak wajib** karena Lombaku sudah otomatis membuatnya!

---

## Langkah 2 — Upload Proyek ke GitHub

Gunakan folder bersih **`lombaku-siap-upload-github`** yang sudah dipisahkan dari file sementara:

1. Login ke [github.com](https://github.com) → klik **New Repository** → beri nama `lombaku` → klik **Create repository**.
2. Klik **uploading an existing file**.
3. Buka folder `C:\Users\UserL\.gemini\antigravity\scratch\lombaku-siap-upload-github`, tekan **`Ctrl + A`** (pilih semua isi di dalamnya), lalu **tarik (*drag-and-drop*)** ke halaman upload GitHub.
4. Pastikan `app.py`, `vercel.json`, `requirements.txt` ada di halaman utama repository, lalu klik **Commit changes**.

*(Atau jika memakai Git CLI, cukup klik dua kali `push_github.bat` di folder proyek utama).*

---

## Langkah 3 — Deploy ke Vercel & Hubungkan Supabase

1. Buka [vercel.com](https://vercel.com) dan login menggunakan akun **GitHub** Anda.
2. Klik **Add New... → Project**, lalu klik **Import** pada repository **`lombaku`**.
3. Buka bagian **Environment Variables** dan tambahkan **4 variabel berikut**:

| Name | Value |
| --- | --- |
| `DATABASE_URL` | Tempel URI **Transaction Pooler** dari Supabase *(sudah diganti password aslinya)* |
| `SECRET_KEY` | Teks acak panjang rahasia (contoh: `lombaku-sman1-rahasia-2026-aman`) |
| `ADMIN_USERNAME` | `admin` *(atau username panitia pilihan Anda)* |
| `ADMIN_PASSWORD` | Password login panitia yang Anda inginkan |

4. Klik **Deploy** dan tunggu ±1 menit hingga proses build Python (`Flask`, `Werkzeug`, `openpyxl`, `psycopg2-binary`) selesai.
5. Klik link domain Vercel Anda (`https://lombaku-xxxx.vercel.app`)!
   - Saat dibuka pertama kali, Python otomatis membuat seluruh tabel di Supabase dan mengisi 3 event default (*Bulan Bahasa*, *PORAK*, *17 Agustus*).
   - Anda bisa langsung mengecek tabel & data pendaftar yang masuk secara real-time di **Supabase Dashboard → Table Editor**!

---

## Tips Troubleshooting Cepat

- **Error `could not translate host name` atau IPv6 di Vercel?**
  Pastikan Anda memakai URL **Pooler** (`...pooler.supabase.com:6543/postgres`), **bukan** Direct Connection (`db.xxxx.supabase.co:5432`).
- **Error `password authentication failed`?**
  Pastikan tanda kurung siku `[YOUR-PASSWORD]` sudah dihapus dan diganti dengan password database Supabase Anda yang benar.
- **Ingin cek apakah sudah tersambung ke Supabase?**
  Buka **Supabase → Table Editor**: jika tabel `events`, `competitions`, `registrations`, dan `matches` sudah muncul otomatis beserta datanya, berarti koneksi Vercel ↔ Supabase sudah 100% berhasil!
