"""
Titik masuk utama (Entry Point) aplikasi web Lombaku.
Menjalankan server Flask, menginisialisasi database SQLite,
mengisi data demo otomatis jika masih kosong, dan mendaftarkan seluruh blueprint.
"""
import os
from flask import Flask, render_template, session
from config import Config
from database.db import init_db, close_db, get_db
from database.seed import seed_demo_data
from routes.public import public_bp
from routes.admin import admin_bp
from routes.api import api_bp
from services.events import get_settings


def ensure_database_ready():
    """Memastikan database & data demo siap (baik SQLite lokal maupun Supabase PostgreSQL)."""
    if Config.USE_POSTGRES:
        init_db()
        seed_demo_data(force_reset=False)
        return
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    if not os.path.exists(Config.DATABASE_PATH):
        init_db()
        seed_demo_data(force_reset=False)


def create_app() -> Flask:
    """Factory function untuk membuat dan mengonfigurasi instance Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inisialisasi skema database & data demo presentasi saat startup
    init_db()
    seed_demo_data(force_reset=False)

    @app.before_request
    def _check_db_on_request():
        if not Config.USE_POSTGRES and not os.path.exists(Config.DATABASE_PATH):
            ensure_database_ready()

    # Tutup koneksi database otomatis setiap request berakhir
    app.teardown_appcontext(close_db)

    # Daftarkan seluruh Blueprint (Public, Admin, API)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Variabel global yang tersedia di semua template HTML
    @app.context_processor
    def inject_globals():
        db = get_db()
        settings = get_settings(db)
        live_count = db.execute(
            "SELECT COUNT(*) AS c FROM matches WHERE status = 'LIVE'"
        ).fetchone()["c"]
        return {
            "app_name": Config.APP_NAME,
            "is_admin": bool(session.get("admin_id")),
            "admin_name": session.get("admin_name", ""),
            "school_settings": settings,
            "global_live_count": live_count,
            "sound_cue": session.pop("sound_cue", ""),
            "celebrate_mode": session.pop("celebrate_mode", ""),
        }

    # Penanganan halaman error yang elegan
    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, title="Halaman Tidak Ditemukan", message="Halaman atau event yang Anda cari tidak tersedia."), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("error.html", code=500, title="Terjadi Kesalahan Sistem", message="Mohon maaf, terjadi gangguan tak terduga. Silakan muat ulang halaman."), 500

    return app


app = create_app()

if __name__ == "__main__":
    print("=" * 56)
    print("  LOMBAKU — Liquid Glass School Competition Platform")
    print("  Buka di browser : http://127.0.0.1:5000")
    print("  Login Panitia   : http://127.0.0.1:5000/admin/login")
    print("  Akun Default    : admin / admin123")
    print("=" * 56)
    app.run(host="127.0.0.1", port=5000, debug=True)
