"""
Routes halaman publik (Siswa & Pengunjung) untuk Lombaku.
Seluruh rendering halaman, perpindahan event, gerbang juknis, pendaftaran individu/tim,
cek status, dan tampilan bracket diproses langsung di Python (Flask + Jinja2).
"""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from database.db import get_db
from services.events import (
    get_all_events,
    get_event_by_slug,
    get_competitions_for_event,
    get_all_competitions,
    get_settings,
    parse_dt,
)
from services.bracket import get_bracket_data
from services.registration import create_registration, lookup_registrations

public_bp = Blueprint("public", __name__)


def _compute_countdown_parts(event_date_str: str) -> dict:
    """Menghitung sisa hari, jam, menit menuju event secara server-side dengan Python."""
    target = parse_dt(event_date_str)
    if not target:
        return {"days": 0, "hours": 0, "mins": 0, "secs": 0, "ring_offset": 140}
    diff = max(0, int((target - datetime.now()).total_seconds()))
    days = diff // 86400
    hours = (diff % 86400) // 3600
    mins = (diff % 3600) // 60
    secs = diff % 60
    pct = max(0.12, min(1.0, 1.0 - (days / 45.0)))
    circumference = 163.36  # 2 * pi * 26
    return {
        "days": days,
        "hours": hours,
        "mins": mins,
        "secs": secs,
        "ring_offset": round(circumference * (1.0 - pct), 2),
    }


@public_bp.route("/")
def home():
    """Halaman Beranda — Hero Experience server-rendered dengan Flask & Jinja2."""
    db = get_db()
    events = get_all_events(db)
    for ev in events:
        ev["competitions"] = get_competitions_for_event(db, ev["id"])

    # Pilih event aktif dari query ?event=<slug> (default: event featured pertama)
    requested_slug = (request.args.get("event") or "").strip()
    active_idx = 0
    if events:
        if requested_slug:
            for i, ev in enumerate(events):
                if ev["slug"] == requested_slug:
                    active_idx = i
                    break
        else:
            for i, ev in enumerate(events):
                if ev["is_featured"]:
                    active_idx = i
                    break

    active_event = events[active_idx] if events else None
    prev_event = events[(active_idx - 1) % len(events)] if events else None
    next_event = events[(active_idx + 1) % len(events)] if events else None
    countdown = _compute_countdown_parts(active_event["event_date"]) if active_event else _compute_countdown_parts("")

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
        active_event=active_event,
        active_idx=active_idx,
        prev_event=prev_event,
        next_event=next_event,
        countdown=countdown,
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


@public_bp.route("/register", methods=["GET", "POST"])
def register_page():
    """
    Halaman pendaftaran lomba (Individu & Tim) + Gerbang Wajib Baca Juknis + Cek Status.
    100% ditangani oleh Python Flask + Jinja2 tanpa memerlukan AJAX/JavaScript.
    """
    db = get_db()
    events = get_all_events(db)
    for ev in events:
        ev["competitions"] = get_competitions_for_event(db, ev["id"])

    # Tentukan event & cabang terpilih
    selected_event_id = request.values.get("event_id", type=int)
    selected_comp_id = request.values.get("competition_id", type=int)

    if selected_comp_id and not selected_event_id:
        row = db.execute("SELECT event_id FROM competitions WHERE id = ?", (selected_comp_id,)).fetchone()
        if row:
            selected_event_id = row["event_id"]

    if not selected_event_id and events:
        selected_event_id = events[0]["id"]

    active_event = next((e for e in events if e["id"] == selected_event_id), events[0] if events else None)
    event_comps = active_event["competitions"] if active_event else []

    active_comp = next((c for c in event_comps if c["id"] == selected_comp_id), None)
    if not active_comp and event_comps:
        active_comp = event_comps[0]
        selected_comp_id = active_comp["id"]

    # Cek status konfirmasi Juknis di session server-side Flask
    confirmed_set = set(session.get("juknis_confirmed_ids") or [])
    juknis_unlocked = bool(active_comp and active_comp["id"] in confirmed_set)

    # Tentukan tab aktif: juknis | form | status
    active_tab = (request.values.get("tab") or "juknis").strip().lower()
    if active_tab not in ("juknis", "form", "status"):
        active_tab = "juknis"

    # Proses submit formulir pendaftaran (POST)
    form_data = {}
    if request.method == "POST":
        comp_id_post = request.form.get("competition_id", type=int)
        is_confirmed = bool(comp_id_post and comp_id_post in confirmed_set)

        # Ambil daftar anggota tambahan (jika lomba tim)
        m_names = request.form.getlist("member_name[]")
        m_nises = request.form.getlist("member_nis[]")
        m_classes = request.form.getlist("member_kelas[]")
        members = []
        for idx in range(max(len(m_names), len(m_nises), len(m_classes))):
            nm = (m_names[idx] if idx < len(m_names) else "").strip()
            ns = (m_nises[idx] if idx < len(m_nises) else "").strip()
            kl = (m_classes[idx] if idx < len(m_classes) else "").strip()
            if nm or ns:
                members.append({"name": nm, "nis": ns, "kelas": kl})

        payload = {
            "competition_id": comp_id_post,
            "juknis_confirmed": is_confirmed,
            "participant_name": request.form.get("participant_name", ""),
            "nis": request.form.get("nis", ""),
            "kelas": request.form.get("kelas", ""),
            "contact": request.form.get("contact", ""),
            "team_name": request.form.get("team_name", ""),
            "notes": request.form.get("notes", ""),
            "members": members,
        }
        form_data = payload

        ok, result = create_registration(db, payload)
        if ok:
            session["last_receipt"] = result
            session["sound_cue"] = "submit"
            flash(f"Pendaftaran berhasil! Kode pendaftaran Anda: {result['registration_code']}", "success")
            return redirect(
                url_for(
                    "public.register_page",
                    event_id=active_event["id"] if active_event else "",
                    competition_id=comp_id_post,
                    tab="form",
                )
            )
        else:
            session["sound_cue"] = "error"
            flash(result, "error")
            active_tab = "form" if is_confirmed else "juknis"

    # Jika pengguna mencoba langsung ke tab form tanpa membaca Juknis, arahkan kembali ke Juknis
    if active_tab == "form" and not juknis_unlocked:
        flash("Buka dan setujui Tab Juknis terlebih dahulu sebelum mengisi formulir pendaftaran.", "warning")
        active_tab = "juknis"

    # Ambil bukti pendaftaran terakhir (jika baru saja sukses mendaftar)
    last_receipt = session.pop("last_receipt", None)

    # Pencarian status pendaftaran (tab status)
    search_q = (request.args.get("q") or "").strip()
    lookup_results = lookup_registrations(db, search_q) if search_q else []

    # Jumlah baris anggota tambahan untuk tim (min_members - 1 wajib, sampai max_members - 1 opsional)
    required_extra_members = max(0, (active_comp["min_members"] - 1)) if active_comp and active_comp["comp_type"] == "TEAM" else 0
    max_extra_members = max(0, (active_comp["max_members"] - 1)) if active_comp and active_comp["comp_type"] == "TEAM" else 0

    return render_template(
        "register.html",
        events=events,
        active_event=active_event,
        event_comps=event_comps,
        active_comp=active_comp,
        active_tab=active_tab,
        juknis_unlocked=juknis_unlocked,
        required_extra_members=required_extra_members,
        max_extra_members=max_extra_members,
        form_data=form_data,
        last_receipt=last_receipt,
        search_q=search_q,
        lookup_results=lookup_results,
    )


@public_bp.route("/register/confirm-juknis", methods=["POST"])
def confirm_juknis():
    """Menyimpan konfirmasi baca Juknis di session Flask dan membuka Tab Formulir."""
    event_id = request.form.get("event_id", type=int)
    comp_id = request.form.get("competition_id", type=int)
    if comp_id:
        confirmed = list(set(session.get("juknis_confirmed_ids") or []))
        if comp_id not in confirmed:
            confirmed.append(comp_id)
        session["juknis_confirmed_ids"] = confirmed
        session["sound_cue"] = "open"
        flash("Juknis terkonfirmasi! Formulir pendaftaran kini terbuka.", "success")
    return redirect(url_for("public.register_page", event_id=event_id, competition_id=comp_id, tab="form"))


@public_bp.route("/bracket")
def bracket_page():
    """Halaman tampilan Interactive Tournament Bracket server-rendered dengan Jinja2."""
    db = get_db()
    competitions = get_all_competitions(db)
    comp_id = request.args.get("competition_id", type=int)

    if not comp_id and competitions:
        with_matches = [c for c in competitions if c["match_count"] > 0]
        comp_id = with_matches[0]["id"] if with_matches else competitions[0]["id"]

    bracket_data = get_bracket_data(db, comp_id) if comp_id else None
    active_round = request.args.get("round", type=int) or 1
    view_mode = (request.args.get("view") or "tabs").strip().lower()

    return render_template(
        "bracket.html",
        competitions=competitions,
        selected_comp_id=comp_id,
        bracket=bracket_data,
        active_round=active_round,
        view_mode=view_mode,
        is_admin_bracket=False,
        shuffled=False,
        highlight_round=None,
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
