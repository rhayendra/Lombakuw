"""
Routes halaman khusus Panitia / Admin Lombaku.
Dilindungi oleh autentikasi password hash dan decorator @admin_required.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from database.db import get_db
from database.seed import seed_demo_data
from services.auth import (
    verify_password,
    hash_password,
    login_admin,
    logout_admin,
    is_admin_logged_in,
    admin_required,
)
from services.events import (
    get_all_events,
    get_all_competitions,
    get_competitions_for_event,
    get_settings,
)
from services.registration import get_participants
from services.bracket import get_bracket_data
from services.exporter import export_registrations_excel

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """Halaman login aman khusus panitia."""
    if is_admin_logged_in():
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        db = get_db()
        admin = db.execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()
        if admin and verify_password(admin["password_hash"], password):
            login_admin(admin)
            flash(f"Selamat datang kembali, {admin['full_name']}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/admin"):
                return redirect(next_url)
            return redirect(url_for("admin.dashboard"))
        flash("Username atau password panitia salah.", "error")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    """Keluar dari sesi panitia."""
    logout_admin()
    flash("Anda telah keluar dari mode panitia.", "info")
    return redirect(url_for("public.home"))


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """Dashboard utama panitia dengan statistik lengkap dan kontrol cepat."""
    db = get_db()
    events = get_all_events(db)
    stats = {
        "total_events": len(events),
        "open_events": sum(1 for e in events if e["effective_status"] in ("OPEN", "ONGOING")),
        "total_competitions": db.execute("SELECT COUNT(*) AS c FROM competitions").fetchone()["c"],
        "total_registrations": db.execute("SELECT COUNT(*) AS c FROM registrations").fetchone()["c"],
        "accepted_registrations": db.execute(
            "SELECT COUNT(*) AS c FROM registrations WHERE status = 'Accepted'"
        ).fetchone()["c"],
        "pending_registrations": db.execute(
            "SELECT COUNT(*) AS c FROM registrations WHERE status IN ('Registered', 'Pending')"
        ).fetchone()["c"],
        "live_matches": db.execute(
            "SELECT COUNT(*) AS c FROM matches WHERE status = 'LIVE'"
        ).fetchone()["c"],
        "completed_matches": db.execute(
            "SELECT COUNT(*) AS c FROM matches WHERE status = 'COMPLETED'"
        ).fetchone()["c"],
    }

    recent_registrations = get_participants(db)[:8]
    live_matches = db.execute(
        """
        SELECT m.*, c.name AS competition_name, c.id AS comp_id, e.name AS event_name
        FROM matches m
        JOIN competitions c ON c.id = m.competition_id
        JOIN events e ON e.id = c.event_id
        WHERE m.status = 'LIVE'
        ORDER BY m.updated_at DESC
        """
    ).fetchall()

    return render_template(
        "admin/dashboard.html",
        events=events,
        stats=stats,
        recent_registrations=recent_registrations,
        live_matches=[dict(m) for m in live_matches],
    )


@admin_bp.route("/events", methods=["GET"])
@admin_required
def manage_events():
    """Halaman manajemen Event & Cabang Lomba (edit event, tambah/edit/hapus cabang)."""
    db = get_db()
    events = get_all_events(db)
    for ev in events:
        ev["competitions"] = get_competitions_for_event(db, ev["id"])
    return render_template("admin/events.html", events=events)


@admin_bp.route("/events/<int:event_id>/update", methods=["POST"])
@admin_required
def update_event(event_id):
    """Menyimpan perubahan informasi, jadwal, juknis, dan status event."""
    db = get_db()
    name = (request.form.get("name") or "").strip()
    subtitle = (request.form.get("subtitle") or "").strip()
    description = (request.form.get("description") or "").strip()
    event_date = (request.form.get("event_date") or "").strip()
    reg_open = (request.form.get("registration_open") or "").strip()
    reg_deadline = (request.form.get("registration_deadline") or "").strip()
    schedule_text = (request.form.get("schedule_text") or "").strip()
    juknis = (request.form.get("juknis") or "").strip()
    committee_info = (request.form.get("committee_info") or "").strip()
    status = (request.form.get("status") or "OPEN").upper()

    if not name or not event_date:
        flash("Nama event dan tanggal pelaksanaan wajib diisi.", "error")
        return redirect(url_for("admin.manage_events"))

    db.execute(
        """
        UPDATE events
        SET name = ?, subtitle = ?, description = ?, event_date = ?,
            registration_open = ?, registration_deadline = ?,
            schedule_text = ?, juknis = ?, committee_info = ?, status = ?
        WHERE id = ?
        """,
        (
            name, subtitle, description, event_date,
            reg_open, reg_deadline, schedule_text, juknis, committee_info, status, event_id
        ),
    )
    db.commit()
    flash(f"Event '{name}' berhasil diperbarui.", "success")
    return redirect(url_for("admin.manage_events"))


@admin_bp.route("/competitions/create", methods=["POST"])
@admin_required
def create_competition():
    """Menambahkan cabang lomba baru ke dalam sebuah event."""
    db = get_db()
    event_id = request.form.get("event_id", type=int)
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "Umum").strip()
    description = (request.form.get("description") or "").strip()
    comp_type = (request.form.get("comp_type") or "INDIVIDUAL").upper()
    min_members = 1 if comp_type == "INDIVIDUAL" else max(2, request.form.get("min_members", type=int) or 2)
    max_members = 1 if comp_type == "INDIVIDUAL" else max(min_members, request.form.get("max_members", type=int) or min_members)
    same_class = 1 if (comp_type == "TEAM" and request.form.get("same_class_required")) else 0
    max_slots = max(2, request.form.get("max_slots", type=int) or 16)
    requirements = (request.form.get("requirements") or "").strip()
    juknis = (request.form.get("juknis") or "").strip()
    schedule_info = (request.form.get("schedule_info") or "").strip()
    venue = (request.form.get("venue") or "").strip()

    if not event_id or not name:
        flash("Event dan nama cabang lomba wajib diisi.", "error")
        return redirect(url_for("admin.manage_events"))

    db.execute(
        """
        INSERT INTO competitions
            (event_id, name, category, description, comp_type, min_members, max_members,
             same_class_required, max_slots, requirements, juknis, schedule_info, venue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id, name, category, description, comp_type, min_members, max_members,
            same_class, max_slots, requirements, juknis, schedule_info, venue
        ),
    )
    db.commit()
    flash(f"Cabang lomba '{name}' berhasil ditambahkan.", "success")
    return redirect(url_for("admin.manage_events"))


@admin_bp.route("/competitions/<int:comp_id>/update", methods=["POST"])
@admin_required
def update_competition(comp_id):
    """Mengedit detail dan aturan cabang lomba."""
    db = get_db()
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "Umum").strip()
    description = (request.form.get("description") or "").strip()
    comp_type = (request.form.get("comp_type") or "INDIVIDUAL").upper()
    min_members = 1 if comp_type == "INDIVIDUAL" else max(2, request.form.get("min_members", type=int) or 2)
    max_members = 1 if comp_type == "INDIVIDUAL" else max(min_members, request.form.get("max_members", type=int) or min_members)
    same_class = 1 if (comp_type == "TEAM" and request.form.get("same_class_required")) else 0
    max_slots = max(2, request.form.get("max_slots", type=int) or 16)
    requirements = (request.form.get("requirements") or "").strip()
    juknis = (request.form.get("juknis") or "").strip()
    schedule_info = (request.form.get("schedule_info") or "").strip()
    venue = (request.form.get("venue") or "").strip()

    db.execute(
        """
        UPDATE competitions
        SET name = ?, category = ?, description = ?, comp_type = ?,
            min_members = ?, max_members = ?, same_class_required = ?, max_slots = ?,
            requirements = ?, juknis = ?, schedule_info = ?, venue = ?
        WHERE id = ?
        """,
        (
            name, category, description, comp_type, min_members, max_members,
            same_class, max_slots, requirements, juknis, schedule_info, venue, comp_id
        ),
    )
    db.commit()
    flash(f"Cabang lomba '{name}' berhasil diperbarui.", "success")
    return redirect(url_for("admin.manage_events"))


@admin_bp.route("/competitions/<int:comp_id>/delete", methods=["POST"])
@admin_required
def delete_competition(comp_id):
    """Menghapus cabang lomba beserta pendaftaran & bracket terkait."""
    db = get_db()
    comp = db.execute("SELECT name FROM competitions WHERE id = ?", (comp_id,)).fetchone()
    if comp:
        db.execute("DELETE FROM competitions WHERE id = ?", (comp_id,))
        db.commit()
        flash(f"Cabang lomba '{comp['name']}' telah dihapus.", "info")
    return redirect(url_for("admin.manage_events"))


@admin_bp.route("/participants")
@admin_required
def participants():
    """Halaman manajemen peserta individu & tim dengan filter lengkap."""
    db = get_db()
    event_id = request.args.get("event_id", type=int)
    competition_id = request.args.get("competition_id", type=int)
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()

    events = get_all_events(db)
    competitions = get_all_competitions(db)
    items = get_participants(
        db,
        event_id=event_id,
        competition_id=competition_id,
        status=status or None,
        search=search or None,
    )

    return render_template(
        "admin/participants.html",
        events=events,
        competitions=competitions,
        participants=items,
        filters={
            "event_id": event_id,
            "competition_id": competition_id,
            "status": status,
            "search": search,
        },
    )


@admin_bp.route("/bracket")
@admin_required
def bracket_control():
    """Halaman kontrol bracket panitia: Generate, Shuffle, Lock, Skor & Pemenang."""
    db = get_db()
    competitions = get_all_competitions(db)
    comp_id = request.args.get("competition_id", type=int)
    if not comp_id and competitions:
        with_matches = [c for c in competitions if c["match_count"] > 0]
        comp_id = with_matches[0]["id"] if with_matches else competitions[0]["id"]

    bracket_data = get_bracket_data(db, comp_id) if comp_id else None
    return render_template(
        "admin/bracket.html",
        competitions=competitions,
        selected_comp_id=comp_id,
        bracket=bracket_data,
    )


@admin_bp.route("/export")
@admin_required
def export_page():
    """Halaman pusat ekspor data pendaftaran ke Excel (.xlsx)."""
    db = get_db()
    events = get_all_events(db)
    competitions = get_all_competitions(db)
    total_all = db.execute("SELECT COUNT(*) AS c FROM registrations").fetchone()["c"]
    return render_template(
        "admin/export.html",
        events=events,
        competitions=competitions,
        total_all=total_all,
    )


@admin_bp.route("/export/download")
@admin_required
def export_download():
    """Endpoint download file Excel (.xlsx) sesuai scope yang dipilih."""
    db = get_db()
    event_id = request.args.get("event_id", type=int)
    competition_id = request.args.get("competition_id", type=int)

    output, filename = export_registrations_excel(
        db, event_id=event_id, competition_id=competition_id
    )
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings_page():
    """Pengaturan sekolah, pengumuman, ubah password admin, dan reset data demo."""
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_settings":
            for key in ("school_name", "school_tagline", "committee_contact", "announcement"):
                val = (request.form.get(key) or "").strip()
                db.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, val),
                )
            db.commit()
            flash("Pengaturan sekolah berhasil disimpan.", "success")
        elif action == "change_password":
            from flask import session
            old_pw = request.form.get("old_password") or ""
            new_pw = request.form.get("new_password") or ""
            confirm_pw = request.form.get("confirm_password") or ""
            admin = db.execute(
                "SELECT * FROM admins WHERE id = ?", (session["admin_id"],)
            ).fetchone()
            if not verify_password(admin["password_hash"], old_pw):
                flash("Password lama tidak sesuai.", "error")
            elif len(new_pw) < 6:
                flash("Password baru minimal 6 karakter.", "error")
            elif new_pw != confirm_pw:
                flash("Konfirmasi password baru tidak cocok.", "error")
            else:
                db.execute(
                    "UPDATE admins SET password_hash = ? WHERE id = ?",
                    (hash_password(new_pw), admin["id"]),
                )
                db.commit()
                flash("Password panitia berhasil diperbarui.", "success")
        elif action == "reset_demo":
            seed_demo_data(force_reset=True)
            flash("Data demo presentasi berhasil dipulihkan ke kondisi awal.", "success")

        return redirect(url_for("admin.settings_page"))

    settings = get_settings(db)
    return render_template("admin/settings.html", settings=settings)
