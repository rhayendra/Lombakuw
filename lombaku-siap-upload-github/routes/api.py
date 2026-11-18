"""
Routes JSON API untuk interaksi dinamis (AJAX) Lombaku:
pendaftaran real-time, cek status NIS, kontrol status event,
kelola status peserta, serta kontrol bracket (shuffle, lock, skor, pemenang).
"""
from flask import Blueprint, jsonify, request
from database.db import get_db
from services.auth import admin_api_required
from services.events import compute_effective_status
from services.registration import create_registration, lookup_registrations
from services.bracket import build_bracket, update_match, toggle_bracket_lock, get_bracket_data

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ------------------------------------------------------------------
# PUBLIC APIs (Siswa)
# ------------------------------------------------------------------
@api_bp.route("/competition/<int:comp_id>", methods=["GET"])
def api_competition_detail(comp_id):
    """Mengembalikan aturan lengkap cabang lomba & status efektif event untuk form registrasi."""
    db = get_db()
    comp = db.execute("SELECT * FROM competitions WHERE id = ?", (comp_id,)).fetchone()
    if not comp:
        return jsonify({"ok": False, "error": "Cabang lomba tidak ditemukan."}), 404

    event = db.execute("SELECT * FROM events WHERE id = ?", (comp["event_id"],)).fetchone()
    status_info = compute_effective_status(event)
    registered_count = db.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE competition_id = ? AND status != 'Rejected'",
        (comp_id,),
    ).fetchone()["c"]

    data = dict(comp)
    data["event_name"] = event["name"]
    data["event_juknis"] = event["juknis"]
    data["event_effective_status"] = status_info["effective_status"]
    data["can_register"] = status_info["can_register"]
    data["status_reason"] = status_info["status_reason"]
    data["registered_count"] = registered_count
    return jsonify({"ok": True, "competition": data})


@api_bp.route("/register", methods=["POST"])
def api_register():
    """Memproses pendaftaran lomba (Individu / Tim) dengan validasi backend penuh."""
    payload = request.get_json(silent=True) or {}
    db = get_db()
    ok, result = create_registration(db, payload)
    if not ok:
        return jsonify({"ok": False, "error": result}), 400
    return jsonify({"ok": True, "registration": result}), 201


@api_bp.route("/registration/status", methods=["GET"])
def api_registration_status():
    """Mencari status pendaftaran siswa berdasarkan NIS atau Kode Daftar."""
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "Masukkan NIS atau Kode Pendaftaran."}), 400
    db = get_db()
    results = lookup_registrations(db, q)
    return jsonify({"ok": True, "results": results})


@api_bp.route("/bracket/<int:comp_id>", methods=["GET"])
def api_get_bracket(comp_id):
    """Mengambil data bracket terbaru dalam format JSON."""
    db = get_db()
    data = get_bracket_data(db, comp_id)
    if not data:
        return jsonify({"ok": False, "error": "Cabang lomba tidak ditemukan."}), 404
    return jsonify({"ok": True, "bracket": data})


# ------------------------------------------------------------------
# ADMIN APIs (Dilindungi @admin_api_required)
# ------------------------------------------------------------------
@api_bp.route("/admin/event/<int:event_id>/status", methods=["POST"])
@admin_api_required
def api_admin_event_status(event_id):
    """Mengubah status event secara cepat (OPEN / ONGOING / LOCKED / COMPLETED / CLOSED)."""
    payload = request.get_json(silent=True) or {}
    new_status = (payload.get("status") or "").upper()
    if new_status not in ("OPEN", "ONGOING", "LOCKED", "COMPLETED", "CLOSED"):
        return jsonify({"ok": False, "error": "Status tidak valid."}), 400

    db = get_db()
    ev = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not ev:
        return jsonify({"ok": False, "error": "Event tidak ditemukan."}), 404

    db.execute("UPDATE events SET status = ? WHERE id = ?", (new_status, event_id))
    db.commit()
    updated = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    status_info = compute_effective_status(updated)
    return jsonify({"ok": True, "event_id": event_id, "status_info": status_info})


@api_bp.route("/admin/participant/<int:reg_id>/status", methods=["POST"])
@admin_api_required
def api_admin_participant_status(reg_id):
    """Memperbarui status pendaftaran peserta (Registered/Pending/Accepted/Rejected)."""
    payload = request.get_json(silent=True) or {}
    new_status = (payload.get("status") or "").strip()
    if new_status not in ("Registered", "Pending", "Accepted", "Rejected"):
        return jsonify({"ok": False, "error": "Status pendaftaran tidak valid."}), 400

    db = get_db()
    row = db.execute("SELECT id FROM registrations WHERE id = ?", (reg_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Peserta tidak ditemukan."}), 404

    db.execute("UPDATE registrations SET status = ? WHERE id = ?", (new_status, reg_id))
    db.commit()
    return jsonify({"ok": True, "id": reg_id, "status": new_status})


@api_bp.route("/admin/participant/<int:reg_id>", methods=["DELETE"])
@admin_api_required
def api_admin_delete_participant(reg_id):
    """Menghapus data peserta dari database."""
    db = get_db()
    row = db.execute("SELECT id FROM registrations WHERE id = ?", (reg_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "Peserta tidak ditemukan."}), 404
    db.execute("DELETE FROM registrations WHERE id = ?", (reg_id,))
    db.commit()
    return jsonify({"ok": True, "deleted_id": reg_id})


@api_bp.route("/admin/bracket/<int:comp_id>/generate", methods=["POST"])
@admin_api_required
def api_admin_bracket_generate(comp_id):
    """Membuat bracket otomatis berdasarkan peserta terdaftar."""
    db = get_db()
    ok, res = build_bracket(db, comp_id, shuffle=False)
    if not ok:
        return jsonify({"ok": False, "error": res}), 400
    return jsonify({"ok": True, "bracket": res, "message": "Bracket berhasil dibuat."})


@api_bp.route("/admin/bracket/<int:comp_id>/shuffle", methods=["POST"])
@admin_api_required
def api_admin_bracket_shuffle(comp_id):
    """Mengacak posisi peserta di bracket secara random dan menyimpan ke database."""
    db = get_db()
    ok, res = build_bracket(db, comp_id, shuffle=True)
    if not ok:
        return jsonify({"ok": False, "error": res}), 400
    return jsonify({"ok": True, "bracket": res, "message": "Bracket berhasil diacak!"})


@api_bp.route("/admin/bracket/<int:comp_id>/lock", methods=["POST"])
@admin_api_required
def api_admin_bracket_lock(comp_id):
    """Mengunci atau membuka kunci bracket."""
    db = get_db()
    ok, res = toggle_bracket_lock(db, comp_id)
    if not ok:
        return jsonify({"ok": False, "error": res}), 400
    msg = "Bracket berhasil dikunci." if res["bracket_locked"] else "Kunci bracket dibuka."
    return jsonify({"ok": True, "bracket_locked": res["bracket_locked"], "message": msg})


@api_bp.route("/admin/match/<int:match_id>/update", methods=["POST"])
@admin_api_required
def api_admin_match_update(match_id):
    """Memperbarui skor, status, dan/atau menentukan pemenang pertandingan."""
    payload = request.get_json(silent=True) or {}
    db = get_db()
    ok, res = update_match(
        db,
        match_id,
        score1=payload.get("score1"),
        score2=payload.get("score2"),
        status=payload.get("status"),
        winner_slot=payload.get("winner_slot"),
        scheduled_time=payload.get("scheduled_time"),
    )
    if not ok:
        return jsonify({"ok": False, "error": res}), 400
    return jsonify({"ok": True, **res})
