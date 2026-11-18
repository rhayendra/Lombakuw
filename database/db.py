"""
Manajemen koneksi dan skema database Lombaku (Dual-Engine: SQLite & Supabase PostgreSQL).
- Di komputer lokal tanpa DATABASE_URL -> memakai SQLite bawaan Python.
- Di Vercel dengan DATABASE_URL Supabase -> otomatis memakai PostgreSQL Supabase yang permanen.
"""
import re
import sqlite3
from flask import g
from config import Config

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None


def _translate_sql_for_postgres(sql: str) -> tuple:
    """
    Menyesuaikan query SQL bergaya SQLite agar berjalan mulus di PostgreSQL (Supabase):
    - Placeholder '?' -> '%s'
    - Pencarian ' LIKE ' -> ' ILIKE ' (case-insensitive seperti SQLite)
    - '= CURRENT_TIMESTAMP' -> teks format YYYY-MM-DD HH24:MI:SS
    - Menambahkan 'RETURNING id' pada INSERT tabel yang memiliki kolom id
    """
    pg_sql = sql.replace("?", "%s")
    pg_sql = re.sub(r"\bLIKE\b", "ILIKE", pg_sql, flags=re.IGNORECASE)
    pg_sql = re.sub(
        r"=\s*CURRENT_TIMESTAMP\b",
        "= to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')",
        pg_sql,
        flags=re.IGNORECASE,
    )

    needs_returning_id = False
    stripped = pg_sql.strip()
    upper = stripped.upper()
    if upper.startswith("INSERT INTO ") and "RETURNING" not in upper and "ON CONFLICT" not in upper:
        # Tabel yang memiliki kolom id auto-increment
        if not re.match(r"INSERT\s+INTO\s+settings\b", stripped, flags=re.IGNORECASE):
            pg_sql = stripped.rstrip(";") + " RETURNING id"
            needs_returning_id = True

    return pg_sql, needs_returning_id


class _CursorWrapper:
    """Pembungkus cursor agar antarmuka fetchone/fetchall/lastrowid identik antara SQLite & Postgres."""
    def __init__(self, cursor, lastrowid=None):
        self._cursor = cursor
        self.lastrowid = lastrowid if lastrowid is not None else getattr(cursor, "lastrowid", None)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class DBConnection:
    """Pembungkus koneksi universal untuk SQLite dan Supabase PostgreSQL."""
    def __init__(self, conn, is_postgres: bool = False):
        self._conn = conn
        self.is_postgres = is_postgres

    def execute(self, sql: str, params=None):
        params = tuple(params) if params is not None else ()
        if not self.is_postgres:
            cur = self._conn.execute(sql, params)
            return _CursorWrapper(cur, lastrowid=cur.lastrowid)

        pg_sql, needs_returning_id = _translate_sql_for_postgres(sql)
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(pg_sql, params)
        lastrowid = None
        if needs_returning_id:
            row = cur.fetchone()
            if row and "id" in row:
                lastrowid = row["id"]
        return _CursorWrapper(cur, lastrowid=lastrowid)

    def executescript(self, script: str):
        if not self.is_postgres:
            self._conn.executescript(script)
            return
        cur = self._conn.cursor()
        # Jalankan setiap statement DDL secara terpisah di PostgreSQL
        for stmt in script.split(";"):
            cleaned = stmt.strip()
            if cleaned:
                cur.execute(cleaned)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _open_raw_connection() -> DBConnection:
    """Membuka koneksi baru sesuai mode (Supabase PostgreSQL atau SQLite)."""
    if Config.USE_POSTGRES:
        if psycopg2 is None:
            raise RuntimeError("Paket 'psycopg2-binary' belum terpasang. Jalankan: pip install -r requirements.txt")
        dsn = Config.DATABASE_URL
        # Supabase membutuhkan koneksi SSL
        if "sslmode=" not in dsn:
            sep = "&" if "?" in dsn else "?"
            dsn = f"{dsn}{sep}sslmode=require"
        conn = psycopg2.connect(dsn)
        return DBConnection(conn, is_postgres=True)

    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return DBConnection(conn, is_postgres=False)


def get_db() -> DBConnection:
    """Mengambil koneksi database yang aktif pada request Flask saat ini."""
    if "db" not in g:
        g.db = _open_raw_connection()
    return g.db


def close_db(e=None):
    """Menutup koneksi database saat request berakhir (penting untuk pooler Supabase)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_standalone_db() -> DBConnection:
    """Membuka koneksi database di luar request Flask (saat inisialisasi & seed)."""
    return _open_raw_connection()


SQLITE_SCHEMA_SQL = """
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


POSTGRES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
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
    created_at TEXT DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS competitions (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
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
    created_at TEXT DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS registrations (
    id SERIAL PRIMARY KEY,
    registration_code TEXT UNIQUE NOT NULL,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    participant_name TEXT NOT NULL,
    nis TEXT NOT NULL,
    kelas TEXT NOT NULL,
    contact TEXT DEFAULT '',
    team_name TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Registered',
    juknis_confirmed INTEGER NOT NULL DEFAULT 1,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    registration_id INTEGER NOT NULL REFERENCES registrations(id) ON DELETE CASCADE,
    member_name TEXT NOT NULL,
    member_nis TEXT NOT NULL,
    member_kelas TEXT NOT NULL,
    is_captain INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    round_name TEXT NOT NULL,
    match_order INTEGER NOT NULL,
    participant1_id INTEGER REFERENCES registrations(id) ON DELETE SET NULL,
    participant2_id INTEGER REFERENCES registrations(id) ON DELETE SET NULL,
    participant1_label TEXT DEFAULT 'TBD',
    participant2_label TEXT DEFAULT 'TBD',
    score1 INTEGER DEFAULT 0,
    score2 INTEGER DEFAULT 0,
    winner_id INTEGER REFERENCES registrations(id) ON DELETE SET NULL,
    winner_label TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'PENDING',
    scheduled_time TEXT DEFAULT '',
    updated_at TEXT DEFAULT to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
);

CREATE INDEX IF NOT EXISTS idx_reg_event_nis ON registrations(event_id, nis);
CREATE INDEX IF NOT EXISTS idx_reg_comp ON registrations(competition_id);
CREATE INDEX IF NOT EXISTS idx_member_nis ON team_members(member_nis);
CREATE INDEX IF NOT EXISTS idx_matches_comp ON matches(competition_id);
"""


def init_db():
    """Membuat seluruh tabel database jika belum ada (SQLite maupun Supabase PostgreSQL)."""
    conn = get_standalone_db()
    try:
        schema = POSTGRES_SCHEMA_SQL if conn.is_postgres else SQLITE_SCHEMA_SQL
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
