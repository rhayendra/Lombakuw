"""
Layanan autentikasi panitia/admin Lombaku.
Menggunakan password hash Werkzeug (PBKDF2/scrypt) dan Flask session.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(plain_password: str) -> str:
    """Membuat hash password yang aman untuk disimpan di database."""
    return generate_password_hash(plain_password)


def verify_password(password_hash: str, plain_password: str) -> bool:
    """Memverifikasi password polos terhadap hash di database."""
    return check_password_hash(password_hash, plain_password)


def login_admin(admin_row):
    """Menyimpan informasi login admin ke session Flask."""
    session.clear()
    session["admin_id"] = admin_row["id"]
    session["admin_username"] = admin_row["username"]
    session["admin_name"] = admin_row["full_name"]


def logout_admin():
    """Menghapus session admin saat logout."""
    session.clear()


def is_admin_logged_in() -> bool:
    """Mengecek apakah pengguna saat ini adalah admin yang sudah login."""
    return bool(session.get("admin_id"))


def admin_required(view_func):
    """Decorator untuk melindungi halaman HTML khusus admin."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_admin_logged_in():
            flash("Silakan login sebagai panitia untuk mengakses halaman ini.", "warning")
            return redirect(url_for("admin.login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


def admin_api_required(view_func):
    """Decorator untuk melindungi endpoint JSON API khusus admin."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_admin_logged_in():
            return jsonify({"ok": False, "error": "Akses ditolak. Login panitia diperlukan."}), 401
        return view_func(*args, **kwargs)
    return wrapped
