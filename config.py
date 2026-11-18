"""
Konfigurasi utama aplikasi Lombaku.
Mendukung mode lokal (SQLite di folder data/) maupun deployment Vercel
(otomatis menggunakan direktori /tmp yang writable di serverless environment).
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

if IS_VERCEL:
    # Filesystem utama Vercel bersifat read-only; /tmp dapat ditulis untuk SQLite demo.
    DATA_DIR = os.environ.get("LOMBAKU_DATA_DIR", "/tmp/lombaku_data")
else:
    DATA_DIR = os.environ.get("LOMBAKU_DATA_DIR", os.path.join(BASE_DIR, "data"))

os.makedirs(DATA_DIR, exist_ok=True)


class Config:
    # Atur SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD di Environment Variables Vercel saat produksi.
    SECRET_KEY = os.environ.get("SECRET_KEY", "lombaku-liquid-glass-secret-key-2026")
    DATABASE_PATH = os.path.join(DATA_DIR, "lombaku.db")
    APP_NAME = "Lombaku"
    IS_VERCEL = IS_VERCEL
    DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
