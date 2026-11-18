"""
Layanan manajemen Event dan Cabang Lomba Lombaku.
Menangani pengecekan jadwal otomatis (auto-lock) serta agregasi statistik event.
"""
from datetime import datetime


def parse_dt(dt_str: str):
    """Mengubah string ISO datetime menjadi objek datetime dengan aman."""
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str.strip(), fmt)
        except ValueError:
            continue
    return None


def format_indo_date(dt_str: str) -> str:
    """Memformat tanggal ISO ke tampilan ringkas Bahasa Indonesia."""
    dt = parse_dt(dt_str)
    if not dt:
        return dt_str or "-"
    months = [
        "", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
        "Jul", "Agu", "Sep", "Okt", "Nov", "Des"
    ]
    return f"{dt.day:02d} {months[dt.month]} {dt.year}, {dt.strftime('%H:%M')} WIB"


def compute_effective_status(event_row) -> dict:
    """
    Menghitung status efektif event berdasarkan status manual admin + jadwal otomatis.
    Mendukung 5 status: OPEN, ONGOING, LOCKED, COMPLETED, CLOSED.
    """
    manual_status = (event_row["status"] or "CLOSED").upper()
    now = datetime.now()
    reg_open = parse_dt(event_row["registration_open"])
    reg_deadline = parse_dt(event_row["registration_deadline"])

    effective_status = manual_status
    reason = "Pendaftaran sedang dibuka."
    can_register = False

    if manual_status == "CLOSED":
        effective_status = "CLOSED"
        reason = "Event ditutup oleh panitia."
    elif manual_status == "LOCKED":
        effective_status = "LOCKED"
        reason = "Pendaftaran dikunci oleh panitia."
    elif manual_status == "COMPLETED":
        effective_status = "COMPLETED"
        reason = "Rangkaian perlombaan telah selesai dilaksanakan."
    elif manual_status == "ONGOING":
        effective_status = "ONGOING"
        if reg_deadline and now <= reg_deadline and (not reg_open or now >= reg_open):
            can_register = True
            reason = f"Event sedang berlangsung! Susulan dibuka hingga {format_indo_date(event_row['registration_deadline'])}."
        else:
            can_register = False
            reason = "Pertandingan sedang berlangsung secara langsung."
    else:
        # Status manual OPEN -> cek jendela jadwal pendaftaran otomatis
        if reg_open and now < reg_open:
            effective_status = "LOCKED"
            reason = f"Pendaftaran dibuka mulai {format_indo_date(event_row['registration_open'])}."
        elif reg_deadline and now > reg_deadline:
            effective_status = "LOCKED"
            reason = f"Batas pendaftaran telah berakhir pada {format_indo_date(event_row['registration_deadline'])}."
        else:
            effective_status = "OPEN"
            reason = f"Terbuka hingga {format_indo_date(event_row['registration_deadline'])}."
            can_register = True

    return {
        "manual_status": manual_status,
        "effective_status": effective_status,
        "can_register": can_register,
        "status_reason": reason,
    }


def enrich_event(db, event_row) -> dict:
    """Mengubah row event menjadi dictionary lengkap dengan statistik dan status efektif."""
    event = dict(event_row)
    status_info = compute_effective_status(event_row)
    event.update(status_info)

    comp_count = db.execute(
        "SELECT COUNT(*) AS c FROM competitions WHERE event_id = ?", (event["id"],)
    ).fetchone()["c"]

    reg_count = db.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE event_id = ? AND status != 'Rejected'",
        (event["id"],),
    ).fetchone()["c"]

    live_matches = db.execute(
        """
        SELECT COUNT(*) AS c
        FROM matches m
        JOIN competitions c ON c.id = m.competition_id
        WHERE c.event_id = ? AND m.status = 'LIVE'
        """,
        (event["id"],),
    ).fetchone()["c"]

    completed_matches = db.execute(
        """
        SELECT COUNT(*) AS c
        FROM matches m
        JOIN competitions c ON c.id = m.competition_id
        WHERE c.event_id = ? AND m.status = 'COMPLETED'
        """,
        (event["id"],),
    ).fetchone()["c"]

    event["competition_count"] = comp_count
    event["participant_count"] = reg_count
    event["live_match_count"] = live_matches
    event["completed_match_count"] = completed_matches
    event["event_date_label"] = format_indo_date(event["event_date"])
    event["deadline_label"] = format_indo_date(event["registration_deadline"])
    return event


def get_all_events(db) -> list:
    """Mengambil seluruh event beserta statistiknya secara terurut."""
    rows = db.execute(
        "SELECT * FROM events ORDER BY sort_order ASC, id ASC"
    ).fetchall()
    return [enrich_event(db, r) for r in rows]


def get_event_by_id(db, event_id: int):
    """Mengambil satu event lengkap berdasarkan ID."""
    row = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        return None
    return enrich_event(db, row)


def get_event_by_slug(db, slug: str):
    """Mengambil satu event lengkap berdasarkan slug URL."""
    row = db.execute("SELECT * FROM events WHERE slug = ?", (slug,)).fetchone()
    if not row:
        return None
    return enrich_event(db, row)


def get_competitions_for_event(db, event_id: int) -> list:
    """Mengambil daftar cabang lomba dalam sebuah event beserta jumlah pendaftar."""
    rows = db.execute(
        """
        SELECT c.*,
               (SELECT COUNT(*) FROM registrations r
                WHERE r.competition_id = c.id AND r.status != 'Rejected') AS registered_count,
               (SELECT COUNT(*) FROM matches m WHERE m.competition_id = c.id) AS match_count,
               (SELECT COUNT(*) FROM matches m WHERE m.competition_id = c.id AND m.status = 'LIVE') AS live_count
        FROM competitions c
        WHERE c.event_id = ?
        ORDER BY c.id ASC
        """,
        (event_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_competitions(db) -> list:
    """Mengambil semua cabang lomba beserta nama event induknya."""
    rows = db.execute(
        """
        SELECT c.*, e.name AS event_name, e.slug AS event_slug, e.status AS event_status,
               (SELECT COUNT(*) FROM registrations r
                WHERE r.competition_id = c.id AND r.status != 'Rejected') AS registered_count,
               (SELECT COUNT(*) FROM matches m WHERE m.competition_id = c.id) AS match_count
        FROM competitions c
        JOIN events e ON e.id = c.event_id
        ORDER BY e.sort_order ASC, c.id ASC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def get_settings(db) -> dict:
    """Mengambil konfigurasi umum sekolah & aplikasi dari tabel settings."""
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    data = {r["key"]: r["value"] for r in rows}
    data.setdefault("school_name", "SMA Negeri Nusantara 01")
    data.setdefault("school_tagline", "Platform Manajemen Perlombaan Sekolah Digital")
    data.setdefault("committee_contact", "OSIS & MPK — Ruang Sekretariat Lt. 2 · WA 0812-3456-7890")
    data.setdefault("announcement", "Pendaftaran Bulan Bahasa & PORAK 2026 sedang dibuka. Pastikan membaca Juknis sebelum mendaftar.")
    return data
