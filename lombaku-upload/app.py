"""
====================================================================
FILE: app.py
APLIKASI: LombaKu — Portal Kompetisi & Paspor Lomba Siswa
BAHASA: Python 3 + SQLite (sqlite3 Standard Library)
DESKRIPSI:
Server utama aplikasi LombaKu yang menghubungkan database SQLite
(`database_lombaku.py`) dan logika bisnis (`logika_lombaku.py`)
dengan halaman browser.
====================================================================
"""

import os
import json
import secrets
from datetime import datetime
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    send_from_directory,
    session,
)

from database_lombaku import (
    buka_koneksi,
    inisialisasi_database,
    LOKASI_DB,
)
from logika_lombaku import (
    bersihkan_teks,
    ambil_semua_data_lombaku,
    cek_paspor_siswa,
    acak_bagan_lomba,
    majukan_pemenang_bagan,
    buat_file_excel_lombaku,
)

FOLDER_DASAR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(FOLDER_DASAR, "templates"),
    static_folder=os.path.join(FOLDER_DASAR, "static"),
    static_url_path="/static",
)

app.secret_key = os.environ.get("LOMBAKU_SECRET") or "kunci-rahasia-lombaku-sqlite-2026"
app.config.update(
    SESSION_COOKIE_NAME="sesi_lombaku",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
)

# Jalankan pembuatan tabel SQLite & pengisian data awal saat aplikasi aktif
inisialisasi_database()


def wajib_login_panitia(fungsi):
    """Decorator untuk memastikan hanya panitia yang sudah login yang bisa mengakses fitur admin."""
    @wraps(fungsi)
    def pembungkus(*args, **kwargs):
        if not session.get("admin_lombaku"):
            return jsonify({
                "success": False,
                "message": "Sesi panitia belum aktif. Silakan masuk sebagai Panitia terlebih dahulu."
            }), 401
        return fungsi(*args, **kwargs)
    return pembungkus


# ====================================================================
# 1. ROUTE HALAMAN UTAMA (EXPLORE, EVENT, JADWAL, PROFIL PASPOR SISWA)
# ====================================================================

@app.route("/static/<path:filename>")
def file_statis(filename):
    return send_from_directory(os.path.join(FOLDER_DASAR, "static"), filename)


@app.route("/public/<path:filename>")
def file_publik(filename):
    return send_from_directory(os.path.join(FOLDER_DASAR, "public"), filename)


@app.route("/")
def halaman_explore():
    """Halaman Utama (Explore Lomba, Rekomendasi, Jadwal & Bagan)."""
    return render_template("index.html")


@app.route("/event")
@app.route("/daftar")
def halaman_event():
    """Halaman Khusus Event, Kriteria Penilaian, Persyaratan & Pendaftaran."""
    return render_template("daftar.html")


@app.route("/profil")
@app.route("/peserta")
def halaman_profil_siswa():
    """Halaman Dashboard Pengguna & Paspor Kompetisi Siswa Berbasis NIS."""
    return render_template("peserta.html")


# ====================================================================
# 2. API PUBLIK & PENCARIAN PASPOR NIS SISWA
# ====================================================================

@app.route("/api/lombaku/data")
@app.route("/api/public-data")
@app.route("/api/bootstrap")
def api_ambil_data():
    """Mengirimkan seluruh data Event, Cabang Lomba, Kuota, dan Aktivitas Terbaru dari SQLite."""
    semua = ambil_semua_data_lombaku()
    peserta = semua.get("participants", [])

    # 5 aktivitas pendaftaran terbaru untuk ditampilkan pada bagian Ulasan/Aktivitas
    terbaru = list(reversed(peserta[-5:]))

    return jsonify({
        "events": semua["events"],
        "competitions": semua["competitions"],
        "participantCount": len(peserta),
        "recentParticipants": terbaru,
        "serverTime": datetime.now().strftime("%d %b %Y • %H:%M WIB"),
    })


@app.route("/api/lombaku/cek-nis")
@app.route("/api/registrations/check")
def api_cek_nis_siswa():
    """Mencari status pendaftaran siswa berdasarkan NIS/NISN, Kode Tiket, atau Nama."""
    kata_kunci = (request.args.get("nis") or request.args.get("q") or "").strip()
    if not kata_kunci:
        return jsonify({
            "success": False,
            "message": "Masukkan NIS/NISN, Nama, atau Kode Tiket untuk mencari."
        }), 400

    semua = ambil_semua_data_lombaku()
    hasil = cek_paspor_siswa(kata_kunci, semua)
    return jsonify({
        "success": True,
        "nis": kata_kunci,
        "registrations": hasil,
    })


# ====================================================================
# 3. API PENDAFTARAN LOMBA (BERBASIS NIS & KUOTA CABANG)
# ====================================================================

@app.route("/api/lombaku/daftar", methods=["POST"])
@app.route("/api/register", methods=["POST"])
def api_daftar_lomba():
    """
    Menyimpan pendaftaran siswa baru ke tabel SQLite `tb_pendaftaran`.
    Menerapkan aturan:
    - Wajib sudah membuka/membaca Persyaratan & Kriteria (Mandatory Juknis View).
    - Event & cabang lomba berstatus terbuka dan kuota masih tersedia.
    - 1 NIS siswa hanya boleh mendaftar 1 cabang pada setiap event utama (Single Registration).
    - Jika cabang beregu/tim, wajib mengisi Nama Tim dan memenuhi syarat minimal anggota.
    """
    data_input = request.get_json() or {}
    id_event = (data_input.get("eventId") or "").strip()
    id_lomba = (data_input.get("competitionId") or "").strip()
    nama_siswa = (data_input.get("nama") or data_input.get("studentName") or "").strip()
    nis = (data_input.get("nis") or "").strip()
    kelas = (data_input.get("kelas") or "").strip()
    no_wa = (data_input.get("kontak") or data_input.get("phone") or "").strip()
    nama_tim = (data_input.get("namaKelompok") or data_input.get("teamName") or "").strip()
    anggota_list = data_input.get("anggotaList") or []
    anggota_list = [str(a).strip() for a in anggota_list if str(a).strip()]
    sudah_baca = bool(data_input.get("juknisViewed"))

    # Jika NIS tidak dikirim dari form cepat, buat kode identitas siswa dari nama+kelas
    if not nis:
        nis = f"SIS-{secrets.randbelow(90000) + 10000}"

    if not sudah_baca:
        return jsonify({
            "success": False,
            "message": "Wajib membuka dan membaca tab Persyaratan & Kriteria Lomba terlebih dahulu!"
        }), 400

    if not nama_siswa or not kelas or not id_event or not id_lomba:
        return jsonify({
            "success": False,
            "message": "Mohon lengkapi Nama Siswa, NIS, Kelas, dan pilihan Lomba."
        }), 400

    semua = ambil_semua_data_lombaku()
    ev = next((e for e in semua["events"] if e["id"] == id_event), None)
    if not ev:
        return jsonify({"success": False, "message": "Event tidak ditemukan."}), 404

    if ev.get("effectiveLocked"):
        return jsonify({
            "success": False,
            "message": f"Pendaftaran event {ev['name']} sedang terkunci ({ev.get('lockReason')})."
        }), 400

    comp = next((c for c in ev.get("competitions", []) if c["id"] == id_lomba), None)
    if not comp:
        return jsonify({"success": False, "message": "Cabang perlombaan tidak ditemukan."}), 404

    if comp.get("locked"):
        return jsonify({
            "success": False,
            "message": f"Cabang lomba {comp['name']} sedang ditutup oleh panitia."
        }), 400

    if comp.get("isQuotaFull"):
        return jsonify({
            "success": False,
            "message": f"Kuota cabang {comp['name']} sudah penuh ({comp['quota']}/{comp['quota']})."
        }), 400

    # Validasi Lomba Tim / Beregu
    if comp.get("isGroup"):
        if not nama_tim:
            return jsonify({
                "success": False,
                "message": f"Cabang '{comp['name']}' adalah lomba beregu. Wajib mengisi Nama Tim / Regu Kelas!"
            }), 400
        total_orang = 1 + len(anggota_list)
        min_orang = int(comp.get("minMembers", 2))
        if total_orang < min_orang:
            return jsonify({
                "success": False,
                "message": (
                    f"Cabang '{comp['name']}' membutuhkan minimal {min_orang} pendaftar dalam 1 tim. "
                    f"Saat ini baru tercatat {total_orang} orang (Perwakilan + {len(anggota_list)} anggota)."
                )
            }), 400

    # Pemeriksaan Single Registration per Event (berdasarkan NIS atau Nama+Kelas)
    nis_bersih = bersihkan_teks(nis)
    nama_bersih = bersihkan_teks(nama_siswa)
    kelas_bersih = bersihkan_teks(kelas)

    for p in semua.get("participants", []):
        if p["eventId"] != id_event:
            continue
        sama_nis = nis_bersih and not nis_bersih.startswith("sis-") and bersihkan_teks(p.get("nis")) == nis_bersih
        sama_nama = bersihkan_teks(p.get("nama")) == nama_bersih and bersihkan_teks(p.get("kelas")) == kelas_bersih
        if sama_nis or sama_nama:
            return jsonify({
                "success": False,
                "message": (
                    f"Siswa '{p['nama']}' (NIS: {p['nis']}) sudah terdaftar di cabang '{p['competitionName']}' "
                    f"pada event {ev['name']} (Tiket: {p['id']}). Aturan LombaKu: maksimal 1 cabang per event."
                )
            }), 400

    # Buat Kode Tiket LombaKu unik (contoh: LMK-BB-014)
    awalan = "BB" if id_event == "bulan-bahasa" else ("PR" if id_event == "porak" else "AG")
    nomor_urut = len(semua.get("participants", [])) + 1
    kode_tiket = f"LMK-{awalan}-{nomor_urut:03d}-{secrets.randbelow(90) + 10}"
    waktu_skrg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    koneksi = buka_koneksi()
    try:
        koneksi.execute("""
            INSERT INTO tb_pendaftaran
            (kode_tiket, id_event, id_lomba, nama_siswa, nis, kelas, no_wa,
             nama_tim, anggota_tim_json, sudah_baca_juknis, waktu_daftar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
        """, (
            kode_tiket,
            id_event,
            id_lomba,
            nama_siswa,
            nis,
            kelas,
            no_wa or "-",
            nama_tim if comp.get("isGroup") else "",
            json.dumps(anggota_list if comp.get("isGroup") else [], ensure_ascii=False),
            waktu_skrg,
        ))
        koneksi.commit()
    finally:
        koneksi.close()

    # Aktifkan sesi Paspor Siswa secara otomatis
    session["nis_siswa_aktif"] = nis
    session["tiket_siswa_aktif"] = kode_tiket

    tiket_data = {
        "id": kode_tiket,
        "kodeTiket": kode_tiket,
        "password": nis,
        "nama": nama_siswa,
        "nis": nis,
        "kelas": kelas,
        "kontak": no_wa or "-",
        "eventId": id_event,
        "eventName": ev["name"],
        "competitionId": id_lomba,
        "competitionName": comp["name"],
        "isGroup": comp.get("isGroup", False),
        "namaKelompok": nama_tim if comp.get("isGroup") else "",
        "anggotaList": anggota_list if comp.get("isGroup") else [],
        "totalPendaftar": (1 + len(anggota_list)) if comp.get("isGroup") else 1,
        "registeredAt": waktu_skrg,
        "status": "Terdaftar Resmi",
    }

    return jsonify({
        "success": True,
        "autoLoggedIn": True,
        "redirectUrl": f"/peserta?welcome=1&nis={nis}&tiket={kode_tiket}",
        "message": f"Pendaftaran berhasil! Tiket {kode_tiket} telah ditambahkan ke Paspor Siswa Anda.",
        "card": tiket_data,
    })


# ====================================================================
# 4. API SESI PASPOR SISWA (MASUK DENGAN NIS / KODE TIKET)
# ====================================================================

def _susun_respon_paspor(tiket_terpilih, semua_data):
    """Menyusun data lengkap untuk halaman Profil / Paspor Siswa."""
    semua_milik_siswa = cek_paspor_siswa(tiket_terpilih["nis"], semua_data)
    if not semua_milik_siswa:
        semua_milik_siswa = cek_paspor_siswa(tiket_terpilih["id"], semua_data)

    aktif_detail = next(
        (item for item in semua_milik_siswa if item["id"] == tiket_terpilih["id"]),
        semua_milik_siswa[0] if semua_milik_siswa else tiket_terpilih,
    )
    ev = next((e for e in semua_data["events"] if e["id"] == aktif_detail["eventId"]), None)
    comp = next((c for c in semua_data["competitions"] if c["id"] == aktif_detail["competitionId"]), None)

    return {
        "authenticated": True,
        "success": True,
        "participant": aktif_detail,
        "event": ev,
        "competition": comp,
        "bracketStatus": aktif_detail.get("bracketStatus", "Terdaftar Resmi"),
        "allRegistrations": semua_milik_siswa,
    }


@app.route("/api/participant/me")
def api_paspor_saya():
    tiket_id = session.get("tiket_siswa_aktif")
    nis_aktif = session.get("nis_siswa_aktif")
    if not tiket_id and not nis_aktif:
        return jsonify({"authenticated": False})

    semua = ambil_semua_data_lombaku()
    ditemukan = None
    if tiket_id:
        ditemukan = next((p for p in semua["participants"] if p["id"] == tiket_id), None)
    if not ditemukan and nis_aktif:
        ditemukan = next((p for p in semua["participants"] if p["nis"] == nis_aktif), None)

    if not ditemukan:
        session.pop("tiket_siswa_aktif", None)
        session.pop("nis_siswa_aktif", None)
        return jsonify({"authenticated": False})

    return jsonify(_susun_respon_paspor(ditemukan, semua))


@app.route("/api/participant/login", methods=["POST"])
def api_masuk_paspor_siswa():
    """
    Siswa dapat masuk ke Paspor Profil cukup menggunakan:
    - NIS / NISN (atau Kode Tiket LMK-...)
    - Kelas atau Nama (maupun password/NIS).
    """
    body = request.get_json() or {}
    kunci_utama = (body.get("id") or body.get("nis") or "").strip()
    kunci_kedua = (body.get("password") or body.get("kelas") or "").strip()

    if not kunci_utama:
        return jsonify({"success": False, "message": "Masukkan NIS/NISN atau Kode Tiket LombaKu Anda."}), 400

    semua = ambil_semua_data_lombaku()
    q1 = bersihkan_teks(kunci_utama)
    q2 = bersihkan_teks(kunci_kedua)

    cocok = None
    for p in semua["participants"]:
        cocok_id_atau_nis = (
            bersihkan_teks(p["id"]) == q1
            or bersihkan_teks(p["nis"]) == q1
            or bersihkan_teks(p["nama"]) == q1
        )
        if cocok_id_atau_nis:
            if not q2 or q2 in (
                bersihkan_teks(p["nis"]),
                bersihkan_teks(p["kelas"]),
                bersihkan_teks(p["id"]),
                bersihkan_teks(p["nama"]),
            ):
                cocok = p
                break

    if not cocok:
        return jsonify({
            "success": False,
            "message": "Data siswa tidak ditemukan. Pastikan NIS/NISN atau Kode Tiket sudah benar."
        }), 401

    session["nis_siswa_aktif"] = cocok["nis"]
    session["tiket_siswa_aktif"] = cocok["id"]
    return jsonify(_susun_respon_paspor(cocok, semua))


@app.route("/api/participant/switch", methods=["POST"])
def api_ganti_tiket_paspor():
    body = request.get_json() or {}
    target_id = (body.get("id") or "").strip()
    semua = ambil_semua_data_lombaku()
    target = next((p for p in semua["participants"] if p["id"].upper() == target_id.upper()), None)
    if not target:
        return jsonify({"success": False, "message": "Tiket lomba tidak ditemukan."}), 404

    session["tiket_siswa_aktif"] = target["id"]
    session["nis_siswa_aktif"] = target["nis"]
    return jsonify(_susun_respon_paspor(target, semua))


@app.route("/api/participant/logout", methods=["POST"])
def api_keluar_paspor():
    session.pop("tiket_siswa_aktif", None)
    session.pop("nis_siswa_aktif", None)
    return jsonify({"success": True})


# ====================================================================
# 5. API PANEL KENDALI PANITIA / GURU PEMBINA
# ====================================================================

@app.route("/api/panitia/login", methods=["POST"])
def api_login_panitia():
    body = request.get_json() or {}
    user_input = (body.get("id") or body.get("username") or "").strip()
    pw_input = (body.get("password") or "").strip()

    semua = ambil_semua_data_lombaku()
    ditemukan = None

    # Dukung login default ('panitia' dengan password 'lombaku2026' atau 'panitia')
    if user_input.lower() == "panitia" and pw_input in ("lombaku2026", "panitia"):
        ditemukan = {
            "id": "panitia",
            "name": "Koordinator Panitia LombaKu",
            "role": "Pembina OSIS",
        }
    else:
        for adm in semua.get("panitia", []):
            if adm["id"].lower() == user_input.lower() and adm["password"] == pw_input:
                ditemukan = {
                    "id": adm["id"],
                    "name": adm["name"],
                    "role": adm["role"],
                }
                break

    if not ditemukan:
        return jsonify({
            "success": False,
            "message": "Username atau Password Panitia salah."
        }), 401

    session["admin_lombaku"] = ditemukan
    return jsonify({
        "success": True,
        "message": f"Selamat bertugas, {ditemukan['name']}!",
        "panitia": ditemukan,
    })


@app.route("/api/panitia/me")
def api_status_panitia():
    adm = session.get("admin_lombaku")
    if adm:
        return jsonify({"authenticated": True, "panitia": adm})
    return jsonify({"authenticated": False})


@app.route("/api/panitia/logout", methods=["POST"])
def api_logout_panitia():
    session.pop("admin_lombaku", None)
    return jsonify({"success": True})


@app.route("/api/panitia/participants")
@wajib_login_panitia
def api_daftar_peserta_panitia():
    semua = ambil_semua_data_lombaku()
    return jsonify({
        "success": True,
        "participants": semua.get("participants", []),
    })


@app.route("/api/panitia/delete-participant", methods=["POST"])
@wajib_login_panitia
def api_hapus_peserta():
    body = request.get_json() or {}
    kode = (body.get("id") or "").strip()
    koneksi = buka_koneksi()
    try:
        kursor = koneksi.execute("DELETE FROM tb_pendaftaran WHERE kode_tiket = ?;", (kode,))
        koneksi.commit()
        if kursor.rowcount == 0:
            return jsonify({"success": False, "message": "Data tiket peserta tidak ditemukan."}), 404
    finally:
        koneksi.close()
    return jsonify({"success": True, "message": f"Tiket pendaftaran {kode} berhasil dihapus."})


@app.route("/api/panitia/toggle-event-lock", methods=["POST"])
@wajib_login_panitia
def api_ubah_status_event():
    body = request.get_json() or {}
    id_ev = body.get("eventId")
    mode_baru = body.get("statusMode")

    koneksi = buka_koneksi()
    try:
        baris = koneksi.execute(
            "SELECT nama_event, mode_status FROM tb_event WHERE id_event = ?;", (id_ev,)
        ).fetchone()
        if not baris:
            return jsonify({"success": False, "message": "Event tidak ditemukan."}), 404

        if not mode_baru:
            mode_baru = "available" if baris["mode_status"] == "locked" else "locked"

        koneksi.execute(
            "UPDATE tb_event SET mode_status = ? WHERE id_event = ?;",
            (mode_baru, id_ev),
        )
        koneksi.commit()
    finally:
        koneksi.close()

    return jsonify({
        "success": True,
        "locked": mode_baru == "locked",
        "message": f"Mode status event {baris['nama_event']} diubah ke {mode_baru.upper()}."
    })


@app.route("/api/panitia/update-event-schedule", methods=["POST"])
@wajib_login_panitia
def api_simpan_jadwal_event():
    body = request.get_json() or {}
    id_ev = body.get("eventId")
    batas = (body.get("registrationDeadline") or "").strip()
    tgl_acara = (body.get("eventDate") or "").strip()

    koneksi = buka_koneksi()
    try:
        koneksi.execute("""
            UPDATE tb_event
            SET waktu_tutup = COALESCE(NULLIF(?, ''), waktu_tutup),
                tanggal_acara = COALESCE(NULLIF(?, ''), tanggal_acara)
            WHERE id_event = ?;
        """, (batas, tgl_acara, id_ev))
        koneksi.commit()
    finally:
        koneksi.close()

    return jsonify({"success": True, "message": "Jadwal event berhasil disimpan ke SQLite!"})


@app.route("/api/panitia/toggle-comp-lock", methods=["POST"])
@wajib_login_panitia
def api_buka_tutup_lomba():
    body = request.get_json() or {}
    id_lomba = body.get("compId")

    koneksi = buka_koneksi()
    try:
        baris = koneksi.execute(
            "SELECT nama_lomba, aktif FROM tb_lomba WHERE id_lomba = ?;", (id_lomba,)
        ).fetchone()
        if not baris:
            return jsonify({"success": False, "message": "Cabang lomba tidak ditemukan."}), 404
        aktif_baru = 0 if baris["aktif"] else 1
        koneksi.execute("UPDATE tb_lomba SET aktif = ? WHERE id_lomba = ?;", (aktif_baru, id_lomba))
        koneksi.commit()
    finally:
        koneksi.close()

    return jsonify({
        "success": True,
        "locked": aktif_baru == 0,
        "message": f"Cabang {baris['nama_lomba']} {'dibuka' if aktif_baru else 'ditutup'}."
    })


@app.route("/api/panitia/add-competition", methods=["POST"])
@wajib_login_panitia
def api_tambah_cabang_lomba():
    body = request.get_json() or {}
    id_event = (body.get("eventId") or "").strip()
    nama = (body.get("name") or "").strip()
    kategori = (body.get("category") or "Individu").strip()
    juknis_mentah = (body.get("juknis") or "").strip()
    kuota = int(body.get("quota") or 16)
    jadwal = (body.get("schedule") or "08.00 WIB – Selesai").strip()
    lokasi = (body.get("venue") or "Area Utama Sekolah").strip()
    pj = (body.get("pj") or "Panitia OSIS").strip()
    is_group = bool(body.get("isGroup")) or ("tim" in kategori.lower())
    min_anggota = max(2, int(body.get("minMembers") or 2)) if is_group else 1

    if not id_event or not nama or not juknis_mentah:
        return jsonify({"success": False, "message": "Event, Nama Cabang, dan Aturan wajib diisi."}), 400

    aturan_list = [baris.strip() for baris in juknis_mentah.split("\n") if baris.strip()]
    kriteria_default = [
        {"aspek": "Kualitas Penampilan & Teknik", "bobot": 60},
        {"aspek": "Kesesuaian Aturan & Sportivitas", "bobot": 40},
    ]
    slug = "".join(ch if ch.isalnum() else "-" for ch in nama.lower()).strip("-")
    id_lomba = f"{id_event[:3]}-{slug}-{secrets.token_hex(2)}"

    koneksi = buka_koneksi()
    try:
        koneksi.execute("""
            INSERT INTO tb_lomba
            (id_lomba, id_event, nama_lomba, kategori, minimal_anggota, kuota,
             jadwal_tanding, lokasi_lomba, penanggung_jawab, ringkasan, aktif,
             aturan_json, kriteria_json, perlengkapan, catatan_panitia, bagan_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?);
        """, (
            id_lomba,
            id_event,
            nama,
            "Tim / Kelas" if is_group else kategori,
            min_anggota,
            kuota,
            jadwal,
            lokasi,
            pj,
            f"Cabang perlombaan {nama} ({kategori}).",
            json.dumps(aturan_list, ensure_ascii=False),
            json.dumps(kriteria_default, ensure_ascii=False),
            "Menyesuaikan arahan PJ lomba.",
            "Hadir 15 menit sebelum jadwal dimulai.",
            json.dumps({"rounds": [], "champion": ""}),
        ))
        koneksi.commit()
    finally:
        koneksi.close()

    return jsonify({
        "success": True,
        "message": f"Cabang lomba '{nama}' berhasil ditambahkan ke database SQLite!"
    })


@app.route("/api/panitia/update-juknis", methods=["POST"])
@wajib_login_panitia
def api_ubah_juknis_lomba():
    body = request.get_json() or {}
    id_lomba = body.get("compId")
    juknis_teks = (body.get("juknis") or "").strip()
    if not id_lomba or not juknis_teks:
        return jsonify({"success": False, "message": "Isi aturan/juknis tidak boleh kosong."}), 400

    aturan_baru = [b.strip() for b in juknis_teks.split("\n") if b.strip()]
    koneksi = buka_koneksi()
    try:
        koneksi.execute(
            "UPDATE tb_lomba SET aturan_json = ? WHERE id_lomba = ?;",
            (json.dumps(aturan_baru, ensure_ascii=False), id_lomba),
        )
        koneksi.commit()
    finally:
        koneksi.close()

    return jsonify({"success": True, "message": "Persyaratan & Juknis lomba berhasil diperbarui!"})


@app.route("/api/panitia/list")
@wajib_login_panitia
def api_daftar_admin():
    semua = ambil_semua_data_lombaku()
    return jsonify({"success": True, "panitia": semua.get("panitia", [])})


@app.route("/api/panitia/add", methods=["POST"])
@wajib_login_panitia
def api_tambah_admin():
    body = request.get_json() or {}
    uname = (body.get("id") or "").strip()
    nama = (body.get("name") or "").strip()
    jabatan = (body.get("role") or "Panitia OSIS").strip()
    pw = (body.get("password") or "").strip()
    if not uname or not nama or not pw:
        return jsonify({"success": False, "message": "Lengkapi Username, Nama, dan Password."}), 400

    koneksi = buka_koneksi()
    try:
        ada = koneksi.execute(
            "SELECT 1 FROM tb_admin WHERE LOWER(username) = LOWER(?);", (uname,)
        ).fetchone()
        if ada:
            return jsonify({"success": False, "message": "Username panitia sudah digunakan."}), 400
        koneksi.execute(
            "INSERT INTO tb_admin (username, nama_lengkap, jabatan, password) VALUES (?, ?, ?, ?);",
            (uname, nama, jabatan, pw),
        )
        koneksi.commit()
    finally:
        koneksi.close()

    return jsonify({"success": True, "message": f"Akun panitia '{nama}' berhasil ditambahkan!"})


@app.route("/api/panitia/delete", methods=["POST"])
@wajib_login_panitia
def api_hapus_admin():
    body = request.get_json() or {}
    target = (body.get("id") or "").strip()
    if target.lower() == "panitia":
        return jsonify({"success": False, "message": "Akun utama 'panitia' tidak boleh dihapus."}), 400

    koneksi = buka_koneksi()
    try:
        koneksi.execute("DELETE FROM tb_admin WHERE LOWER(username) = LOWER(?);", (target,))
        koneksi.commit()
    finally:
        koneksi.close()

    return jsonify({"success": True, "message": f"Akun panitia '{target}' dihapus."})


# ====================================================================
# 6. API BAGAN PERTANDINGAN & EKSPOR EXCEL (.XLSX)
# ====================================================================

@app.route("/api/panitia/bracket/update", methods=["POST"])
@wajib_login_panitia
def api_kelola_bagan():
    body = request.get_json() or {}
    id_lomba = body.get("compId")
    aksi = body.get("action")

    if aksi == "shuffle":
        bagan, pesan = acak_bagan_lomba(id_lomba)
        if not bagan:
            return jsonify({"success": False, "message": pesan}), 404
        return jsonify({"success": True, "message": pesan, "bracket": bagan})

    if aksi == "reset":
        koneksi = buka_koneksi()
        try:
            koneksi.execute(
                "UPDATE tb_lomba SET bagan_json = ? WHERE id_lomba = ?;",
                (json.dumps({"rounds": [], "champion": ""}), id_lomba),
            )
            koneksi.commit()
        finally:
            koneksi.close()
        return jsonify({"success": True, "message": "Bagan berhasil direset."})

    if aksi == "advance":
        idx_babak = int(body.get("roundIndex", 0))
        idx_match = int(body.get("matchIndex", 0))
        pemenang = (body.get("winner") or "").strip()
        bagan, pesan = majukan_pemenang_bagan(id_lomba, idx_babak, idx_match, pemenang)
        if not bagan:
            return jsonify({"success": False, "message": pesan}), 400
        return jsonify({"success": True, "message": pesan, "bracket": bagan})

    return jsonify({"success": False, "message": "Aksi tidak dikenali."}), 400


@app.route("/api/panitia/export-excel")
@wajib_login_panitia
def api_unduh_excel():
    filter_ev = (request.args.get("eventId") or "").strip()
    stream_xlsx = buat_file_excel_lombaku(filter_ev)
    nama_file = f"Rekap_LombaKu_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        stream_xlsx,
        as_attachment=True,
        download_name=nama_file,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    print(f"Server Python LombaKu aktif di http://127.0.0.1:5000 (Database: {LOKASI_DB})")
    app.run(host="127.0.0.1", port=5000, debug=False)
