"""
Routes halaman publik (Siswa & Pengunjung) untuk Lombaku.
Meliputi: Home Hero Experience, Daftar Event, Detail Event, Pendaftaran, Bracket, dan Informasi.
"""
from flask import Blueprint, render_template, request, abort
from database.db import get_db
from services.events import (
    get_all_events,
    get_event_by_slug,
    get_competitions_for_event,
    get_all_competitions,
    get_settings,
)
from services.bracket import get_bracket_data
from services.registration import lookup_registrations

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    """Halaman Beranda — Hero Experience dengan showcase event utama dan floating glass panels."""
    db = get_db()
    events = get_all_events(db)
    for ev in events:
        ev["competitions"] = get_competitions_for_event(db, ev["id"])

    # Statistik agregat sekolah
    total_participants = db.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE status != 'Rejected'"
    ).fetchone()["c"]
    total_competitions = db.execute("SELECT COUNT(*) AS c FROM competitions").fetchone()["c"]
    live_matches = db.execute(
        """
        SELECT m.*, c.name AS competition_name, c.id AS comp_id, e.name AS event_name
        FROM matches m
        JOIN competitions c ON c.id = m.competition_id
        JOIN events e ON e.id = c.event_id
        WHERE m.status = 'LIVE'
        ORDER BY m.updated_at DESC
        LIMIT 5
        """
    ).fetchall()

    recent_winners = db.execute(
        """
        SELECT m.winner_label, m.round_name, m.score1, m.score2,
               c.name AS competition_name, c.id AS comp_id, e.name AS event_name
        FROM matches m
        JOIN competitions c ON c.id = m.competition_id
        JOIN events e ON e.id = c.event_id
        WHERE m.status = 'COMPLETED' AND m.winner_id IS NOT NULL
        ORDER BY m.round_number DESC, m.updated_at DESC
        LIMIT 4
        """
    ).fetchall()

    # Distribusi peserta per cabang untuk mini bar telemetry (seperti referensi)
    comp_bars = db.execute(
        """
        SELECT c.name, COUNT(r.id) AS cnt
        FROM competitions c
        LEFT JOIN registrations r ON r.competition_id = c.id AND r.status != 'Rejected'
        GROUP BY c.id
        ORDER BY cnt DESC, c.id ASC
        LIMIT 8
        """
    ).fetchall()

    return render_template(
        "index.html",
        events=events,
        total_participants=total_participants,
        total_competitions=total_competitions,
        live_matches=[dict(m) for m in live_matches],
        recent_winners=[dict(w) for w in recent_winners],
        comp_bars=[dict(b) for b in comp_bars],
    )


@public_bp.route("/events")
def events_page():
    """Halaman daftar seluruh event perlombaan sekolah."""
    db = get_db()
    events = get_all_events(db)
    for ev in events:
        ev["competitions"] = get_competitions_for_event(db, ev["id"])
    return render_template("events.html", events=events)


@public_bp.route("/events/<slug>")
def event_detail(slug):
    """Halaman detail satu event: jadwal, juknis, panitia, dan daftar cabang lomba."""
    db = get_db()
    event = get_event_by_slug(db, slug)
    if not event:
        abort(404)
    competitions = get_competitions_for_event(db, event["id"])
    return render_template("event_detail.html", event=event, competitions=competitions)


@public_bp.route("/register")
def register_page():
    """Halaman pendaftaran lomba (Individu & Tim) + Cek Status Pendaftaran."""
    db = get_db()
    events = get_all_events(db)
    for ev in events:
        ev["competitions"] = get_competitions_for_event(db, ev["id"])

    selected_event_id = request.args.get("event_id", type=int)
    selected_comp_id = request.args.get("competition_id", type=int)

    # Jika competition_id dipilih tapi event_id kosong, cari event induknya
    if selected_comp_id and not selected_event_id:
        row = db.execute(
            "SELECT event_id FROM competitions WHERE id = ?", (selected_comp_id,)
        ).fetchone()
        if row:
            selected_event_id = row["event_id"]

    return render_template(
        "register.html",
        events=events,
        selected_event_id=selected_event_id,
        selected_comp_id=selected_comp_id,
    )


@public_bp.route("/bracket")
def bracket_page():
    """Halaman tampilan Interactive Tournament Bracket untuk siswa."""
    db = get_db()
    competitions = get_all_competitions(db)
    comp_id = request.args.get("competition_id", type=int)

    # Default pilih cabang pertama yang sudah memiliki bracket
    if not comp_id and competitions:
        with_matches = [c for c in competitions if c["match_count"] > 0]
        comp_id = with_matches[0]["id"] if with_matches else competitions[0]["id"]

    bracket_data = get_bracket_data(db, comp_id) if comp_id else None
    return render_template(
        "bracket.html",
        competitions=competitions,
        selected_comp_id=comp_id,
        bracket=bracket_data,
    )


@public_bp.route("/info")
def info_page():
    """Halaman Informasi, Alur Pendaftaran, Jadwal Ringkas, Kontak Panitia & Cek Status."""
    db = get_db()
    events = get_all_events(db)
    settings = get_settings(db)
    q = request.args.get("q", "").strip()
    lookup_results = lookup_registrations(db, q) if q else []
    return render_template(
        "info.html",
        events=events,
        settings=settings,
        search_query=q,
        lookup_results=lookup_results,
    )
