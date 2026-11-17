"""
====================================================================
FILE: database_lombaku.py
DESKRIPSI:
Modul pengelolaan database SQLite untuk aplikasi LombaKu.
Menggunakan modul bawaan Python `sqlite3` tanpa library database luar.

Daftar Tabel di Database (data/lombaku_sqlite.db):
1. tb_event       : Menyimpan 3 event utama sekolah (Bulan Bahasa, PORAK, 17 Agustus).
2. tb_lomba       : Menyimpan cabang perlombaan, kuota, jadwal, PJ, aturan, & kriteria.
3. tb_pendaftaran : Menyimpan data siswa/tim yang mendaftar berdasarkan NIS/NISN.
4. tb_admin       : Menyimpan akun panitia/guru pembina.
====================================================================
"""

import os
import json
import sqlite3

# Menentukan lokasi penyimpanan file database SQLite
FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
FOLDER_DATA = os.path.join(FOLDER_PROYEK, "data")

if os.environ.get("VERCEL"):
    LOKASI_DB = "/tmp/lombaku_sqlite.db"
else:
    os.makedirs(FOLDER_DATA, exist_ok=True)
    LOKASI_DB = os.path.join(FOLDER_DATA, "lombaku_sqlite.db")


def buka_koneksi():
    """
    Membuka koneksi ke database SQLite dan mengubah hasil baris (Row)
    agar bisa diakses menggunakan nama kolom seperti dictionary.
    """
    koneksi = sqlite3.connect(LOKASI_DB, check_same_thread=False)
    koneksi.row_factory = sqlite3.Row
    koneksi.execute("PRAGMA foreign_keys = ON;")
    return koneksi


def inisialisasi_database():
    """
    Fungsi ini dijalankan otomatis saat server Python menyala.
    Berfungsi membuat tabel-tabel jika belum ada, lalu mengisi data awal (seed).
    """
    koneksi = buka_koneksi()
    try:
        kursor = koneksi.cursor()

        # 1. Buat tabel tb_event
        kursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_event (
                id_event TEXT PRIMARY KEY,
                nama_event TEXT NOT NULL,
                slogan TEXT DEFAULT '',
                deskripsi TEXT DEFAULT '',
                lokasi_utama TEXT DEFAULT '',
                tema_warna TEXT DEFAULT 'cyan',
                mode_status TEXT NOT NULL DEFAULT 'auto',
                waktu_buka TEXT DEFAULT '',
                waktu_tutup TEXT DEFAULT '',
                tanggal_acara TEXT DEFAULT '',
                urutan INTEGER NOT NULL DEFAULT 0
            );
        """)

        # 2. Buat tabel tb_lomba
        kursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_lomba (
                id_lomba TEXT PRIMARY KEY,
                id_event TEXT NOT NULL,
                nama_lomba TEXT NOT NULL,
                kategori TEXT NOT NULL DEFAULT 'Individu',
                minimal_anggota INTEGER NOT NULL DEFAULT 1,
                kuota INTEGER NOT NULL DEFAULT 16,
                jadwal_tanding TEXT DEFAULT '',
                lokasi_lomba TEXT DEFAULT '',
                penanggung_jawab TEXT DEFAULT '',
                ringkasan TEXT DEFAULT '',
                aktif INTEGER NOT NULL DEFAULT 1,
                aturan_json TEXT NOT NULL DEFAULT '[]',
                kriteria_json TEXT NOT NULL DEFAULT '[]',
                perlengkapan TEXT DEFAULT '',
                catatan_panitia TEXT DEFAULT '',
                bagan_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (id_event) REFERENCES tb_event(id_event) ON DELETE CASCADE
            );
        """)

        # 3. Buat tabel tb_pendaftaran
        kursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_pendaftaran (
                kode_tiket TEXT PRIMARY KEY,
                id_event TEXT NOT NULL,
                id_lomba TEXT NOT NULL,
                nama_siswa TEXT NOT NULL,
                nis TEXT NOT NULL,
                kelas TEXT NOT NULL,
                no_wa TEXT NOT NULL,
                nama_tim TEXT DEFAULT '',
                anggota_tim_json TEXT NOT NULL DEFAULT '[]',
                sudah_baca_juknis INTEGER NOT NULL DEFAULT 1,
                waktu_daftar TEXT NOT NULL,
                FOREIGN KEY (id_event) REFERENCES tb_event(id_event) ON DELETE CASCADE,
                FOREIGN KEY (id_lomba) REFERENCES tb_lomba(id_lomba) ON DELETE CASCADE
            );
        """)

        # 4. Buat tabel tb_admin (Panitia)
        kursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_admin (
                username TEXT PRIMARY KEY,
                nama_lengkap TEXT NOT NULL,
                jabatan TEXT NOT NULL DEFAULT 'Panitia OSIS',
                password TEXT NOT NULL
            );
        """)

        koneksi.commit()

        # Cek apakah tabel tb_event masih kosong
        kursor.execute("SELECT COUNT(*) AS jumlah FROM tb_event;")
        if kursor.fetchone()["jumlah"] == 0:
            isi_data_awal_lombaku(koneksi)

        # Pastikan akun panitia default selalu ada
        kursor.execute("SELECT COUNT(*) AS jumlah FROM tb_admin WHERE username = 'panitia';")
        if kursor.fetchone()["jumlah"] == 0:
            kursor.execute(
                "INSERT INTO tb_admin (username, nama_lengkap, jabatan, password) VALUES (?, ?, ?, ?);",
                ("panitia", "Koordinator Panitia LombaKu", "Pembina OSIS", "lombaku2026")
            )
            koneksi.commit()

    finally:
        koneksi.close()


def isi_data_awal_lombaku(koneksi):
    """
    Mengisi data awal 3 Event Utama Sekolah, 9 Cabang Perlombaan lengkap dengan
    kriteria penilaian, perlengkapan, PJ, serta contoh pendaftar awal.
    """
    kursor = koneksi.cursor()

    daftar_event = [
        (
            "bulan-bahasa",
            "Bulan Bahasa",
            "Ekspresi Sastra, Literasi & Kreativitas Berbahasa",
            "Ajang tahunan mengasah bakat literasi, seni bertutur, penulisan kreatif, dan penguasaan bahasa bagi seluruh siswa.",
            "Aula Utama & Perpustakaan Sekolah",
            "cyan",
            "auto",
            "2026-11-01T07:00",
            "2026-12-20T16:00",
            "2026-12-22T08:00",
            1
        ),
        (
            "porak",
            "PORAK",
            "Pekan Olahraga Antarkelas — Junjung Sportivitas!",
            "Kompetisi olahraga, ketangkasan, dan e-sport antarkelas untuk mempererat solidaritas serta semangat juara.",
            "Lapangan Olahraga & GOR Sekolah",
            "violet",
            "available",
            "2026-11-01T07:00",
            "2026-12-24T16:00",
            "2026-12-26T07:30",
            2
        ),
        (
            "17-agustus",
            "17 Agustus",
            "Semarak Kemerdekaan RI — Merdeka Berprestasi!",
            "Rangkaian lomba tradisional dan kekompakan kelas dalam rangka memeriahkan HUT Kemerdekaan Republik Indonesia.",
            "Lapangan Upacara & Halaman Tengah",
            "pink",
            "available",
            "2026-11-01T07:00",
            "2026-12-28T16:00",
            "2026-12-29T07:30",
            3
        ),
    ]

    kursor.executemany("""
        INSERT INTO tb_event
        (id_event, nama_event, slogan, deskripsi, lokasi_utama, tema_warna, mode_status, waktu_buka, waktu_tutup, tanggal_acara, urutan)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, daftar_event)

    # Data cabang lomba lengkap dengan kriteria bobot & perlengkapan
    daftar_lomba = [
        (
            "bb-baca-puisi",
            "bulan-bahasa",
            "Baca Puisi Nusantara",
            "Individu",
            1,
            16,
            "Jumat, 08.30 – 11.30 WIB",
            "Aula Utama Lt. 2",
            "Bu Ratna & Sekbid Sastra",
            "Membacakan puisi wajib dan puisi pilihan bertema perjuangan & lingkungan.",
            1,
            json.dumps([
                "Peserta adalah siswa aktif kelas X, XI, atau XII.",
                "Membawakan 1 puisi wajib ('Aku' - Chairil Anwar) dan 1 puisi pilihan panitia.",
                "Durasi penampilan maksimal 6 menit di atas panggung.",
                "Mengenakan seragam sekolah rapi atau busana bernuansa sastra."
            ]),
            json.dumps([
                {"aspek": "Penghayatan & Ekspresi", "bobot": 35},
                {"aspek": "Intonasi, Vokal & Artikulasi", "bobot": 30},
                {"aspek": "Irama & Dinamika Suara", "bobot": 20},
                {"aspek": "Penguasaan Panggung", "bobot": 15}
            ]),
            "Naskah puisi cetak (disiapkan panitia atau dibawa masing-masing).",
            "Hadir 15 menit sebelum acara untuk pengambilan nomor urut tampil.",
            json.dumps({
                "rounds": [
                    {
                        "name": "Semifinal",
                        "matches": [
                            {"id": "m1", "p1": "Alya Putri (XI IPA 1)", "p2": "Bima Sakti (X-3)", "winner": "Alya Putri (XI IPA 1)"},
                            {"id": "m2", "p1": "Citra Kirana (XII IPS 2)", "p2": "Daffa Maulana (XI IPS 1)", "winner": ""}
                        ]
                    },
                    {
                        "name": "Final",
                        "matches": [
                            {"id": "m3", "p1": "Alya Putri (XI IPA 1)", "p2": "Menunggu Pemenang M2", "winner": ""}
                        ]
                    }
                ],
                "champion": ""
            })
        ),
        (
            "bb-story-telling",
            "bulan-bahasa",
            "Story Telling (English)",
            "Individu",
            1,
            16,
            "Jumat, 13.00 – 15.30 WIB",
            "Ruang Multimedia / Lab Bahasa",
            "Mr. Bagus & English Club",
            "Bercerita cerita rakyat Nusantara dalam bahasa Inggris dengan properti kreatif.",
            1,
            json.dumps([
                "Penampilan disampaikan dalam Bahasa Inggris tanpa membaca teks penuh.",
                "Tema cerita: Indonesian Folklore / Cerita Rakyat Nusantara.",
                "Durasi tampil 4 sampai 6 menit.",
                "Diperbolehkan membawa maksimal 3 properti pendukung."
            ]),
            json.dumps([
                {"aspek": "Pronunciation & Fluency", "bobot": 35},
                {"aspek": "Story Delivery & Character Voice", "bobot": 30},
                {"aspek": "Grammar & Vocabulary", "bobot": 20},
                {"aspek": "Creativity & Props", "bobot": 15}
            ]),
            "Properti cerita sederhana & file audio latar (jika ada).",
            "Naskah cerita dikumpulkan ke meja panitia saat registrasi ulang.",
            json.dumps({"rounds": [], "champion": ""})
        ),
        (
            "bb-cipta-cerpen",
            "bulan-bahasa",
            "Cipta Cerpen Sekolah",
            "Individu",
            1,
            24,
            "Sabtu, 08.00 – 10.30 WIB",
            "Perpustakaan Sekolah",
            "Pak Hendra & Tim Literasi",
            "Menulis cerita pendek orisinal secara langsung bertema Jejak Langkah di Sekolah.",
            1,
            json.dumps([
                "Karya ditulis langsung di ruang perpustakaan selama 120 menit.",
                "Panjang cerpen 750–1.500 kata sesuai kaidah EYD/PUEBI.",
                "Karya wajib orisinal dan tidak menggunakan bantuan AI/internet."
            ]),
            json.dumps([
                {"aspek": "Orisinalitas Ide & Kesesuaian Tema", "bobot": 35},
                {"aspek": "Alur, Konflik & Penokohan", "bobot": 35},
                {"aspek": "Gaya Bahasa & Kerapian Ejaan", "bobot": 30}
            ]),
            "Pulpen hitam/biru dan papan jalan. Kertas disediakan panitia.",
            "Tiga karya terbaik akan diterbitkan di Buletin Sekolah.",
            json.dumps({"rounds": [], "champion": ""})
        ),
        (
            "porak-futsal",
            "porak",
            "Futsal Antarkelas",
            "Tim / Kelas",
            5,
            16,
            "Senin–Rabu, 08.00 – 14.00 WIB",
            "Lapangan Futsal Sekolah",
            "Pak Dimas (PJOK) & Ekskul Futsal",
            "Turnamen futsal sistem gugur antar tim perwakilan kelas (minimal 5 pemain).",
            1,
            json.dumps([
                "Setiap tim minimal terdiri dari 5 pemain inti (maksimal 8 dengan cadangan) dari kelas yang sama.",
                "Pendaftaran dilakukan oleh kapten kelas dengan mencantumkan nama tim dan anggota.",
                "Pertandingan berlangsung 2 x 10 menit waktu kotor dengan sistem gugur.",
                "Wajib mengenakan sepatu futsal, kaos tim bernomor, dan shin guard."
            ]),
            json.dumps([
                {"aspek": "Kemenangan Skor Pertandingan", "bobot": 70},
                {"aspek": "Kekompakan & Sportivitas (Fair Play)", "bobot": 30}
            ]),
            "Sepatu futsal, kaos seragam kelas, pelindung tulang kering (shin guard).",
            "Tim wajib berada di tepi lapangan 10 menit sebelum jadwal kick-off.",
            json.dumps({
                "rounds": [
                    {
                        "name": "Semifinal",
                        "matches": [
                            {"id": "pf1", "p1": "Garuda XII IPA 1 (XII IPA 1)", "p2": "Spartan XI IPS 2 (XI IPS 2)", "winner": "Garuda XII IPA 1 (XII IPA 1)"},
                            {"id": "pf2", "p1": "Rajawali X-2 (X Merdeka 2)", "p2": "Phoenix XI IPA 3 (XI IPA 3)", "winner": ""}
                        ]
                    },
                    {
                        "name": "Final",
                        "matches": [
                            {"id": "pf3", "p1": "Garuda XII IPA 1 (XII IPA 1)", "p2": "Menunggu Pemenang M2", "winner": ""}
                        ]
                    }
                ],
                "champion": ""
            })
        ),
        (
            "porak-badminton",
            "porak",
            "Badminton Tunggal",
            "Individu",
            1,
            16,
            "Selasa–Kamis, 08.30 – 13.00 WIB",
            "GOR Bulutangkis Sekolah",
            "Bu Nina & Ekskul Badminton",
            "Turnamen bulutangkis tunggal sistem gugur rally point 21.",
            1,
            json.dumps([
                "Menggunakan sistem rally point 21 sesuai peraturan PBSI.",
                "Shuttlecock disediakan panitia maksimal 2 buah per pertandingan.",
                "Peserta membawa raket masing-masing dan wajib bersepatu olahraga."
            ]),
            json.dumps([
                {"aspek": "Kemenangan Set Pertandingan (Rally Point 21)", "bobot": 80},
                {"aspek": "Ketepatan Kehadiran & Etika Bertanding", "bobot": 20}
            ]),
            "Raket bulutangkis pribadi, sepatu olahraga non-marking, handuk kecil.",
            "Panggilan pertandingan dilakukan maksimal 3 kali sebelum dinyatakan WO.",
            json.dumps({"rounds": [], "champion": ""})
        ),
        (
            "porak-mlbb",
            "porak",
            "E-Sport Mobile Legends",
            "Tim / Kelas",
            5,
            16,
            "Kamis, 10.00 – 15.00 WIB",
            "Aula Utama (Area Turnamen)",
            "OSIS Sekbid TIK",
            "Turnamen 5v5 antar tim kelas dengan mode Custom Draft Pick.",
            1,
            json.dumps([
                "1 tim wajib beranggotakan minimal 5 pemain dari kelas yang sama.",
                "Menggunakan mode Custom Draft Pick di bawah pengawasan wasit panitia.",
                "Dilarang melakukan chat all bernada provokasi atau menggunakan script/cheat."
            ]),
            json.dumps([
                {"aspek": "Kemenangan Match (menghancurkan Base lawan)", "bobot": 85},
                {"aspek": "Ketepatan masuk Lobby Room", "bobot": 15}
            ]),
            "Smartphone pribadi baterai penuh, kuota data pribadi, dan headset.",
            "Babak penyisihan Best of 1 (BO1), Babak Final Best of 3 (BO3).",
            json.dumps({"rounds": [], "champion": ""})
        ),
        (
            "agustus-tarik-tambang",
            "17-agustus",
            "Tarik Tambang Kelas",
            "Tim / Kelas",
            6,
            16,
            "17 Agustus, 09.00 – 11.30 WIB",
            "Lapangan Utama Sekolah",
            "Pak Agus & Paskibra",
            "Lomba adu kekuatan dan strategi kekompakan minimal 6 orang per tim kelas.",
            1,
            json.dumps([
                "Setiap tim wajib terdiri dari minimal 6 siswa dari kelas yang sama.",
                "Dilarang melilitkan tali tambang ke tangan atau pinggang demi keamanan.",
                "Seluruh anggota tim wajib memakai sepatu olahraga tertutup.",
                "Format Best of 3 tarikan dengan pertukaran posisi lapangan."
            ]),
            json.dumps([
                {"aspek": "Keberhasilan menarik pita batas melewati garis tengah", "bobot": 80},
                {"aspek": "Kepatuhan aba-aba wasit & keselamatan", "bobot": 20}
            ]),
            "Sepatu olahraga beralas karet dan kaos olahraga kelas.",
            "Keputusan wasit garis bersifat mutlak.",
            json.dumps({"rounds": [], "champion": ""})
        ),
        (
            "agustus-balap-karung",
            "17-agustus",
            "Balap Karung Estafet",
            "Tim / Kelas",
            4,
            16,
            "17 Agustus, 11.30 – 13.00 WIB",
            "Lapangan Upacara",
            "OSIS Sekbid Olahraga",
            "Lomba balap karung helm beranting 4 siswa per tim kelas.",
            1,
            json.dumps([
                "1 tim terdiri dari minimal 4 pelari estafet dari kelas yang sama.",
                "Setiap pelari wajib mengenakan helm pengaman yang disiapkan panitia.",
                "Pergantian pelari dilakukan di zona garis estafet."
            ]),
            json.dumps([
                {"aspek": "Kecepatan waktu menyentuh garis finish", "bobot": 80},
                {"aspek": "Ketertiban pergantian karung & helm", "bobot": 20}
            ]),
            "Pakaian olahraga lengkap dan sepatu kets.",
            "Karung goni dan helm disediakan oleh panitia.",
            json.dumps({"rounds": [], "champion": ""})
        ),
        (
            "agustus-cerdas-cermat",
            "17-agustus",
            "Cerdas Cermat Kemerdekaan",
            "Tim / Kelas",
            3,
            16,
            "17 Agustus, 13.00 – 15.00 WIB",
            "Aula Sekolah",
            "Guru Sejarah & PPKn",
            "Kuis cepat tepat wawasan kebangsaan & sejarah kemerdekaan (3 siswa/tim).",
            1,
            json.dumps([
                "Setiap tim terdiri dari minimal 3 siswa perwakilan kelas.",
                "Terdiri dari Babak Soal Wajib, Soal Lemparan, dan Soal Rebutan.",
                "Dilarang membawa perangkat komunikasi ke meja peserta."
            ]),
            json.dumps([
                {"aspek": "Akumulasi Skor Babak Wajib & Lemparan", "bobot": 50},
                {"aspek": "Ketepatan & Kecepatan Babak Rebutan", "bobot": 50}
            ]),
            "Alat tulis disediakan oleh panitia di meja masing-masing regu.",
            "Materi meliputi Sejarah Kemerdekaan RI, Pancasila, dan UUD 1945.",
            json.dumps({"rounds": [], "champion": ""})
        ),
    ]

    kursor.executemany("""
        INSERT INTO tb_lomba
        (id_lomba, id_event, nama_lomba, kategori, minimal_anggota, kuota, jadwal_tanding,
         lokasi_lomba, penanggung_jawab, ringkasan, aktif, aturan_json, kriteria_json,
         perlengkapan, catatan_panitia, bagan_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, daftar_lomba)

    # Contoh pendaftar awal berbasis NIS agar aplikasi langsung hidup
    pendaftar_awal = [
        (
            "LMK-BB-001",
            "bulan-bahasa",
            "bb-baca-puisi",
            "Alya Putri Ramadhani",
            "2026101",
            "XI IPA 1",
            "081234560101",
            "",
            "[]",
            1,
            "2026-11-16 09:15:00"
        ),
        (
            "LMK-BB-002",
            "bulan-bahasa",
            "bb-baca-puisi",
            "Bima Sakti Nugroho",
            "2026102",
            "X-3",
            "081234560102",
            "",
            "[]",
            1,
            "2026-11-16 10:20:00"
        ),
        (
            "LMK-PR-001",
            "porak",
            "porak-futsal",
            "Raka Pratama",
            "2026201",
            "XII IPA 1",
            "081345670201",
            "Garuda XII IPA 1",
            json.dumps(["Dimas", "Aldi", "Rizky", "Rehan"]),
            1,
            "2026-11-16 11:05:00"
        ),
        (
            "LMK-PR-002",
            "porak",
            "porak-futsal",
            "Kevin Wijaya",
            "2026202",
            "XI IPS 2",
            "081345670202",
            "Spartan XI IPS 2",
            json.dumps(["Fikri", "Galih", "Hendra", "Iqbal"]),
            1,
            "2026-11-16 13:40:00"
        ),
    ]

    kursor.executemany("""
        INSERT INTO tb_pendaftaran
        (kode_tiket, id_event, id_lomba, nama_siswa, nis, kelas, no_wa, nama_tim, anggota_tim_json, sudah_baca_juknis, waktu_daftar)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, pendaftar_awal)

    koneksi.commit()
