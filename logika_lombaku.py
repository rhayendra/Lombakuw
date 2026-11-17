"""
====================================================================
FILE: logika_lombaku.py
DESKRIPSI:
Berisi seluruh fungsi perhitungan logika aplikasi LombaKu:
1. Perhitungan status buka/kunci otomatis event (Schedule-Based Lock).
2. Pemeriksaan aturan 1 siswa 1 cabang per event (Single Registration via NIS).
3. Validasi kuota lomba dan syarat jumlah minimal anggota tim.
4. Pengacakan bagan sistem gugur (Shuffle) dan penentuan juara.
5. Pembuatan file laporan Excel (.xlsx) dari database SQLite.
====================================================================
"""

import json
import math
import secrets
import zipfile
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

from database_lombaku import buka_koneksi


def bersihkan_teks(teks):
    """Merapikan teks menjadi huruf kecil tanpa spasi ganda untuk pencocokan data."""
    return " ".join(str(teks or "").strip().lower().split())


def hitung_status_event(ev_dict):
    """
    Menentukan apakah suatu event sedang TERBUKA (AVAILABLE) atau TERKUNCI (LOCKED)
    berdasarkan pengaturan panitia ('available', 'locked', atau 'auto' jadwal).
    """
    mode = (ev_dict.get("statusMode") or "auto").lower()
    sekarang = datetime.now()

    waktu_tutup_str = ev_dict.get("registrationDeadline") or ""
    lewat_jadwal = False
    if waktu_tutup_str:
        try:
            batas = datetime.fromisoformat(waktu_tutup_str.replace("Z", ""))
            lewat_jadwal = sekarang >= batas
        except ValueError:
            lewat_jadwal = False

    if mode == "available":
        terkunci_efektif = False
        alasan = "Dibuka langsung oleh Panitia (Available)"
    elif mode == "locked":
        terkunci_efektif = True
        alasan = "Ditutup sementara oleh Panitia (Locked)"
    else:
        terkunci_efektif = lewat_jadwal
        alasan = (
            "Terkunci otomatis karena melewati batas waktu pendaftaran"
            if lewat_jadwal
            else "Terbuka otomatis sesuai jadwal pendaftaran"
        )

    return {
        "scheduleLocked": lewat_jadwal,
        "locked": mode == "locked",
        "effectiveLocked": terkunci_efektif,
        "effectiveStatus": "LOCKED" if terkunci_efektif else "AVAILABLE",
        "lockReason": alasan,
    }


def format_juknis_teks(aturan_list, kriteria_list, perlengkapan, catatan):
    """
    Menyusun ringkasan teks juknis yang rapi dari daftar aturan, kriteria bobot,
    perlengkapan wajib, dan catatan panitia.
    """
    baris = ["KETENTUAN & ATURAN LOMBA:"]
    for idx, a in enumerate(aturan_list, start=1):
        baris.append(f"{idx}. {a}")

    if kriteria_list:
        baris.append("\nKRITERIA PENILAIAN JURI:")
        for k in kriteria_list:
            if isinstance(k, dict):
                baris.append(f"• {k.get('aspek', '-')}: {k.get('bobot', 0)}%")
            else:
                baris.append(f"• {k}")

    if perlengkapan:
        baris.append(f"\nPERLENGKAPAN WAJIB:\n{perlengkapan}")

    if catatan:
        baris.append(f"\nCATATAN PANITIA:\n{catatan}")

    return "\n".join(baris)


def ambil_semua_data_lombaku():
    """
    Membaca seluruh data Event, Cabang Lomba, Pendaftaran, dan Admin dari SQLite,
    lalu menghitung statistik kuota dan status masing-masing cabang.
    """
    koneksi = buka_koneksi()
    try:
        kursor = koneksi.cursor()

        kursor.execute("SELECT * FROM tb_event ORDER BY urutan ASC, id_event ASC;")
        rows_event = kursor.fetchall()

        kursor.execute("SELECT * FROM tb_lomba ORDER BY rowid ASC;")
        rows_lomba = kursor.fetchall()

        kursor.execute("SELECT * FROM tb_pendaftaran ORDER BY rowid ASC;")
        rows_daftar = kursor.fetchall()

        kursor.execute("SELECT * FROM tb_admin ORDER BY rowid ASC;")
        rows_admin = kursor.fetchall()

        # Mapping nama event dan nama lomba
        peta_nama_event = {r["id_event"]: r["nama_event"] for r in rows_event}
        peta_nama_lomba = {r["id_lomba"]: r["nama_lomba"] for r in rows_lomba}

        # Susun daftar pendaftaran
        daftar_peserta = []
        for p in rows_daftar:
            try:
                anggota = json.loads(p["anggota_tim_json"] or "[]")
            except Exception:
                anggota = []
            nama_tim = p["nama_tim"] or ""
            is_grp = bool(nama_tim) or len(anggota) > 0

            daftar_peserta.append({
                "id": p["kode_tiket"],
                "kodeTiket": p["kode_tiket"],
                "password": p["nis"],  # NIS berfungsi sebagai kunci akses paspor siswa
                "nama": p["nama_siswa"],
                "studentName": p["nama_siswa"],
                "nis": p["nis"],
                "kelas": p["kelas"],
                "kontak": p["no_wa"],
                "phone": p["no_wa"],
                "eventId": p["id_event"],
                "eventName": peta_nama_event.get(p["id_event"], p["id_event"]),
                "competitionId": p["id_lomba"],
                "competitionName": peta_nama_lomba.get(p["id_lomba"], p["id_lomba"]),
                "isGroup": is_grp,
                "namaKelompok": nama_tim,
                "teamName": nama_tim,
                "anggotaList": anggota,
                "totalPendaftar": (1 + len(anggota)) if is_grp else 1,
                "registeredAt": p["waktu_daftar"],
                "status": "Terdaftar Resmi"
            })

        # Kelompokkan cabang lomba per event
        lomba_per_event = {}
        semua_cabang_flat = []
        for c in rows_lomba:
            try:
                aturan_list = json.loads(c["aturan_json"] or "[]")
            except Exception:
                aturan_list = []
            try:
                kriteria_list = json.loads(c["kriteria_json"] or "[]")
            except Exception:
                kriteria_list = []
            try:
                bagan_obj = json.loads(c["bagan_json"] or "{}")
            except Exception:
                bagan_obj = {"rounds": [], "champion": ""}

            terdaftar_cabang = sum(
                1 for p in daftar_peserta if p["competitionId"] == c["id_lomba"]
            )
            kuota_maks = int(c["kuota"] or 16)
            sisa_kuota = max(0, kuota_maks - terdaftar_cabang)
            is_group = "tim" in (c["kategori"] or "").lower() or int(c["minimal_anggota"] or 1) > 1
            juknis_teks = format_juknis_teks(
                aturan_list, kriteria_list, c["perlengkapan"], c["catatan_panitia"]
            )

            item_lomba = {
                "id": c["id_lomba"],
                "eventId": c["id_event"],
                "name": c["nama_lomba"],
                "category": c["kategori"],
                "isGroup": is_group,
                "minMembers": int(c["minimal_anggota"] or 1),
                "quota": kuota_maks,
                "participantCount": terdaftar_cabang,
                "registeredCount": terdaftar_cabang,
                "remainingQuota": sisa_kuota,
                "isQuotaFull": sisa_kuota <= 0,
                "schedule": c["jadwal_tanding"] or "08.00 WIB – Selesai",
                "venue": c["lokasi_lomba"] or "Area Sekolah",
                "pj": c["penanggung_jawab"] or "Panitia OSIS",
                "summary": c["ringkasan"] or "",
                "locked": not bool(c["aktif"]),
                "isActive": bool(c["aktif"]),
                "rules": aturan_list,
                "criteria": kriteria_list,
                "equipment": c["perlengkapan"] or "-",
                "notes": c["catatan_panitia"] or "-",
                "juknis": juknis_teks,
                "bracket": bagan_obj,
            }
            lomba_per_event.setdefault(c["id_event"], []).append(item_lomba)
            semua_cabang_flat.append(item_lomba)

        # Susun daftar event utama
        daftar_event = []
        for ev in rows_event:
            ev_base = {
                "id": ev["id_event"],
                "name": ev["nama_event"],
                "subtitle": ev["slogan"],
                "tagline": ev["slogan"],
                "description": ev["deskripsi"],
                "location": ev["lokasi_utama"],
                "themeColor": ev["tema_warna"],
                "statusMode": ev["mode_status"],
                "registrationOpenAt": ev["waktu_buka"],
                "registrationDeadline": ev["waktu_tutup"],
                "eventDate": ev["tanggal_acara"],
            }
            info_status = hitung_status_event(ev_base)
            ev_base.update(info_status)

            cabang_ev = lomba_per_event.get(ev["id_event"], [])
            for c in cabang_ev:
                c["effectiveLocked"] = c["locked"] or ev_base["effectiveLocked"] or c["isQuotaFull"]

            ev_base["competitions"] = cabang_ev
            ev_base["competitionCount"] = len(cabang_ev)
            ev_base["participantCount"] = sum(
                1 for p in daftar_peserta if p["eventId"] == ev["id_event"]
            )
            daftar_event.append(ev_base)

        daftar_admin = [
            {
                "id": a["username"],
                "name": a["nama_lengkap"],
                "role": a["jabatan"],
                "password": a["password"],
            }
            for a in rows_admin
        ]

        return {
            "events": daftar_event,
            "competitions": semua_cabang_flat,
            "participants": daftar_peserta,
            "panitia": daftar_admin,
        }
    finally:
        koneksi.close()


def cek_paspor_siswa(kata_kunci, semua_data):
    """
    Mencari seluruh pendaftaran siswa berdasarkan NIS/NISN, Kode Tiket, atau Nama,
    serta melengkapi posisi babak pertandingan mereka di bagan.
    """
    q = bersihkan_teks(kata_kunci)
    if not q:
        return []

    peserta_cocok = [
        p for p in semua_data.get("participants", [])
        if (
            bersihkan_teks(p.get("nis")) == q
            or bersihkan_teks(p.get("id")) == q
            or q in bersihkan_teks(p.get("nama"))
            or (p.get("namaKelompok") and q in bersihkan_teks(p.get("namaKelompok")))
        )
    ]

    peta_lomba = {c["id"]: c for c in semua_data.get("competitions", [])}
    peta_event = {e["id"]: e for e in semua_data.get("events", [])}

    hasil = []
    for p in peserta_cocok:
        comp = peta_lomba.get(p["competitionId"], {})
        ev = peta_event.get(p["eventId"], {})
        bagan = comp.get("bracket", {})
        label_peserta = (
            f"{p['namaKelompok']} ({p['kelas']})"
            if p.get("isGroup") and p.get("namaKelompok")
            else f"{p['nama']} ({p['kelas']})"
        )

        status_tanding = "Menunggu pengundian bagan oleh panitia"
        persen_progres = 40
        if bagan and bagan.get("rounds"):
            if bagan.get("champion") in (label_peserta, f"{p['nama']} ({p['kelas']})"):
                status_tanding = "🏆 Juara 1 pada cabang perlombaan ini!"
                persen_progres = 100
            else:
                posisi = []
                for idx_r, r in enumerate(bagan.get("rounds", [])):
                    for m in r.get("matches", []):
                        if m.get("p1") == label_peserta or m.get("p2") == label_peserta:
                            lawan = m.get("p2") if m.get("p1") == label_peserta else m.get("p1")
                            if m.get("winner") == label_peserta:
                                posisi.append(f"{r['name']}: Menang vs {lawan}")
                                persen_progres = min(90, 55 + (idx_r + 1) * 20)
                            elif m.get("winner"):
                                posisi.append(f"{r['name']}: Terhenti vs {lawan}")
                                persen_progres = 50
                            else:
                                posisi.append(f"{r['name']}: Dijadwalkan vs {lawan}")
                                persen_progres = 65
                if posisi:
                    status_tanding = " • ".join(posisi)
                else:
                    status_tanding = "Terdaftar resmi (Menunggu jadwal babak)"

        item_lengkap = dict(p)
        item_lengkap["schedule"] = comp.get("schedule", "-")
        item_lengkap["venue"] = comp.get("venue", ev.get("location", "-"))
        item_lengkap["pj"] = comp.get("pj", "Panitia OSIS")
        item_lengkap["bracketStatus"] = status_tanding
        item_lengkap["progressPercent"] = persen_progres
        hasil.append(item_lengkap)

    return hasil


def acak_bagan_lomba(id_lomba):
    """
    Mengacak peserta pada cabang lomba menggunakan algoritma Fisher-Yates
    dan menyimpannya ke kolom `bagan_json` pada tabel SQLite `tb_lomba`.
    """
    semua = ambil_semua_data_lombaku()
    comp = next((c for c in semua["competitions"] if c["id"] == id_lomba), None)
    if not comp:
        return None, "Cabang lomba tidak ditemukan."

    pendaftar = [p for p in semua["participants"] if p["competitionId"] == id_lomba]
    label_peserta = []
    for p in pendaftar:
        if p.get("isGroup") and p.get("namaKelompok"):
            label_peserta.append(f"{p['namaKelompok']} ({p['kelas']})")
        else:
            label_peserta.append(f"{p['nama']} ({p['kelas']})")

    if len(label_peserta) < 2:
        contoh = ["Perwakilan X-1", "Perwakilan X-2", "Perwakilan XI-IPA 1", "Perwakilan XII-IPS 1"]
        for c_nama in contoh:
            if len(label_peserta) >= 4:
                break
            if c_nama not in label_peserta:
                label_peserta.append(c_nama)

    # Fisher-Yates Shuffle
    acak = list(label_peserta)
    for i in range(len(acak) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        acak[i], acak[j] = acak[j], acak[i]

    ukuran = 1
    while ukuran < len(acak):
        ukuran *= 2
    ukuran = max(2, min(ukuran, 16))
    slot = acak[:ukuran]
    while len(slot) < ukuran:
        slot.append("BYE")

    jml_babak = int(math.log2(ukuran))
    peta_nama_babak = {
        1: ["Final"],
        2: ["Semifinal", "Final"],
        3: ["Perempat Final", "Semifinal", "Final"],
        4: ["16 Besar", "Perempat Final", "Semifinal", "Final"],
    }
    nama_babak_list = peta_nama_babak.get(jml_babak, [f"Babak {i+1}" for i in range(jml_babak)])

    rounds = []
    match_awal = []
    for i in range(0, ukuran, 2):
        p1, p2 = slot[i], slot[i + 1]
        pemenang = p1 if (p2 == "BYE" and p1 != "BYE") else (p2 if (p1 == "BYE" and p2 != "BYE") else "")
        match_awal.append({
            "id": f"{id_lomba}-r1-m{(i // 2) + 1}",
            "p1": p1,
            "p2": p2,
            "winner": pemenang,
        })
    rounds.append({"name": nama_babak_list[0], "matches": match_awal})

    sebelumnya = match_awal
    for r_idx in range(1, jml_babak):
        match_berikut = []
        for m_idx in range(len(sebelumnya) // 2):
            kiri = sebelumnya[m_idx * 2]
            kanan = sebelumnya[m_idx * 2 + 1]
            match_berikut.append({
                "id": f"{id_lomba}-r{r_idx + 1}-m{m_idx + 1}",
                "p1": kiri["winner"] or f"Menunggu Pemenang M{m_idx * 2 + 1}",
                "p2": kanan["winner"] or f"Menunggu Pemenang M{m_idx * 2 + 2}",
                "winner": "",
            })
        rounds.append({"name": nama_babak_list[r_idx], "matches": match_berikut})
        sebelumnya = match_berikut

    bagan_baru = {"rounds": rounds, "champion": ""}
    koneksi = buka_koneksi()
    try:
        koneksi.execute(
            "UPDATE tb_lomba SET bagan_json = ? WHERE id_lomba = ?;",
            (json.dumps(bagan_baru, ensure_ascii=False), id_lomba),
        )
        koneksi.commit()
    finally:
        koneksi.close()

    return bagan_baru, f"Bagan '{comp['name']}' berhasil diacak!"


def majukan_pemenang_bagan(id_lomba, idx_babak, idx_match, pemenang):
    """Memajukan pemenang suatu match ke babak berikutnya di SQLite."""
    koneksi = buka_koneksi()
    try:
        baris = koneksi.execute(
            "SELECT nama_lomba, bagan_json FROM tb_lomba WHERE id_lomba = ?;",
            (id_lomba,),
        ).fetchone()
        if not baris:
            return None, "Cabang lomba tidak ditemukan."

        bagan = json.loads(baris["bagan_json"] or "{}")
        rounds = bagan.get("rounds", [])
        if idx_babak < 0 or idx_babak >= len(rounds):
            return None, "Babak tidak valid."
        matches = rounds[idx_babak].get("matches", [])
        if idx_match < 0 or idx_match >= len(matches):
            return None, "Pertandingan tidak valid."

        if not pemenang or pemenang == "BYE" or pemenang.startswith("Menunggu"):
            return None, "Peserta belum valid untuk dimajukan."

        matches[idx_match]["winner"] = pemenang
        if idx_babak + 1 < len(rounds):
            target_m = rounds[idx_babak + 1]["matches"][idx_match // 2]
            if idx_match % 2 == 0:
                target_m["p1"] = pemenang
            else:
                target_m["p2"] = pemenang
            target_m["winner"] = ""
            bagan["champion"] = ""
        else:
            bagan["champion"] = pemenang

        koneksi.execute(
            "UPDATE tb_lomba SET bagan_json = ? WHERE id_lomba = ?;",
            (json.dumps(bagan, ensure_ascii=False), id_lomba),
        )
        koneksi.commit()
        return bagan, f"Pemenang '{pemenang}' berhasil dimajukan!"
    finally:
        koneksi.close()


def buat_file_excel_lombaku(id_event_filter=""):
    """
    Membuat file spreadsheet Excel (.xlsx) resmi dari tabel SQLite `tb_pendaftaran`.
    """
    semua = ambil_semua_data_lombaku()
    peserta = semua.get("participants", [])
    if id_event_filter and id_event_filter != "all":
        peserta = [p for p in peserta if p.get("eventId") == id_event_filter]

    judul_kolom = [
        "No",
        "Kode Tiket LombaKu",
        "NIS / NISN",
        "Nama Siswa / Perwakilan",
        "Kelas",
        "Event Utama",
        "Cabang Lomba",
        "Kategori",
        "Nama Tim / Regu",
        "Daftar Anggota Tim",
        "No. WhatsApp",
        "Waktu Daftar",
    ]

    baris_data = []
    for no, p in enumerate(peserta, start=1):
        anggota_str = ", ".join(p.get("anggotaList", [])) if p.get("anggotaList") else "-"
        baris_data.append([
            no,
            p.get("id", ""),
            p.get("nis", "-"),
            p.get("nama", ""),
            p.get("kelas", ""),
            p.get("eventName", ""),
            p.get("competitionName", ""),
            "Tim / Kelas" if p.get("isGroup") else "Individu",
            p.get("namaKelompok") or "-",
            anggota_str,
            p.get("kontak", "-"),
            p.get("registeredAt", ""),
        ])

    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "Rekap Pendaftar LombaKu"

        fill_ungu = PatternFill(start_color="4B2399", end_color="4B2399", fill_type="solid")
        fill_pastel = PatternFill(start_color="EDE7F6", end_color="EDE7F6", fill_type="solid")
        font_putih = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
        font_header = Font(name="Calibri", size=11, bold=True, color="1A153A")
        garis = Border(
            left=Side(style="thin", color="D1C4E9"),
            right=Side(style="thin", color="D1C4E9"),
            top=Side(style="thin", color="D1C4E9"),
            bottom=Side(style="thin", color="D1C4E9"),
        )

        ws.merge_cells("A1:L1")
        ws["A1"] = "REKAPITULASI PENDAFTARAN PESERTA — PORTAL LOMBAKU (SQLITE)"
        ws["A1"].font = font_putih
        ws["A1"].fill = fill_ungu
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

        for idx_k, teks in enumerate(judul_kolom, start=1):
            c = ws.cell(row=3, column=idx_k, value=teks)
            c.font = font_header
            c.fill = fill_pastel
            c.border = garis
            c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[3].height = 22

        for r_idx, row_vals in enumerate(baris_data, start=4):
            for c_idx, val in enumerate(row_vals, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.border = garis

        lebar = [6, 18, 15, 26, 14, 18, 26, 15, 22, 34, 18, 22]
        for i, w in enumerate(lebar, start=1):
            ws.column_dimensions[ws.cell(row=3, column=i).column_letter].width = w

        out = BytesIO()
        wb.save(out)
        out.seek(0)
        return out
    except ImportError:
        # Fallback menggunakan modul bawaan Python `zipfile`
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            zf.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            zf.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Rekap LombaKu" sheetId="1" r:id="rId1"/></sheets></workbook>')
            zf.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            rows_xml = []
            for r_i, r_vals in enumerate([judul_kolom] + baris_data, start=1):
                cells = "".join(f'<c t="inlineStr"><is><t>{xml_escape(str(v))}</t></is></c>' for v in r_vals)
                rows_xml.append(f'<row r="{r_i}">{cells}</row>')
            zf.writestr("xl/worksheets/sheet1.xml", f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(rows_xml)}</sheetData></worksheet>')
        buf.seek(0)
        return buf
