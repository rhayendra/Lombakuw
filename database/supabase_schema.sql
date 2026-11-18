-- ============================================================================
-- LOMBAKU — SKEMA POSTGRESQL UNTUK SUPABASE
-- Catatan: Aplikasi Lombaku otomatis membuat tabel ini saat pertama dijalankan
-- jika DATABASE_URL sudah diatur di Vercel. File ini disediakan jika Anda ingin
-- menjalankan atau memeriksa skema secara manual di Supabase SQL Editor.
-- ============================================================================

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
