"""
Pengisian data demo awal (seeding) untuk Lombaku.
Membuat 3 event utama (Bulan Bahasa, PORAK, 17 Agustus), cabang lomba individu & tim,
peserta demo, bracket aktif, pertandingan LIVE, dan contoh pemenang.
"""
from datetime import datetime, timedelta
from config import Config
from database.db import get_standalone_db
from services.auth import hash_password
from services.bracket import build_bracket, update_match


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def seed_demo_data(force_reset: bool = False):
    """
    Mengisi database dengan data demo yang kaya untuk presentasi.
    Jika force_reset=False, seeding hanya berjalan jika tabel events masih kosong.
    """
    conn = get_standalone_db()
    try:
        # Pastikan akun admin default selalu tersedia
        admin_exists = conn.execute(
            "SELECT id FROM admins WHERE username = ?", (Config.DEFAULT_ADMIN_USERNAME,)
        ).fetchone()
        if not admin_exists:
            conn.execute(
                "INSERT INTO admins (username, full_name, password_hash) VALUES (?, ?, ?)",
                (
                    Config.DEFAULT_ADMIN_USERNAME,
                    "Panitia Inti OSIS",
                    hash_password(Config.DEFAULT_ADMIN_PASSWORD),
                ),
            )

        # Pengaturan default
        default_settings = {
            "school_name": "SMA Negeri Nusantara 01",
            "school_tagline": "Pusat Digital Perlombaan & Turnamen Sekolah",
            "committee_contact": "Sekretariat OSIS Lt. 2 · WA Panitia: 0812-8890-2026 · osis@smanusantara01.sch.id",
            "announcement": "Bulan Bahasa & PORAK sedang dibuka! Baca Juknis pada setiap cabang lomba sebelum mendaftar.",
        }
        for k, v in default_settings.items():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING", (k, v)
            )

        if not force_reset:
            ev_count = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"]
            if ev_count > 0:
                conn.commit()
                return

        # Jika force_reset, bersihkan data operasional (tetap pertahankan akun admin)
        conn.execute("DELETE FROM matches")
        conn.execute("DELETE FROM team_members")
        conn.execute("DELETE FROM registrations")
        conn.execute("DELETE FROM competitions")
        conn.execute("DELETE FROM events")

        now = datetime.now()

        # ------------------------------------------------------------------
        # 1. TIGA EVENT UTAMA DEFAULT
        # ------------------------------------------------------------------
        events_data = [
            {
                "slug": "bulan-bahasa",
                "name": "Bulan Bahasa",
                "subtitle": "Festival Literasi, Retorika & Sastra Sekolah",
                "description": (
                    "Ajang apresiasi bahasa, sastra, dan seni berkomunikasi bagi seluruh siswa. "
                    "Menghadirkan kompetisi pidato, debat bahasa Inggris, dan cipta baca puisi "
                    "dengan penilaian juri profesional serta transparansi jadwal digital."
                ),
                "theme_accent": "cyan",
                "icon_type": "quill",
                "event_date": _iso(now + timedelta(days=9, hours=3)),
                "registration_open": _iso(now - timedelta(days=5)),
                "registration_deadline": _iso(now + timedelta(days=7)),
                "schedule_text": (
                    "Hari 1 · 08:00 WIB — Pembukaan & Technical Meeting di Aula Utama\n"
                    "Hari 1 · 09:30 WIB — Babak Penyisihan Pidato & Cipta Puisi\n"
                    "Hari 2 · 08:30 WIB — Semifinal & Final Debat Bahasa Inggris\n"
                    "Hari 2 · 14:00 WIB — Pengumuman Juara & Penyerahan Piala"
                ),
                "juknis": (
                    "1. Peserta merupakan siswa aktif SMA Negeri Nusantara 01.\n"
                    "2. Setiap siswa hanya diperbolehkan mendaftar pada 1 cabang lomba dalam event Bulan Bahasa.\n"
                    "3. Peserta wajib hadir 15 menit sebelum jadwal tampil di ruang lomba.\n"
                    "4. Keputusan dewan juri bersifat mutlak dan tidak dapat diganggu gugat.\n"
                    "5. Karya puisi dan naskah pidato harus orisinal serta tidak mengandung unsur SARA."
                ),
                "committee_info": "Koordinator: Nadya Putri (XI IPA 1) · Ruang OSIS · 0812-3401-1122",
                "status": "OPEN",
                "is_featured": 1,
                "sort_order": 1,
            },
            {
                "slug": "porak",
                "name": "PORAK",
                "subtitle": "Pekan Olahraga & E-Sports Antar Kelas",
                "description": (
                    "Turnamen olahraga bergengsi antar kelas untuk menumbuhkan sportivitas, kerja sama tim, "
                    "dan semangat kompetitif yang sehat. Dilengkapi bracket turnamen langsung yang bisa dipantau "
                    "secara real-time dari HP maupun laptop."
                ),
                "theme_accent": "blue",
                "icon_type": "flame",
                "event_date": _iso(now + timedelta(days=5, hours=2)),
                "registration_open": _iso(now - timedelta(days=7)),
                "registration_deadline": _iso(now + timedelta(days=4)),
                "schedule_text": (
                    "Hari 1 · 07:30 WIB — Apel Pembukaan PORAK di Lapangan Utama\n"
                    "Hari 1 · 08:30 WIB — Penyisihan Futsal Putra & Badminton Tunggal\n"
                    "Hari 2 · 09:00 WIB — Semifinal Futsal & Babak Utama Mobile Legends\n"
                    "Hari 3 · 13:00 WIB — Partai Final & Penganugerahan Juara Umum"
                ),
                "juknis": (
                    "1. Setiap kelas berhak mengirimkan maksimal 1 tim per cabang beregu.\n"
                    "2. Satu siswa hanya dapat mengikuti satu cabang lomba selama rangkaian PORAK.\n"
                    "3. Peserta cabang olahraga wajib mengenakan pakaian olahraga dan sepatu yang sesuai.\n"
                    "4. Keterlambatan lebih dari 10 menit dari jadwal pertandingan dinyatakan WO (Walk Out).\n"
                    "5. Menjunjung tinggi fair play; pelanggaran berat berujung diskualifikasi."
                ),
                "committee_info": "Koordinator: Bagas Pratama (XII IPS 2) · Seksi Olahraga OSIS · 0813-7788-2026",
                "status": "ONGOING",
                "is_featured": 0,
                "sort_order": 2,
            },
            {
                "slug": "17-agustus",
                "name": "17 Agustus",
                "subtitle": "Semarak Hari Kemerdekaan Republik Indonesia",
                "description": (
                    "Perayaan HUT Kemerdekaan RI penuh keceriaan dengan perlombaan tradisional dan wawasan "
                    "kebangsaan. Mempererat kebersamaan antar kelas melalui semangat gotong royong dan kreativitas."
                ),
                "theme_accent": "amber",
                "icon_type": "star",
                "event_date": _iso(now + timedelta(days=38, hours=1)),
                "registration_open": _iso(now + timedelta(days=10)),
                "registration_deadline": _iso(now + timedelta(days=34)),
                "schedule_text": (
                    "07:00 WIB — Upacara Pengibaran Bendera Merah Putih\n"
                    "09:00 WIB — Penyisihan Tarik Tambang & Balap Karung Estafet\n"
                    "11:00 WIB — Cerdas Cermat Kebangsaan di Aula\n"
                    "14:30 WIB — Final Tarik Tambang & Pembagian Hadiah Kemerdekaan"
                ),
                "juknis": (
                    "1. Terbuka untuk seluruh kelas X, XI, dan XII.\n"
                    "2. Setiap siswa hanya boleh mendaftar pada 1 cabang lomba di event 17 Agustus.\n"
                    "3. Pakaian bernuansa merah putih atau seragam olahraga sekolah.\n"
                    "4. Menjaga kebersihan area lapangan selama perlombaan berlangsung."
                ),
                "committee_info": "Koordinator: Raka Mahendra (XI IPS 1) · Panitia HUT RI · 0857-9001-1708",
                "status": "CLOSED",
                "is_featured": 0,
                "sort_order": 3,
            },
        ]

        event_ids = {}
        for ev in events_data:
            cur = conn.execute(
                """
                INSERT INTO events
                    (slug, name, subtitle, description, theme_accent, icon_type,
                     event_date, registration_open, registration_deadline,
                     schedule_text, juknis, committee_info, status, is_featured, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev["slug"], ev["name"], ev["subtitle"], ev["description"],
                    ev["theme_accent"], ev["icon_type"], ev["event_date"],
                    ev["registration_open"], ev["registration_deadline"],
                    ev["schedule_text"], ev["juknis"], ev["committee_info"],
                    ev["status"], ev["is_featured"], ev["sort_order"],
                ),
            )
            event_ids[ev["slug"]] = cur.lastrowid

        # ------------------------------------------------------------------
        # 2. CABANG LOMBA
        # ------------------------------------------------------------------
        competitions_data = [
            # Bulan Bahasa
            {
                "key": "pidato",
                "event_id": event_ids["bulan-bahasa"],
                "name": "Pidato Bahasa Indonesia",
                "category": "Retorika",
                "description": "Kompetisi orasi bertema 'Generasi Digital Berbahasa Santun' dengan durasi tampil 5–7 menit.",
                "comp_type": "INDIVIDUAL",
                "min_members": 1,
                "max_members": 1,
                "same_class_required": 0,
                "max_slots": 16,
                "requirements": "Menyiapkan naskah pidato orisinal 2 rangkap saat technical meeting.",
                "juknis": (
                    "KISI-KISI & PENILAIAN PIDATO:\n"
                    "• Kesesuaian tema & kedalaman isi (35%)\n"
                    "• Intonasi, artikulasi, dan penguasaan bahasa baku (30%)\n"
                    "• Gestur, kontak mata, dan kepercayaan diri (20%)\n"
                    "• Ketepatan waktu 5–7 menit (15%)\n\n"
                    "ATURAN: Dilarang membaca teks secara penuh; diperbolehkan membawa kartu catatan kecil."
                ),
                "schedule_info": "Hari 1 · 09:30 WIB",
                "venue": "Aula Utama Lt. 1",
            },
            {
                "key": "debat",
                "event_id": event_ids["bulan-bahasa"],
                "name": "Debat Bahasa Inggris",
                "category": "Akademik",
                "description": "Format Asian Parliamentary Debate (3 pembicara per tim) dengan mosi aktual teknologi & pendidikan.",
                "comp_type": "TEAM",
                "min_members": 3,
                "max_members": 3,
                "same_class_required": 0,
                "max_slots": 16,
                "requirements": "Tim terdiri dari tepat 3 siswa (lintas kelas diperbolehkan).",
                "juknis": (
                    "KISI-KISI & ATURAN DEBAT:\n"
                    "• Format: Asian Parliamentary (Prime Minister, Deputy, Whip)\n"
                    "• Waktu case building: 15 menit tanpa akses internet\n"
                    "• Durasi pidato substansi: 5 menit + reply speech 3 menit\n"
                    "• Penilaian: Matter (40%), Manner (40%), Method (20%)"
                ),
                "schedule_info": "Hari 2 · 08:30 WIB",
                "venue": "Ruang Audio Visual",
            },
            {
                "key": "puisi",
                "event_id": event_ids["bulan-bahasa"],
                "name": "Cipta & Baca Puisi",
                "category": "Sastra",
                "description": "Menulis puisi secara langsung sesuai tema yang diumumkan panitia lalu membacakannya di atas panggung.",
                "comp_type": "INDIVIDUAL",
                "min_members": 1,
                "max_members": 1,
                "same_class_required": 0,
                "max_slots": 24,
                "requirements": "Membawa alat tulis sendiri; kertas disediakan panitia.",
                "juknis": (
                    "KISI-KISI CIPTA & BACA PUISI:\n"
                    "• Waktu penciptaan karya: 60 menit di tempat\n"
                    "• Pembacaan puisi maksimal 4 menit per peserta\n"
                    "• Penilaian: Diksi & estetika (40%), Penghayatan (35%), Vokal & ekspresi (25%)"
                ),
                "schedule_info": "Hari 1 · 10:30 WIB",
                "venue": "Perpustakaan Glass Hall",
            },
            # PORAK
            {
                "key": "futsal",
                "event_id": event_ids["porak"],
                "name": "Futsal Putra",
                "category": "Olahraga",
                "description": "Turnamen futsal sistem gugur antar kelas. 5 pemain inti + maksimal 2 pemain cadangan.",
                "comp_type": "TEAM",
                "min_members": 5,
                "max_members": 7,
                "same_class_required": 1,
                "max_slots": 16,
                "requirements": "Seluruh anggota wajib berasal dari kelas yang sama dan memakai sepatu futsal.",
                "juknis": (
                    "ATURAN FUTSAL PORAK:\n"
                    "• Durasi pertandingan: 2 x 10 menit (kotor), jeda istirahat 3 menit\n"
                    "• Jumlah anggota tim: minimal 5 orang, maksimal 7 orang dari kelas yang sama\n"
                    "• Jika skor imbang, langsung dilanjutkan adu penalti 3 penendang\n"
                    "• Kartu kuning = peringatan; 2 kartu kuning / kartu merah = absen 1 laga"
                ),
                "schedule_info": "Hari 1–3 · 08:30 WIB",
                "venue": "Lapangan Futsal Indoor",
            },
            {
                "key": "badminton",
                "event_id": event_ids["porak"],
                "name": "Badminton Tunggal",
                "category": "Olahraga",
                "description": "Pertandingan bulu tangkis tunggal putra/putri sistem gugur dengan format rally point 21.",
                "comp_type": "INDIVIDUAL",
                "min_members": 1,
                "max_members": 1,
                "same_class_required": 0,
                "max_slots": 16,
                "requirements": "Membawa raket pribadi; shuttlecock disediakan panitia.",
                "juknis": (
                    "ATURAN BADMINTON TUNGGAL:\n"
                    "• Sistem gugur best of 3 games (21 poin rally point)\n"
                    "• Deuce maksimal pada poin 30\n"
                    "• Wajib mengenakan sepatu non-marking di lapangan GOR"
                ),
                "schedule_info": "Hari 1–2 · 09:00 WIB",
                "venue": "GOR Serbaguna Sekolah",
            },
            {
                "key": "mlbb",
                "event_id": event_ids["porak"],
                "name": "E-Sports Mobile Legends",
                "category": "E-Sports",
                "description": "Kompetisi Mobile Legends 5v5 Draft Pick Mode antar skuad sekolah dengan layar tancap di aula.",
                "comp_type": "TEAM",
                "min_members": 5,
                "max_members": 6,
                "same_class_required": 0,
                "max_slots": 16,
                "requirements": "5 pemain inti + maksimal 1 cadangan. Bawa perangkat & kuota cadangan sendiri.",
                "juknis": (
                    "ATURAN MOBILE LEGENDS:\n"
                    "• Mode Custom Draft Pick, 5v5\n"
                    "• Penyisihan & Semifinal: Best of 1 (BO1); Final: Best of 3 (BO3)\n"
                    "• Dilarang chat all/taunting tidak sopan dan dilarang menggunakan program ilegal\n"
                    "• Pause teknis maksimal 2 kali per tim (maks. 3 menit)"
                ),
                "schedule_info": "Hari 2 · 10:00 WIB",
                "venue": "Lab Multimedia & Aula",
            },
            # 17 Agustus
            {
                "key": "tarik-tambang",
                "event_id": event_ids["17-agustus"],
                "name": "Tarik Tambang",
                "category": "Tradisional",
                "description": "Adu kekuatan dan kekompakan 5 siswa per kelas di lapangan upacara.",
                "comp_type": "TEAM",
                "min_members": 5,
                "max_members": 6,
                "same_class_required": 1,
                "max_slots": 16,
                "requirements": "Seluruh anggota dari kelas yang sama, wajib memakai sepatu olahraga.",
                "juknis": (
                    "ATURAN TARIK TAMBANG:\n"
                    "• Sistem best of 3 tarikan\n"
                    "• Dilarang melilitkan tali pada pinggang atau tangan demi keselamatan\n"
                    "• Posisi awal pita tengah tepat di garis netral"
                ),
                "schedule_info": "17 Agu · 09:00 WIB",
                "venue": "Lapangan Upacara",
            },
            {
                "key": "cerdas-cermat",
                "event_id": event_ids["17-agustus"],
                "name": "Cerdas Cermat Kebangsaan",
                "category": "Wawasan",
                "description": "Kuis cepat tepat seputar sejarah kemerdekaan, Pancasila, dan wawasan Nusantara.",
                "comp_type": "INDIVIDUAL",
                "min_members": 1,
                "max_members": 1,
                "same_class_required": 0,
                "max_slots": 20,
                "requirements": "Membawa kartu pelajar saat registrasi ulang.",
                "juknis": (
                    "KISI-KISI CERDAS CERMAT:\n"
                    "• Sejarah Proklamasi & Tokoh Pahlawan Nasional (40%)\n"
                    "• UUD 1945 & Nilai Pancasila (30%)\n"
                    "• Geografi & Budaya Nusantara (30%)"
                ),
                "schedule_info": "17 Agu · 11:00 WIB",
                "venue": "Aula Utama Lt. 1",
            },
        ]

        comp_ids = {}
        for c in competitions_data:
            cur = conn.execute(
                """
                INSERT INTO competitions
                    (event_id, name, category, description, comp_type,
                     min_members, max_members, same_class_required, max_slots,
                     requirements, juknis, schedule_info, venue)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c["event_id"], c["name"], c["category"], c["description"], c["comp_type"],
                    c["min_members"], c["max_members"], c["same_class_required"], c["max_slots"],
                    c["requirements"], c["juknis"], c["schedule_info"], c["venue"],
                ),
            )
            comp_ids[c["key"]] = cur.lastrowid

        # Helper insert registrasi
        reg_counter = [1]

        def add_individual(event_slug, comp_key, name, nis, kelas, status="Accepted", contact="0812-0000-0000"):
            code = f"LMB-2026-{reg_counter[0]:04d}"
            reg_counter[0] += 1
            cur = conn.execute(
                """
                INSERT INTO registrations
                    (registration_code, event_id, competition_id, participant_name, nis, kelas,
                     contact, team_name, status, juknis_confirmed)
                VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, 1)
                """,
                (code, event_ids[event_slug], comp_ids[comp_key], name, nis, kelas, contact, status),
            )
            return cur.lastrowid

        def add_team(event_slug, comp_key, team_name, kelas, members, status="Accepted", contact="0813-0000-0000"):
            """members: list of (name, nis, kelas_anggota) -> index 0 adalah ketua tim."""
            code = f"LMB-2026-{reg_counter[0]:04d}"
            reg_counter[0] += 1
            captain_name, captain_nis, _ = members[0]
            cur = conn.execute(
                """
                INSERT INTO registrations
                    (registration_code, event_id, competition_id, participant_name, nis, kelas,
                     contact, team_name, status, juknis_confirmed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (code, event_ids[event_slug], comp_ids[comp_key], captain_name, captain_nis, kelas, contact, team_name, status),
            )
            reg_id = cur.lastrowid
            for idx, (m_name, m_nis, m_kelas) in enumerate(members):
                conn.execute(
                    """
                    INSERT INTO team_members (registration_id, member_name, member_nis, member_kelas, is_captain)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (reg_id, m_name, m_nis, m_kelas, 1 if idx == 0 else 0),
                )
            return reg_id

        # ------------------------------------------------------------------
        # 3. PESERTA DEMO — BULAN BAHASA
        # ------------------------------------------------------------------
        pidato_students = [
            ("Alya Rahmadhani", "240101", "XI IPA 1", "Accepted"),
            ("Dimas Nugroho", "240102", "XII IPS 2", "Accepted"),
            ("Keisha Azzahra", "240103", "X-4", "Accepted"),
            ("Fajar Ramadhan", "240104", "XI IPS 1", "Accepted"),
            ("Salsabila Putri", "240105", "XII IPA 3", "Accepted"),
            ("Naufal Hidayat", "240106", "X-2", "Accepted"),
            ("Clara Wijaya", "240107", "XI IPA 2", "Accepted"),
            ("Rizky Pratama", "240108", "XII IPA 1", "Accepted"),
        ]
        for s in pidato_students:
            add_individual("bulan-bahasa", "pidato", *s)

        debat_teams = [
            ("Veritas Debaters", "XI IPA 1", [
                ("Vania Kusuma", "240201", "XI IPA 1"),
                ("Kevin Tanuwijaya", "240202", "XI IPA 1"),
                ("Raisa Amalia", "240203", "XI IPA 2"),
            ]),
            ("Argon Speakers", "XII IPA 2", [
                ("Daffa Maheswara", "240204", "XII IPA 2"),
                ("Nabila Chairunnisa", "240205", "XII IPA 2"),
                ("Bima Sakti", "240206", "XII IPS 1"),
            ]),
            ("Nova Rhetoric", "X-1", [
                ("Larasati Dewi", "240207", "X-1"),
                ("Reyhan Akbar", "240208", "X-1"),
                ("Citra Lestari", "240209", "X-3"),
            ]),
            ("Eloquence Squad", "XI IPS 2", [
                ("Alvaro Gunawan", "240210", "XI IPS 2"),
                ("Mutiara Sani", "240211", "XI IPS 2"),
                ("Farhan Syahputra", "240212", "XI IPS 1"),
            ]),
        ]
        for t in debat_teams:
            add_team("bulan-bahasa", "debat", t[0], t[1], t[2], "Accepted")

        puisi_students = [
            ("Hana Kartika", "240301", "X-5", "Accepted"),
            ("Galang Perkasa", "240302", "XI IPS 3", "Registered"),
            ("Nadine Aurelia", "240303", "XII IPA 4", "Accepted"),
            ("Ilham Fauzi", "240304", "X-6", "Pending"),
            ("Zahra Khairunnisa", "240305", "XI IPA 3", "Registered"),
        ]
        for s in puisi_students:
            add_individual("bulan-bahasa", "puisi", *s)

        # ------------------------------------------------------------------
        # 4. PESERTA DEMO — PORAK
        # ------------------------------------------------------------------
        futsal_classes = [
            ("Garuda XI IPA 1", "XI IPA 1", "2501"),
            ("Phoenix XII IPS 1", "XII IPS 1", "2502"),
            ("Vanguard X-1", "X-1", "2503"),
            ("Titan XII IPA 2", "XII IPA 2", "2504"),
            ("Spartan XI IPS 2", "XI IPS 2", "2505"),
            ("Aether X-3", "X-3", "2506"),
            ("Eclipse XII IPA 1", "XII IPA 1", "2507"),
            ("Valiant XI IPA 3", "XI IPA 3", "2508"),
        ]
        sample_first = ["Rafi", "Bintang", "Arjun", "Zaki", "Dito", "Yoga", "Haikal", "Gilang"]
        for idx, (tname, kls, prefix) in enumerate(futsal_classes):
            members = [
                (f"{sample_first[(idx + m) % len(sample_first)]} {kls.split()[0]}#{m+1}", f"{prefix}{m+1:02d}", kls)
                for m in range(5)
            ]
            add_team("porak", "futsal", tname, kls, members, "Accepted")

        badminton_players = [
            ("Fikri Setiawan", "251101", "XII IPA 1", "Accepted"),
            ("Aldi Saputra", "251102", "XI IPS 1", "Accepted"),
            ("Tasya Maharani", "251103", "X-2", "Accepted"),
            ("Yoga Permana", "251104", "XII IPS 3", "Accepted"),
            ("Rendy Kurniawan", "251105", "XI IPA 2", "Accepted"),
            ("Siti Nurhaliza", "251106", "X-4", "Registered"),
        ]
        for s in badminton_players:
            add_individual("porak", "badminton", *s)

        mlbb_teams = [
            ("Liquid Five", "XII IPA 3", [
                ("Raka Gaming", "252101", "XII IPA 3"),
                ("Farel Z", "252102", "XII IPA 3"),
                ("Jovan K", "252103", "XII IPA 2"),
                ("Davin R", "252104", "XII IPA 3"),
                ("Niko P", "252105", "XII IPS 2"),
            ]),
            ("Astral Core", "XI IPA 1", [
                ("Kenzo A", "252201", "XI IPA 1"),
                ("Miko S", "252202", "XI IPA 1"),
                ("Reno W", "252203", "XI IPA 2"),
                ("Bayu D", "252204", "XI IPA 1"),
                ("Iqbal T", "252205", "XI IPS 1"),
            ]),
            ("Solaris X", "X-2", [
                ("Vino M", "252301", "X-2"),
                ("Riyan H", "252302", "X-2"),
                ("Tegar B", "252303", "X-1"),
                ("Alif N", "252304", "X-2"),
                ("Genta F", "252305", "X-3"),
            ]),
            ("Zenith Esports", "XII IPS 1", [
                ("Satria L", "252401", "XII IPS 1"),
                ("Andra V", "252402", "XII IPS 1"),
                ("Taufik E", "252403", "XII IPS 2"),
                ("Hendra C", "252404", "XII IPS 1"),
                ("Oki J", "252405", "XII IPS 1"),
            ]),
        ]
        for t in mlbb_teams:
            add_team("porak", "mlbb", t[0], t[1], t[2], "Accepted")

        # ------------------------------------------------------------------
        # 5. PESERTA DEMO — 17 AGUSTUS
        # ------------------------------------------------------------------
        for idx, (tname, kls, pref) in enumerate([
            ("Merah Putih XI-1", "XI IPA 1", "2601"),
            ("Banteng XII-2", "XII IPS 2", "2602"),
            ("Garuda X-4", "X-4", "2603"),
            ("Pejuang XI-3", "XI IPS 3", "2604"),
        ]):
            members = [(f"Anggota {tname.split()[0]} {m+1}", f"{pref}{m+1:02d}", kls) for m in range(5)]
            add_team("17-agustus", "tarik-tambang", tname, kls, members, "Registered")

        for idx, (name, nis, kls) in enumerate([
            ("Putri Kemerdekaan", "261101", "XI IPA 2"),
            ("Bagus Santoso", "261102", "XII IPA 1"),
            ("Dewi Sartika Putri", "261103", "X-1"),
            ("Rama Wijaya", "261104", "XI IPS 2"),
        ]):
            add_individual("17-agustus", "cerdas-cermat", name, nis, kls, "Registered")

        conn.commit()

        # ------------------------------------------------------------------
        # 6. BANGUN BRACKET DEMO + CONTOH PERTANDINGAN LIVE & PEMENANG
        # ------------------------------------------------------------------
        # A) FUTSAL PUTRA (8 tim -> Perempat Final selesai, Semifinal 1 LIVE, Semifinal 2 PENDING)
        build_bracket(conn, comp_ids["futsal"], shuffle=False)
        futsal_r1 = conn.execute(
            "SELECT * FROM matches WHERE competition_id = ? AND round_number = 1 ORDER BY match_order",
            (comp_ids["futsal"],),
        ).fetchall()
        r1_results = [(3, 1, 1), (2, 4, 2), (1, 0, 1), (2, 3, 2)]
        for m, (s1, s2, win) in zip(futsal_r1, r1_results):
            update_match(conn, m["id"], score1=s1, score2=s2, winner_slot=win, scheduled_time="Hari 1 · Selesai")

        futsal_r2 = conn.execute(
            "SELECT * FROM matches WHERE competition_id = ? AND round_number = 2 ORDER BY match_order",
            (comp_ids["futsal"],),
        ).fetchall()
        if len(futsal_r2) >= 2:
            update_match(conn, futsal_r2[0]["id"], score1=2, score2=2, status="LIVE", scheduled_time="SEDANG BERLANGSUNG")
            update_match(conn, futsal_r2[1]["id"], score1=0, score2=0, status="PENDING", scheduled_time="Hari 2 · 11:00 WIB")

        # B) PIDATO BAHASA INDONESIA (8 peserta -> 2 match R1 selesai, 1 LIVE, 1 PENDING)
        build_bracket(conn, comp_ids["pidato"], shuffle=False)
        pidato_r1 = conn.execute(
            "SELECT * FROM matches WHERE competition_id = ? AND round_number = 1 ORDER BY match_order",
            (comp_ids["pidato"],),
        ).fetchall()
        if len(pidato_r1) >= 4:
            update_match(conn, pidato_r1[0]["id"], score1=92, score2=86, winner_slot=1, scheduled_time="09:30 WIB")
            update_match(conn, pidato_r1[1]["id"], score1=84, score2=89, winner_slot=2, scheduled_time="09:50 WIB")
            update_match(conn, pidato_r1[2]["id"], score1=88, score2=87, status="LIVE", scheduled_time="SEDANG TAMPIL")
            update_match(conn, pidato_r1[3]["id"], score1=0, score2=0, status="PENDING", scheduled_time="10:30 WIB")

        # C) DEBAT BAHASA INGGRIS (4 tim -> SELESAI SAMPAI JUARA FINAL!)
        build_bracket(conn, comp_ids["debat"], shuffle=False)
        debat_r1 = conn.execute(
            "SELECT * FROM matches WHERE competition_id = ? AND round_number = 1 ORDER BY match_order",
            (comp_ids["debat"],),
        ).fetchall()
        if len(debat_r1) >= 2:
            update_match(conn, debat_r1[0]["id"], score1=85, score2=79, winner_slot=1, scheduled_time="Selesai")
            update_match(conn, debat_r1[1]["id"], score1=81, score2=84, winner_slot=2, scheduled_time="Selesai")
        debat_final = conn.execute(
            "SELECT * FROM matches WHERE competition_id = ? AND round_number = 2 LIMIT 1",
            (comp_ids["debat"],),
        ).fetchone()
        if debat_final:
            update_match(conn, debat_final["id"], score1=91, score2=88, winner_slot=1, scheduled_time="Final Selesai")

        # D) BADMINTON TUNGGAL (6 peserta -> otomatis mendemonstrasikan BYE di bracket!)
        build_bracket(conn, comp_ids["badminton"], shuffle=False)

        # E) MOBILE LEGENDS (4 tim -> Semifinal selesai, Final sedang LIVE!)
        build_bracket(conn, comp_ids["mlbb"], shuffle=False)
        mlbb_r1 = conn.execute(
            "SELECT * FROM matches WHERE competition_id = ? AND round_number = 1 ORDER BY match_order",
            (comp_ids["mlbb"],),
        ).fetchall()
        if len(mlbb_r1) >= 2:
            update_match(conn, mlbb_r1[0]["id"], score1=1, score2=0, winner_slot=1, scheduled_time="BO1 Selesai")
            update_match(conn, mlbb_r1[1]["id"], score1=0, score2=1, winner_slot=2, scheduled_time="BO1 Selesai")
        mlbb_final = conn.execute(
            "SELECT * FROM matches WHERE competition_id = ? AND round_number = 2 LIMIT 1",
            (comp_ids["mlbb"],),
        ).fetchone()
        if mlbb_final:
            update_match(conn, mlbb_final["id"], score1=1, score2=1, status="LIVE", scheduled_time="GRAND FINAL BO3")

        conn.commit()
    finally:
        conn.close()
