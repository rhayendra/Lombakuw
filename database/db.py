"""
Manajemen koneksi dan skema database SQLite untuk Lombaku.
Menggunakan modul bawaan Python `sqlite3` agar ringan dan mudah dipelajari.
"""
import sqlite3
from flask import g
from config import Config


def get_db():
    """Mengambil koneksi database SQLite yang aktif pada request saat ini."""
    if "db" not in g:
        g.db = sqlite3.connect(Config.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row  # Agar hasil query bisa diakses seperti dict (row['nama'])
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """Menutup koneksi database saat request selesai."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_standalone_db():
    """Membuka koneksi database di luar request Flask (misal saat seed awal)."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    subtitle TEXT DEFAULT '',
    description TEXT NOT NULL,
    theme_accent TEXT DEFAULT 'cyan',
    icon_type TEXT DEFAULT 'trophy',
    event_date TEXT NOT NULL,
    registration_open TEXT NOT NULL,
    registration_deadline TEXT NOT NULL,
    schedule_text TEXT DEFAULT '',
    juknis TEXT DEFAULT '',
    committee_info TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'OPEN',
    is_featured INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT DEFAULT 'Umum',
    description TEXT DEFAULT '',
    comp_type TEXT NOT NULL DEFAULT 'INDIVIDUAL',
    min_members INTEGER NOT NULL DEFAULT 1,
    max_members INTEGER NOT NULL DEFAULT 1,
    same_class_required INTEGER NOT NULL DEFAULT 0,
    max_slots INTEGER NOT NULL DEFAULT 32,
    requirements TEXT DEFAULT '',
    juknis TEXT DEFAULT '',
    schedule_info TEXT DEFAULT '',
    venue TEXT DEFAULT '',
    bracket_locked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_code TEXT UNIQUE NOT NULL,
    event_id INTEGER NOT NULL,
    competition_id INTEGER NOT NULL,
    participant_name TEXT NOT NULL,
    nis TEXT NOT NULL,
    kelas TEXT NOT NULL,
    contact TEXT DEFAULT '',
    team_name TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Registered',
    juknis_confirmed INTEGER NOT NULL DEFAULT 1,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER NOT NULL,
    member_name TEXT NOT NULL,
    member_nis TEXT NOT NULL,
    member_kelas TEXT NOT NULL,
    is_captain INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (registration_id) REFERENCES registrations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    round_name TEXT NOT NULL,
    match_order INTEGER NOT NULL,
    participant1_id INTEGER,
    participant2_id INTEGER,
    participant1_label TEXT DEFAULT 'TBD',
    participant2_label TEXT DEFAULT 'TBD',
    score1 INTEGER DEFAULT 0,
    score2 INTEGER DEFAULT 0,
    winner_id INTEGER,
    winner_label TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'PENDING',
    scheduled_time TEXT DEFAULT '',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
    FOREIGN KEY (participant1_id) REFERENCES registrations(id) ON DELETE SET NULL,
    FOREIGN KEY (participant2_id) REFERENCES registrations(id) ON DELETE SET NULL,
    FOREIGN KEY (winner_id) REFERENCES registrations(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_reg_event_nis ON registrations(event_id, nis);
CREATE INDEX IF NOT EXISTS idx_reg_comp ON registrations(competition_id);
CREATE INDEX IF NOT EXISTS idx_member_nis ON team_members(member_nis);
CREATE INDEX IF NOT EXISTS idx_matches_comp ON matches(competition_id);
"""


def init_db():
    """Membuat seluruh tabel database jika belum ada."""
    conn = get_standalone_db()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
