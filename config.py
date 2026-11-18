"""
Konfigurasi utama aplikasi Lombaku.
Mendukung 2 mode database secara otomatis:
1. Supabase / PostgreSQL (permanen di cloud — aktif otomatis saat DATABASE_URL / POSTGRES_URL diisi di Vercel).
2. SQLite lokal (otomatis digunakan saat dijalankan di komputer lokal tanpa DATABASE_URL).
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

# Mendukung variabel standar Supabase maupun integrasi Vercel Marketplace
_raw_db_url = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_PRISMA_URL")
    or os.environ.get("SUPABASE_DB_URL")
    or ""
).strip()

# Normalisasi prefix postgres:// -> postgresql:// untuk psycopg2
if _raw_db_url.startswith("postgres://"):
    _raw_db_url = "postgresql://" + _raw_db_url[len("postgres://"):]

USE_POSTGRES = _raw_db_url.startswith("postgresql://")

if IS_VERCEL:
    DATA_DIR = os.environ.get("LOMBAKU_DATA_DIR", "/tmp/lombaku_data")
else:
    DATA_DIR = os.environ.get("LOMBAKU_DATA_DIR", os.path.join(BASE_DIR, "data"))

if not USE_POSTGRES:
    os.makedirs(DATA_DIR, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "lombaku-liquid-glass-secret-key-2026")
    DATABASE_URL = _raw_db_url
    USE_POSTGRES = USE_POSTGRES
    DATABASE_PATH = os.path.join(DATA_DIR, "lombaku.db")
    APP_NAME = "Lombaku"
    IS_VERCEL = IS_VERCEL
    DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
