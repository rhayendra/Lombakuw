"""
Sistem Bracket Turnamen Otomatis Lombaku.
Mendukung jumlah peserta dinamis, slot BYE otomatis, shuffle acak,
penguncian bracket, update skor, dan perpindahan pemenang otomatis ke babak berikutnya.
"""
import math
import random


def get_round_name(round_number: int, total_rounds: int) -> str:
    """Memberi nama babak pertandingan yang rapi sesuai jumlah total babak."""
    remaining = total_rounds - round_number
    if remaining == 0:
        return "Final"
    if remaining == 1:
        return "Semifinal"
    if remaining == 2:
        return "Perempat Final"
    return f"Babak Penyisihan {round_number}"


def display_label_for_registration(reg_row) -> str:
    """Menentukan label tampilan peserta di bracket (Nama Tim atau Nama Siswa + Kelas)."""
    if reg_row["team_name"]:
        return f"{reg_row['team_name']} ({reg_row['kelas']})"
    return f"{reg_row['participant_name']} ({reg_row['kelas']})"


def get_eligible_participants(db, competition_id: int) -> list:
    """
    Mengambil peserta cabang lomba yang berhak masuk bracket
    (status Accepted atau Registered; yang Rejected tidak diikutkan).
    """
    rows = db.execute(
        """
        SELECT * FROM registrations
        WHERE competition_id = ? AND status IN ('Accepted', 'Registered')
        ORDER BY id ASC
        """,
        (competition_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def build_bracket(db, competition_id: int, shuffle: bool = False) -> tuple:
    """
    Membuat atau membangun ulang seluruh struktur bracket untuk sebuah cabang lomba.
    Jika jumlah peserta bukan pangkat 2, otomatis menambahkan BYE dan meloloskan
    lawan BYE ke babak berikutnya.
    """
    comp = db.execute("SELECT * FROM competitions WHERE id = ?", (competition_id,)).fetchone()
    if not comp:
        return False, "Cabang lomba tidak ditemukan."

    if comp["bracket_locked"]:
        return False, "Bracket sedang dikunci oleh panitia. Buka kunci terlebih dahulu untuk mengubah atau mengacak."

    participants = get_eligible_participants(db, competition_id)
    if len(participants) < 2:
        return False, "Minimal dibutuhkan 2 peserta (status Registered/Accepted) untuk membuat bracket."

    if shuffle:
        random.shuffle(participants)

    # Tentukan ukuran bracket (pangkat 2 terdekat >= jumlah peserta)
    n = len(participants)
    bracket_size = 1 << (n - 1).bit_length()
    total_rounds = int(math.log2(bracket_size))

    # Hapus bracket lama untuk cabang ini
    db.execute("DELETE FROM matches WHERE competition_id = ?", (competition_id,))

    # Sebar BYE secara seimbang agar tidak ada dua BYE bertemu
    # Buat daftar pasangan slot babak 1
    first_round_matches = bracket_size // 2
    slots_p1 = []
    slots_p2 = []
    for i in range(first_round_matches):
        slots_p1.append(participants[i] if i < n else None)
    for i in range(first_round_matches):
        idx = first_round_matches + i
        slots_p2.append(participants[idx] if idx < n else None)

    # Buat seluruh match dari babak 1 sampai Final
    matches_by_round = {}
    for r in range(1, total_rounds + 1):
        round_name = get_round_name(r, total_rounds)
        num_matches = bracket_size // (2 ** r)
        matches_by_round[r] = []

        for m_order in range(1, num_matches + 1):
            p1_id = None
            p2_id = None
            p1_label = "TBD"
            p2_label = "TBD"
            status = "PENDING"
            winner_id = None
            winner_label = ""

            if r == 1:
                p1 = slots_p1[m_order - 1]
                p2 = slots_p2[m_order - 1]
                if p1:
                    p1_id = p1["id"]
                    p1_label = display_label_for_registration(p1)
                else:
                    p1_label = "BYE"

                if p2:
                    p2_id = p2["id"]
                    p2_label = display_label_for_registration(p2)
                else:
                    p2_label = "BYE"

                # Otomatis lolos jika bertemu BYE
                if p1 and not p2:
                    status = "BYE"
                    winner_id = p1_id
                    winner_label = p1_label
                elif p2 and not p1:
                    status = "BYE"
                    winner_id = p2_id
                    winner_label = p2_label

            cur = db.execute(
                """
                INSERT INTO matches
                    (competition_id, round_number, round_name, match_order,
                     participant1_id, participant2_id, participant1_label, participant2_label,
                     score1, score2, winner_id, winner_label, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?)
                """,
                (
                    competition_id, r, round_name, m_order,
                    p1_id, p2_id, p1_label, p2_label,
                    winner_id, winner_label, status,
                ),
            )
            matches_by_round[r].append(
                {
                    "id": cur.lastrowid,
                    "match_order": m_order,
                    "winner_id": winner_id,
                    "winner_label": winner_label,
                }
            )

    # Majukan otomatis pemenang BYE dari babak 1 ke babak 2
    if total_rounds >= 2:
        for m in matches_by_round[1]:
            if m["winner_id"]:
                _propagate_winner_to_next_round(
                    db, competition_id, 1, m["match_order"], m["winner_id"], m["winner_label"]
                )

    db.commit()
    return True, get_bracket_data(db, competition_id)


def _propagate_winner_to_next_round(db, competition_id: int, round_number: int, match_order: int, winner_id, winner_label: str):
    """Memasukkan pemenang dari suatu pertandingan ke slot yang tepat di babak berikutnya."""
    next_round = round_number + 1
    next_order = (match_order + 1) // 2
    next_match = db.execute(
        """
        SELECT * FROM matches
        WHERE competition_id = ? AND round_number = ? AND match_order = ?
        """,
        (competition_id, next_round, next_order),
    ).fetchone()

    if not next_match:
        return  # Sudah berada di babak Final

    if match_order % 2 == 1:
        db.execute(
            """
            UPDATE matches
            SET participant1_id = ?, participant1_label = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (winner_id, winner_label or "TBD", next_match["id"]),
        )
    else:
        db.execute(
            """
            UPDATE matches
            SET participant2_id = ?, participant2_label = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (winner_id, winner_label or "TBD", next_match["id"]),
        )

    # Jika di babak berikutnya sebelumnya sudah ada pemenang yang tidak lagi valid, reset ke downstream
    if next_match["winner_id"] and next_match["winner_id"] not in (
        winner_id if match_order % 2 == 1 else next_match["participant1_id"],
        winner_id if match_order % 2 == 0 else next_match["participant2_id"],
    ):
        db.execute(
            """
            UPDATE matches
            SET winner_id = NULL, winner_label = '', status = 'PENDING', score1 = 0, score2 = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (next_match["id"],),
        )
        _propagate_winner_to_next_round(db, competition_id, next_round, next_order, None, "TBD")


def update_match(db, match_id: int, score1=None, score2=None, status=None, winner_slot=None, scheduled_time=None) -> tuple:
    """
    Memperbarui skor, status (PENDING/LIVE/COMPLETED), jadwal, dan/atau pemenang pertandingan.
    Jika pemenang dipilih (winner_slot = 1 atau 2), pemenang otomatis maju ke babak berikutnya.
    """
    match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not match:
        return False, "Pertandingan tidak ditemukan."

    new_score1 = match["score1"] if score1 is None else int(score1)
    new_score2 = match["score2"] if score2 is None else int(score2)
    new_status = match["status"] if not status else status.upper()
    new_sched = match["scheduled_time"] if scheduled_time is None else scheduled_time.strip()
    winner_id = match["winner_id"]
    winner_label = match["winner_label"]
    advanced = False

    if winner_slot in (1, "1"):
        if not match["participant1_id"]:
            return False, "Slot peserta 1 masih kosong (TBD)."
        winner_id = match["participant1_id"]
        winner_label = match["participant1_label"]
        new_status = "COMPLETED"
        advanced = True
    elif winner_slot in (2, "2"):
        if not match["participant2_id"]:
            return False, "Slot peserta 2 masih kosong (TBD)."
        winner_id = match["participant2_id"]
        winner_label = match["participant2_label"]
        new_status = "COMPLETED"
        advanced = True
    elif winner_slot in (0, "0", "clear"):
        winner_id = None
        winner_label = ""
        if new_status == "COMPLETED":
            new_status = "PENDING"
        _propagate_winner_to_next_round(
            db, match["competition_id"], match["round_number"], match["match_order"], None, "TBD"
        )

    db.execute(
        """
        UPDATE matches
        SET score1 = ?, score2 = ?, status = ?, winner_id = ?, winner_label = ?,
            scheduled_time = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (new_score1, new_score2, new_status, winner_id, winner_label, new_sched, match_id),
    )

    if advanced and winner_id:
        _propagate_winner_to_next_round(
            db, match["competition_id"], match["round_number"], match["match_order"], winner_id, winner_label
        )

    db.commit()

    # Cek apakah ini pertandingan Final yang baru saja selesai
    max_round = db.execute(
        "SELECT MAX(round_number) AS mr FROM matches WHERE competition_id = ?",
        (match["competition_id"],),
    ).fetchone()["mr"]
    is_champion = bool(advanced and match["round_number"] == max_round)

    return True, {
        "bracket": get_bracket_data(db, match["competition_id"]),
        "advanced": advanced,
        "is_champion": is_champion,
        "winner_label": winner_label,
    }


def toggle_bracket_lock(db, competition_id: int) -> tuple:
    """Mengunci atau membuka kunci bracket oleh panitia."""
    comp = db.execute("SELECT * FROM competitions WHERE id = ?", (competition_id,)).fetchone()
    if not comp:
        return False, "Cabang lomba tidak ditemukan."
    new_val = 0 if comp["bracket_locked"] else 1
    db.execute("UPDATE competitions SET bracket_locked = ? WHERE id = ?", (new_val, competition_id))
    db.commit()
    return True, {"bracket_locked": bool(new_val)}


def get_bracket_data(db, competition_id: int) -> dict:
    """Mengembalikan data bracket lengkap yang siap dirender di UI."""
    comp = db.execute(
        """
        SELECT c.*, e.name AS event_name, e.slug AS event_slug
        FROM competitions c
        JOIN events e ON e.id = c.event_id
        WHERE c.id = ?
        """,
        (competition_id,),
    ).fetchone()
    if not comp:
        return None

    rows = db.execute(
        """
        SELECT * FROM matches
        WHERE competition_id = ?
        ORDER BY round_number ASC, match_order ASC
        """,
        (competition_id,),
    ).fetchall()

    rounds_map = {}
    for r in rows:
        rn = r["round_number"]
        if rn not in rounds_map:
            rounds_map[rn] = {
                "round_number": rn,
                "round_name": r["round_name"],
                "matches": [],
            }
        rounds_map[rn]["matches"].append(dict(r))

    rounds = [rounds_map[k] for k in sorted(rounds_map.keys())]
    champion = None
    if rounds:
        final_matches = rounds[-1]["matches"]
        if final_matches and final_matches[0]["winner_id"]:
            champion = final_matches[0]["winner_label"]

    eligible_count = len(get_eligible_participants(db, competition_id))

    return {
        "competition": dict(comp),
        "bracket_locked": bool(comp["bracket_locked"]),
        "eligible_count": eligible_count,
        "rounds": rounds,
        "champion": champion,
    }
