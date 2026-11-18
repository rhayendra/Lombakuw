"""
Layanan pendaftaran peserta individu dan tim Lombaku.
Semua aturan validasi dijalankan di sisi backend agar aman dan tidak bisa dilewati.
"""
from datetime import datetime
from services.events import compute_effective_status


def generate_registration_code(db) -> str:
    """Menghasilkan kode pendaftaran unik, contoh: LMB-2026-0024."""
    year = datetime.now().year
    row = db.execute("SELECT MAX(id) AS max_id FROM registrations").fetchone()
    next_num = (row["max_id"] or 0) + 1
    while True:
        code = f"LMB-{year}-{next_num:04d}"
        exists = db.execute(
            "SELECT 1 FROM registrations WHERE registration_code = ?", (code,)
        ).fetchone()
        if not exists:
            return code
        next_num += 1


def find_existing_nis_in_event(db, event_id: int, nis_list: list):
    """
    Mengecek apakah ada NIS dalam daftar yang sudah terdaftar (status bukan Rejected)
    pada event yang sama, baik sebagai peserta individu, ketua tim, maupun anggota tim.
    Mengembalikan tuple (nis, nama_cabang) jika ditemukan duplikasi.
    """
    cleaned = [n.strip() for n in nis_list if n and n.strip()]
    if not cleaned:
        return None

    placeholders = ",".join(["?"] * len(cleaned))

    # Cek pada tabel registrations (individu & ketua tim)
    row = db.execute(
        f"""
        SELECT r.nis, c.name AS comp_name
        FROM registrations r
        JOIN competitions c ON c.id = r.competition_id
        WHERE r.event_id = ? AND r.status != 'Rejected' AND r.nis IN ({placeholders})
        LIMIT 1
        """,
        [event_id] + cleaned,
    ).fetchone()
    if row:
        return (row["nis"], row["comp_name"])

    # Cek pada tabel team_members (anggota tim)
    row = db.execute(
        f"""
        SELECT tm.member_nis AS nis, c.name AS comp_name
        FROM team_members tm
        JOIN registrations r ON r.id = tm.registration_id
        JOIN competitions c ON c.id = r.competition_id
        WHERE r.event_id = ? AND r.status != 'Rejected' AND tm.member_nis IN ({placeholders})
        LIMIT 1
        """,
        [event_id] + cleaned,
    ).fetchone()
    if row:
        return (row["nis"], row["comp_name"])

    return None


def create_registration(db, payload: dict) -> tuple:
    """
    Memvalidasi dan menyimpan pendaftaran lomba baru.
    Mengembalikan (True, registration_dict) jika sukses, atau (False, pesan_error).
    """
    try:
        competition_id = int(payload.get("competition_id", 0))
    except (ValueError, TypeError):
        return False, "Cabang lomba tidak valid."

    comp = db.execute("SELECT * FROM competitions WHERE id = ?", (competition_id,)).fetchone()
    if not comp:
        return False, "Cabang lomba tidak ditemukan."

    event = db.execute("SELECT * FROM events WHERE id = ?", (comp["event_id"],)).fetchone()
    if not event:
        return False, "Event tidak ditemukan."

    # 1. Validasi status event & jadwal pendaftaran otomatis
    status_info = compute_effective_status(event)
    if not status_info["can_register"]:
        return False, f"Pendaftaran tidak tersedia: {status_info['status_reason']}"

    # 2. Validasi wajib membaca tab Juknis terlebih dahulu
    juknis_confirmed = str(payload.get("juknis_confirmed", "")).lower() in ("1", "true", "yes", "on")
    if not juknis_confirmed:
        return False, "Anda wajib membuka dan menyetujui tab Juknis terlebih dahulu sebelum mendaftar."

    # 3. Validasi kuota cabang lomba
    current_slots = db.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE competition_id = ? AND status != 'Rejected'",
        (competition_id,),
    ).fetchone()["c"]
    if current_slots >= comp["max_slots"]:
        return False, f"Kuota cabang lomba {comp['name']} sudah penuh ({comp['max_slots']} slot)."

    contact = (payload.get("contact") or "").strip()
    notes = (payload.get("notes") or "").strip()

    if comp["comp_type"] == "INDIVIDUAL":
        student_name = (payload.get("participant_name") or "").strip()
        nis = (payload.get("nis") or "").strip()
        kelas = (payload.get("kelas") or "").strip()

        if not student_name or not nis or not kelas:
            return False, "Nama siswa, NIS, dan Kelas wajib diisi."
        if len(nis) < 4:
            return False, "Format NIS minimal 4 karakter."

        # 4. Aturan 1 siswa hanya boleh mendaftar 1 cabang lomba dalam 1 event
        duplicate = find_existing_nis_in_event(db, event["id"], [nis])
        if duplicate:
            dup_nis, dup_comp = duplicate
            return (
                False,
                f"NIS {dup_nis} sudah terdaftar pada cabang '{dup_comp}' di event {event['name']}. "
                "Satu siswa hanya boleh mendaftar satu cabang lomba per event.",
            )

        reg_code = generate_registration_code(db)
        cur = db.execute(
            """
            INSERT INTO registrations
                (registration_code, event_id, competition_id, participant_name, nis, kelas,
                 contact, team_name, status, juknis_confirmed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, '', 'Registered', 1, ?)
            """,
            (reg_code, event["id"], competition_id, student_name, nis, kelas, contact, notes),
        )
        db.commit()
        return True, {
            "id": cur.lastrowid,
            "registration_code": reg_code,
            "participant_name": student_name,
            "competition_name": comp["name"],
            "event_name": event["name"],
            "status": "Registered",
        }

    # --- LOMBA TIM ---
    team_name = (payload.get("team_name") or "").strip()
    captain_name = (payload.get("participant_name") or "").strip()
    captain_nis = (payload.get("nis") or "").strip()
    captain_kelas = (payload.get("kelas") or "").strip()
    raw_members = payload.get("members") or []

    if not team_name or not captain_name or not captain_nis or not captain_kelas:
        return False, "Nama tim, nama ketua, NIS ketua, dan kelas wajib diisi."

    # Susun daftar anggota lengkap (ketua termasuk dalam hitungan anggota tim)
    cleaned_members = [
        {
            "member_name": captain_name,
            "member_nis": captain_nis,
            "member_kelas": captain_kelas,
            "is_captain": 1,
        }
    ]

    for m in raw_members:
        m_name = (m.get("name") or "").strip()
        m_nis = (m.get("nis") or "").strip()
        m_kelas = (m.get("kelas") or captain_kelas).strip()
        if not m_name and not m_nis:
            continue
        if not m_name or not m_nis:
            return False, "Setiap baris anggota tim harus memiliki Nama dan NIS yang lengkap."
        # Hindari duplikasi jika user memasukkan ketua lagi di daftar anggota tambahan
        if m_nis == captain_nis:
            return False, f"NIS ketua tim ({captain_nis}) tidak perlu dimasukkan ulang di daftar anggota."
        cleaned_members.append(
            {
                "member_name": m_name,
                "member_nis": m_nis,
                "member_kelas": m_kelas,
                "is_captain": 0,
            }
        )

    total_members = len(cleaned_members)
    if total_members < comp["min_members"]:
        return (
            False,
            f"Cabang {comp['name']} membutuhkan minimal {comp['min_members']} orang "
            f"(termasuk ketua). Saat ini baru terisi {total_members} orang.",
        )
    if total_members > comp["max_members"]:
        return (
            False,
            f"Cabang {comp['name']} maksimal terdiri dari {comp['max_members']} orang "
            f"(termasuk ketua). Saat ini terisi {total_members} orang.",
        )

    # Cek duplikasi NIS di dalam formulir tim yang sama
    all_nis = [m["member_nis"] for m in cleaned_members]
    if len(set(all_nis)) != len(all_nis):
        return False, "Terdapat NIS anggota yang sama di dalam tim Anda. Setiap anggota harus berbeda."

    # Cek aturan wajib satu kelas jika diaktifkan admin
    if comp["same_class_required"]:
        base_class = captain_kelas.upper().replace(" ", "")
        for m in cleaned_members:
            if m["member_kelas"].upper().replace(" ", "") != base_class:
                return (
                    False,
                    f"Cabang {comp['name']} mewajibkan seluruh anggota berasal dari kelas yang sama "
                    f"({captain_kelas}). Anggota '{m['member_name']}' tercatat di kelas '{m['member_kelas']}'.",
                )

    # Cek aturan 1 siswa 1 cabang per event untuk seluruh anggota tim
    duplicate = find_existing_nis_in_event(db, event["id"], all_nis)
    if duplicate:
        dup_nis, dup_comp = duplicate
        return (
            False,
            f"NIS {dup_nis} sudah terdaftar pada cabang '{dup_comp}' di event {event['name']}. "
            "Setiap siswa hanya diperbolehkan mengikuti satu cabang lomba dalam event yang sama.",
        )

    reg_code = generate_registration_code(db)
    cur = db.execute(
        """
        INSERT INTO registrations
            (registration_code, event_id, competition_id, participant_name, nis, kelas,
             contact, team_name, status, juknis_confirmed, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Registered', 1, ?)
        """,
        (reg_code, event["id"], competition_id, captain_name, captain_nis, captain_kelas, contact, team_name, notes),
    )
    reg_id = cur.lastrowid

    for m in cleaned_members:
        db.execute(
            """
            INSERT INTO team_members (registration_id, member_name, member_nis, member_kelas, is_captain)
            VALUES (?, ?, ?, ?, ?)
            """,
            (reg_id, m["member_name"], m["member_nis"], m["member_kelas"], m["is_captain"]),
        )

    db.commit()
    return True, {
        "id": reg_id,
        "registration_code": reg_code,
        "participant_name": team_name,
        "captain_name": captain_name,
        "member_count": total_members,
        "competition_name": comp["name"],
        "event_name": event["name"],
        "status": "Registered",
    }


def lookup_registrations(db, query: str) -> list:
    """Mencari status pendaftaran berdasarkan NIS siswa atau kode pendaftaran."""
    q = (query or "").strip()
    if not q:
        return []

    rows = db.execute(
        """
        SELECT DISTINCT r.*, e.name AS event_name, c.name AS competition_name, c.comp_type
        FROM registrations r
        JOIN events e ON e.id = r.event_id
        JOIN competitions c ON c.id = r.competition_id
        LEFT JOIN team_members tm ON tm.registration_id = r.id
        WHERE r.nis = ? OR r.registration_code = ? OR tm.member_nis = ?
        ORDER BY r.created_at DESC
        """,
        (q, q.upper(), q),
    ).fetchall()

    results = []
    for r in rows:
        item = dict(r)
        members = db.execute(
            "SELECT * FROM team_members WHERE registration_id = ? ORDER BY is_captain DESC, id ASC",
            (r["id"],),
        ).fetchall()
        item["members"] = [dict(m) for m in members]
        results.append(item)
    return results


def get_participants(db, event_id=None, competition_id=None, status=None, search=None) -> list:
    """Mengambil daftar peserta lengkap beserta anggota tim untuk dashboard admin."""
    sql = """
        SELECT r.*, e.name AS event_name, c.name AS competition_name, c.comp_type
        FROM registrations r
        JOIN events e ON e.id = r.event_id
        JOIN competitions c ON c.id = r.competition_id
        WHERE 1=1
    """
    params = []
    if event_id:
        sql += " AND r.event_id = ?"
        params.append(event_id)
    if competition_id:
        sql += " AND r.competition_id = ?"
        params.append(competition_id)
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    if search:
        like = f"%{search.strip()}%"
        sql += " AND (r.participant_name LIKE ? OR r.team_name LIKE ? OR r.nis LIKE ? OR r.kelas LIKE ? OR r.registration_code LIKE ?)"
        params.extend([like, like, like, like, like])

    sql += " ORDER BY r.created_at DESC, r.id DESC"
    rows = db.execute(sql, params).fetchall()

    items = []
    for r in rows:
        d = dict(r)
        members = db.execute(
            "SELECT * FROM team_members WHERE registration_id = ? ORDER BY is_captain DESC, id ASC",
            (r["id"],),
        ).fetchall()
        d["members"] = [dict(m) for m in members]
        items.append(d)
    return items
