"""
Layanan ekspor data pendaftaran peserta ke format Excel (.xlsx) menggunakan openpyxl.
Mendukung ekspor: semua event, event tertentu, atau cabang lomba tertentu.
"""
from io import BytesIO
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from services.registration import get_participants


def export_registrations_excel(db, event_id=None, competition_id=None) -> tuple:
    """
    Membuat file Excel (.xlsx) di memori dan mengembalikan (BytesIO, filename).
    """
    participants = get_participants(db, event_id=event_id, competition_id=competition_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Data Peserta Lombaku"

    # Warna tema Liquid Navy Lombaku
    navy_fill = PatternFill(start_color="0F1F35", end_color="0F1F35", fill_type="solid")
    sub_fill = PatternFill(start_color="1B3250", end_color="1B3250", fill_type="solid")
    zebra_fill = PatternFill(start_color="F4F7FA", end_color="F4F7FA", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    status_fills = {
        "Accepted": PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid"),
        "Registered": PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid"),
        "Pending": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"),
        "Rejected": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
    }

    thin_border = Border(
        left=Side(style="thin", color="D5DEE8"),
        right=Side(style="thin", color="D5DEE8"),
        top=Side(style="thin", color="D5DEE8"),
        bottom=Side(style="thin", color="D5DEE8"),
    )

    # Judul laporan di baris 1-2
    scope_label = "Semua Event"
    filename_suffix = "semua_event"
    if competition_id:
        c = db.execute(
            "SELECT c.name, e.name AS event_name FROM competitions c JOIN events e ON e.id = c.event_id WHERE c.id = ?",
            (competition_id,),
        ).fetchone()
        if c:
            scope_label = f"{c['event_name']} — {c['name']}"
            filename_suffix = f"cabang_{c['name'].lower().replace(' ', '_')}"
    elif event_id:
        e = db.execute("SELECT name FROM events WHERE id = ?", (event_id,)).fetchone()
        if e:
            scope_label = f"Event {e['name']}"
            filename_suffix = f"event_{e['name'].lower().replace(' ', '_')}"

    ws.merge_cells("A1:M1")
    ws["A1"] = f"LOMBAKU — LAPORAN DATA PENDAFTARAN ({scope_label.upper()})"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:M2")
    ws["A2"] = f"Diekspor pada: {datetime.now().strftime('%d-%m-%Y %H:%M WIB')} · Total Pendaftar: {len(participants)}"
    ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="E2E8F0")
    ws["A2"].fill = sub_fill
    ws["A2"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 22

    headers = [
        "No",
        "Kode Daftar",
        "Nama Event",
        "Cabang Lomba",
        "Tipe",
        "Nama Peserta",
        "NIS",
        "Kelas",
        "Nama Tim",
        "Ketua Tim",
        "Anggota Tim (Nama & NIS)",
        "Waktu Pendaftaran",
        "Status",
    ]

    header_row = 4
    ws.row_dimensions[header_row].height = 26
    for col_idx, text in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=text)
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    for idx, p in enumerate(participants, start=1):
        row_num = header_row + idx
        is_team = p["comp_type"] == "TEAM"
        if is_team and p["members"]:
            anggota_str = "; ".join(
                f"{m['member_name']} ({m['member_nis']} - {m['member_kelas']})"
                for m in p["members"]
            )
        else:
            anggota_str = "-"

        values = [
            idx,
            p["registration_code"],
            p["event_name"],
            p["competition_name"],
            "Tim" if is_team else "Individu",
            p["team_name"] if is_team else p["participant_name"],
            p["nis"],
            p["kelas"],
            p["team_name"] if is_team else "-",
            p["participant_name"] if is_team else "-",
            anggota_str,
            p["created_at"],
            p["status"],
        ]

        row_fill = zebra_fill if idx % 2 == 0 else white_fill
        ws.row_dimensions[row_num].height = 22 if not is_team else 32
        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(row=row_num, column=col_idx, value=val)
            cell.font = Font(name="Calibri", size=10, color="1E293B")
            cell.fill = status_fills.get(p["status"], row_fill) if col_idx == 13 else row_fill
            cell.border = thin_border
            if col_idx in (1, 2, 5, 7, 8, 13):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=(col_idx == 11))

    # Lebar kolom proporsional
    col_widths = [6, 17, 18, 22, 11, 24, 14, 12, 22, 20, 44, 20, 14]
    for col_idx, width in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.freeze_panes = "A5"

    # Sheet kedua: Ringkasan per Cabang Lomba
    ws2 = wb.create_sheet(title="Ringkasan")
    ws2.append(["Nama Event", "Cabang Lomba", "Tipe", "Total Pendaftar", "Accepted", "Registered", "Pending", "Rejected"])
    for cell in ws2[1]:
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.fill = navy_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    summary = {}
    for p in participants:
        key = (p["event_name"], p["competition_name"], "Tim" if p["comp_type"] == "TEAM" else "Individu")
        if key not in summary:
            summary[key] = {"total": 0, "Accepted": 0, "Registered": 0, "Pending": 0, "Rejected": 0}
        summary[key]["total"] += 1
        if p["status"] in summary[key]:
            summary[key][p["status"]] += 1

    for (ev, comp, ctype), counts in summary.items():
        ws2.append([ev, comp, ctype, counts["total"], counts["Accepted"], counts["Registered"], counts["Pending"], counts["Rejected"]])

    for idx, w in enumerate([20, 24, 12, 16, 12, 12, 12, 12], start=1):
        ws2.column_dimensions[get_column_letter(idx)].width = w

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    date_tag = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"lombaku_{filename_suffix}_{date_tag}.xlsx"
    return output, filename
