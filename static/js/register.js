/**
 * Lombaku Registration Controller
 * Menangani:
 * 1. Pemilih Event & Cabang Lomba
 * 2. Gerbang wajib baca Tab Juknis sebelum form pendaftaran terbuka
 * 3. Form dinamis Individu vs Tim (mengikuti min/max anggota & wajib satu kelas)
 * 4. Validasi + Pengiriman AJAX ke backend Python
 * 5. Cek Status Pendaftaran via NIS / Kode Daftar
 */
document.addEventListener("DOMContentLoaded", () => {
  const eventSelect = document.getElementById("regEventSelect");
  const compSelect = document.getElementById("regCompSelect");
  const eventsDataEl = document.getElementById("regEventsData");
  if (!eventSelect || !compSelect || !eventsDataEl) return;

  const eventsData = JSON.parse(eventsDataEl.textContent || "[]");
  const tabJuknisBtn = document.getElementById("tabBtnJuknis");
  const tabFormBtn = document.getElementById("tabBtnForm");
  const tabStatusBtn = document.getElementById("tabBtnStatus");
  const paneJuknis = document.getElementById("paneJuknis");
  const paneForm = document.getElementById("paneForm");
  const paneStatus = document.getElementById("paneStatus");

  const juknisEventText = document.getElementById("juknisEventText");
  const juknisCompText = document.getElementById("juknisCompText");
  const juknisMetaBadges = document.getElementById("juknisMetaBadges");
  const juknisUnlockBtn = document.getElementById("btnUnlockForm");
  const juknisGateNotice = document.getElementById("juknisGateNotice");
  const regLockBanner = document.getElementById("regLockBanner");

  const regForm = document.getElementById("registrationForm");
  const teamSection = document.getElementById("teamFieldsSection");
  const membersList = document.getElementById("teamMembersContainer");
  const btnAddMember = document.getElementById("btnAddMember");
  const teamRuleHint = document.getElementById("teamRuleHint");
  const labelParticipantName = document.getElementById("labelParticipantName");
  const labelNis = document.getElementById("labelNis");
  const labelKelas = document.getElementById("labelKelas");
  const inputKelas = document.getElementById("regKelas");
  const submitBtn = document.getElementById("btnSubmitRegistration");
  const receiptBox = document.getElementById("registrationReceipt");

  let activeComp = null;
  let juknisReadForCompId = null;

  function switchTab(tabName) {
    if (tabName === "form") {
      if (!activeComp) {
        LombakuUI.toast("Pilih event dan cabang lomba terlebih dahulu.", "warning");
        return;
      }
      if (juknisReadForCompId !== activeComp.id) {
        LombakuSound.play("lock");
        LombakuUI.toast("Buka dan baca Tab Juknis terlebih dahulu sebelum mengisi formulir.", "warning");
        tabName = "juknis";
      }
    }

    [
      [tabJuknisBtn, paneJuknis, "juknis"],
      [tabFormBtn, paneForm, "form"],
      [tabStatusBtn, paneStatus, "status"],
    ].forEach(([btn, pane, key]) => {
      const isAct = key === tabName;
      btn.classList.toggle("active", isAct);
      pane.style.display = isAct ? "block" : "none";
    });
  }

  tabJuknisBtn.addEventListener("click", () => switchTab("juknis"));
  tabFormBtn.addEventListener("click", () => switchTab("form"));
  tabStatusBtn.addEventListener("click", () => switchTab("status"));

  function populateCompetitions(eventId, preselectCompId = null) {
    const ev = eventsData.find((e) => String(e.id) === String(eventId));
    compSelect.innerHTML = "";
    if (!ev || !ev.competitions || !ev.competitions.length) {
      compSelect.innerHTML = `<option value="">-- Belum ada cabang lomba --</option>`;
      activeComp = null;
      return;
    }

    ev.competitions.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      const typeTag = c.comp_type === "TEAM" ? `Tim (${c.min_members}-${c.max_members} org)` : "Individu";
      opt.textContent = `${c.name} · ${typeTag}`;
      if (preselectCompId && String(c.id) === String(preselectCompId)) {
        opt.selected = true;
      }
      compSelect.appendChild(opt);
    });

    loadCompetitionDetail(compSelect.value);
  }

  async function loadCompetitionDetail(compId) {
    if (!compId) return;
    receiptBox.style.display = "none";
    juknisReadForCompId = null;
    tabFormBtn.classList.add("is-locked-tab");

    try {
      const res = await fetch(`/api/competition/${compId}`);
      const json = await res.json();
      if (!json.ok) throw new Error(json.error || "Gagal memuat detail cabang.");
      activeComp = json.competition;
      renderCompetitionContext();
      switchTab("juknis");
    } catch (err) {
      LombakuUI.toast(err.message, "error");
    }
  }

  function renderCompetitionContext() {
    if (!activeComp) return;
    const isTeam = activeComp.comp_type === "TEAM";

    juknisEventText.textContent = activeComp.event_juknis || "Mengikuti peraturan umum panitia sekolah.";
    juknisCompText.textContent = activeComp.juknis || activeComp.description || "Detail juknis belum diisi panitia.";

    const badges = [
      `<span class="glass-chip">${isTeam ? "Lomba Tim" : "Lomba Individu"}</span>`,
      `<span class="glass-chip">Kuota: ${activeComp.registered_count} / ${activeComp.max_slots}</span>`,
      activeComp.venue ? `<span class="glass-chip">Lokasi: ${LombakuUI.escapeHtml(activeComp.venue)}</span>` : "",
      activeComp.schedule_info ? `<span class="glass-chip">Jadwal: ${LombakuUI.escapeHtml(activeComp.schedule_info)}</span>` : "",
      isTeam ? `<span class="glass-chip">Anggota: ${activeComp.min_members}–${activeComp.max_members} orang</span>` : "",
      isTeam && activeComp.same_class_required ? `<span class="glass-chip" style="border-color:rgba(245,181,68,0.4);color:#fde68a;">Wajib Satu Kelas</span>` : "",
    ].filter(Boolean);
    juknisMetaBadges.innerHTML = badges.join("");

    // Status kunci event otomatis
    if (!activeComp.can_register) {
      regLockBanner.style.display = "flex";
      regLockBanner.innerHTML = `<span>▲</span><div><strong>Pendaftaran ${LombakuUI.escapeHtml(activeComp.event_effective_status)}:</strong> ${LombakuUI.escapeHtml(activeComp.status_reason)}</div>`;
      juknisUnlockBtn.disabled = true;
      juknisUnlockBtn.textContent = `Pendaftaran ${activeComp.event_effective_status}`;
    } else if (activeComp.registered_count >= activeComp.max_slots) {
      regLockBanner.style.display = "flex";
      regLockBanner.innerHTML = `<span>▲</span><div><strong>Kuota Penuh:</strong> Cabang lomba ini telah mencapai batas maksimal ${activeComp.max_slots} slot.</div>`;
      juknisUnlockBtn.disabled = true;
      juknisUnlockBtn.textContent = "Kuota Penuh";
    } else {
      regLockBanner.style.display = "none";
      juknisUnlockBtn.disabled = false;
      juknisUnlockBtn.textContent = "Saya Sudah Membaca Juknis — Lanjut ke Formulir →";
    }

    // Sesuaikan form individu vs tim
    if (isTeam) {
      teamSection.style.display = "block";
      labelParticipantName.textContent = "Nama Ketua Tim *";
      labelNis.textContent = "NIS Ketua Tim *";
      labelKelas.textContent = activeComp.same_class_required ? "Kelas Tim (Wajib Sama) *" : "Kelas Ketua Tim *";
      teamRuleHint.textContent =
        `Minimal ${activeComp.min_members} orang, maksimal ${activeComp.max_members} orang (sudah termasuk Ketua Tim). ` +
        (activeComp.same_class_required
          ? "Seluruh anggota wajib berasal dari kelas yang sama."
          : "Anggota boleh berasal dari kelas yang berbeda.");
      rebuildMemberRows();
    } else {
      teamSection.style.display = "none";
      labelParticipantName.textContent = "Nama Lengkap Siswa *";
      labelNis.textContent = "Nomor Induk Siswa (NIS) *";
      labelKelas.textContent = "Kelas *";
      membersList.innerHTML = "";
    }
  }

  function rebuildMemberRows() {
    membersList.innerHTML = "";
    const extraMin = Math.max(0, activeComp.min_members - 1);
    for (let i = 0; i < extraMin; i++) {
      addMemberRow(true);
    }
    updateAddMemberButton();
  }

  function addMemberRow(isRequired = false) {
    if (!activeComp) return;
    const maxExtra = Math.max(0, activeComp.max_members - 1);
    const currentRows = membersList.querySelectorAll(".member-row").length;
    if (currentRows >= maxExtra) {
      LombakuUI.toast(`Maksimal ${activeComp.max_members} orang per tim (termasuk ketua).`, "warning");
      return;
    }

    const rowIdx = currentRows + 2; // Anggota ke-2 dst (ketua = 1)
    const row = document.createElement("div");
    row.className = "member-row";
    const lockedClass = activeComp.same_class_required;
    const defaultKelas = lockedClass ? inputKelas.value : "";

    row.innerHTML = `
      <span class="member-num">${rowIdx}</span>
      <input type="text" class="glass-input member-name" placeholder="Nama Anggota ${rowIdx}" required>
      <input type="text" class="glass-input member-nis" placeholder="NIS Anggota ${rowIdx}" required>
      <input type="text" class="glass-input member-kelas" placeholder="Kelas" value="${LombakuUI.escapeHtml(defaultKelas)}" ${lockedClass ? "readonly" : ""} required>
      ${isRequired ? `<span class="glass-chip" style="justify-content:center;">Wajib</span>` : `<button type="button" class="btn-glass btn-sm btn-danger btn-remove-member">Hapus</button>`}
    `;

    const rmBtn = row.querySelector(".btn-remove-member");
    if (rmBtn) {
      rmBtn.addEventListener("click", () => {
        row.remove();
        renumberMemberRows();
        updateAddMemberButton();
      });
    }

    membersList.appendChild(row);
    updateAddMemberButton();
  }

  function renumberMemberRows() {
    membersList.querySelectorAll(".member-row").forEach((row, i) => {
      const badge = row.querySelector(".member-num");
      if (badge) badge.textContent = i + 2;
    });
  }

  function updateAddMemberButton() {
    if (!activeComp || !btnAddMember) return;
    const maxExtra = Math.max(0, activeComp.max_members - 1);
    const cur = membersList.querySelectorAll(".member-row").length;
    btnAddMember.style.display = cur < maxExtra ? "inline-flex" : "none";
  }

  // Sinkronkan kelas anggota otomatis jika cabang mewajibkan satu kelas
  inputKelas.addEventListener("input", () => {
    if (activeComp && activeComp.same_class_required) {
      membersList.querySelectorAll(".member-kelas").forEach((inp) => {
        inp.value = inputKelas.value;
      });
    }
  });

  if (btnAddMember) {
    btnAddMember.addEventListener("click", () => addMemberRow(false));
  }

  // Buka kunci Tab Formulir setelah membaca Juknis
  juknisUnlockBtn.addEventListener("click", () => {
    if (!activeComp || !activeComp.can_register) return;
    juknisReadForCompId = activeComp.id;
    tabFormBtn.classList.remove("is-locked-tab");
    if (juknisGateNotice) {
      juknisGateNotice.innerHTML = `<span>✦</span><div>Juknis <strong>${LombakuUI.escapeHtml(activeComp.name)}</strong> telah dikonfirmasi. Formulir pendaftaran kini aktif!</div>`;
    }
    LombakuSound.play("open");
    LombakuUI.toast("Formulir pendaftaran dibuka! Silakan lengkapi data Anda.", "success");
    switchTab("form");
  });

  // Submit pendaftaran ke backend API
  regForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!activeComp) return;
    if (juknisReadForCompId !== activeComp.id) {
      LombakuSound.play("error");
      LombakuUI.toast("Anda wajib membaca tab Juknis terlebih dahulu.", "warning");
      switchTab("juknis");
      return;
    }

    const members = [];
    if (activeComp.comp_type === "TEAM") {
      membersList.querySelectorAll(".member-row").forEach((row) => {
        members.push({
          name: row.querySelector(".member-name").value.trim(),
          nis: row.querySelector(".member-nis").value.trim(),
          kelas: row.querySelector(".member-kelas").value.trim(),
        });
      });
    }

    const payload = {
      competition_id: activeComp.id,
      juknis_confirmed: true,
      participant_name: document.getElementById("regParticipantName").value.trim(),
      nis: document.getElementById("regNis").value.trim(),
      kelas: inputKelas.value.trim(),
      contact: document.getElementById("regContact").value.trim(),
      team_name: document.getElementById("regTeamName") ? document.getElementById("regTeamName").value.trim() : "",
      notes: document.getElementById("regNotes").value.trim(),
      members,
    };

    submitBtn.disabled = true;
    const origText = submitBtn.textContent;
    submitBtn.textContent = "Memvalidasi & Menyimpan...";

    try {
      const res = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (!res.ok || !json.ok) {
        LombakuSound.play("error");
        LombakuUI.toast(json.error || "Pendaftaran gagal.", "error", 5500);
        return;
      }

      const r = json.registration;
      LombakuSound.play("submit");
      LombakuUI.toast(`Pendaftaran berhasil! Kode Anda: ${r.registration_code}`, "success", 6000);

      receiptBox.style.display = "block";
      LombakuUI.celebrate(receiptBox, "success");
      receiptBox.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
          <strong style="font-size:1.02rem;color:#a7f3d0;">✦ Pendaftaran Berhasil Tercatat!</strong>
          <span class="status-badge status-registered"><span class="status-dot"></span> ${LombakuUI.escapeHtml(r.status)}</span>
        </div>
        <div style="font-size:0.9rem;color:var(--text-secondary);line-height:1.7;">
          Kode Pendaftaran: <strong style="color:#fff;font-size:1rem;">${LombakuUI.escapeHtml(r.registration_code)}</strong><br>
          Event & Cabang: <strong>${LombakuUI.escapeHtml(r.event_name)} — ${LombakuUI.escapeHtml(r.competition_name)}</strong><br>
          Peserta / Tim: <strong>${LombakuUI.escapeHtml(r.participant_name)}</strong>
        </div>
        <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap;">
          <a href="/bracket?competition_id=${activeComp.id}" class="btn-glass btn-sm btn-primary">Lihat Bracket Lomba</a>
          <button type="button" class="btn-glass btn-sm" id="btnCheckMyCode">Cek di Tab Status</button>
        </div>
      `;

      const checkBtn = document.getElementById("btnCheckMyCode");
      if (checkBtn) {
        checkBtn.addEventListener("click", () => {
          document.getElementById("statusSearchInput").value = r.registration_code;
          switchTab("status");
          runStatusLookup(r.registration_code);
        });
      }

      regForm.reset();
      if (activeComp.comp_type === "TEAM") rebuildMemberRows();
    } catch {
      LombakuSound.play("error");
      LombakuUI.toast("Terjadi gangguan koneksi ke server.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = origText;
    }
  });

  // Cek Status Pendaftaran via NIS / Kode
  const statusForm = document.getElementById("statusLookupForm");
  const statusResults = document.getElementById("statusLookupResults");

  async function runStatusLookup(q) {
    if (!q) return;
    statusResults.innerHTML = `<div class="skeleton" style="height:82px;margin-top:12px;"></div>`;
    try {
      const res = await fetch(`/api/registration/status?q=${encodeURIComponent(q)}`);
      const json = await res.json();
      if (!json.ok) {
        statusResults.innerHTML = `<div class="alert-glass alert-warning" style="margin-top:12px;">${LombakuUI.escapeHtml(json.error)}</div>`;
        return;
      }
      if (!json.results.length) {
        statusResults.innerHTML = `<div class="alert-glass" style="margin-top:12px;">Belum ditemukan pendaftaran untuk NIS / Kode <strong>${LombakuUI.escapeHtml(q)}</strong>.</div>`;
        return;
      }
      statusResults.innerHTML = json.results
        .map((item) => {
          const stClass = `status-${item.status.toLowerCase()}`;
          const membersHtml =
            item.members && item.members.length
              ? `<div style="margin-top:8px;font-size:0.8rem;color:var(--text-muted);">Anggota: ${item.members
                  .map((m) => `${LombakuUI.escapeHtml(m.member_name)} (${LombakuUI.escapeHtml(m.member_nis)})`)
                  .join(", ")}</div>`
              : "";
          return `
            <div class="glass-sub card-pad-sm" style="margin-top:12px;">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
                <div>
                  <div style="font-weight:700;font-size:0.98rem;">${LombakuUI.escapeHtml(item.team_name || item.participant_name)}</div>
                  <div style="font-size:0.8rem;color:var(--text-secondary);">${LombakuUI.escapeHtml(item.event_name)} · ${LombakuUI.escapeHtml(item.competition_name)}</div>
                </div>
                <span class="status-badge ${stClass}"><span class="status-dot"></span> ${LombakuUI.escapeHtml(item.status)}</span>
              </div>
              <div class="event-chip-row">
                <span class="glass-chip">Kode: ${LombakuUI.escapeHtml(item.registration_code)}</span>
                <span class="glass-chip">NIS: ${LombakuUI.escapeHtml(item.nis)}</span>
                <span class="glass-chip">Kelas: ${LombakuUI.escapeHtml(item.kelas)}</span>
              </div>
              ${membersHtml}
            </div>
          `;
        })
        .join("");
    } catch {
      statusResults.innerHTML = `<div class="alert-glass alert-error" style="margin-top:12px;">Gagal memuat status pendaftaran.</div>`;
    }
  }

  if (statusForm) {
    statusForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = document.getElementById("statusSearchInput").value.trim();
      runStatusLookup(q);
    });
  }

  // Event listeners dropdown
  eventSelect.addEventListener("change", () => populateCompetitions(eventSelect.value));
  compSelect.addEventListener("change", () => loadCompetitionDetail(compSelect.value));

  // Init dari pre-selected query params
  const initEventId = eventSelect.dataset.selectedEvent || (eventsData[0] ? eventsData[0].id : "");
  const initCompId = compSelect.dataset.selectedComp || "";
  if (initEventId) {
    eventSelect.value = initEventId;
    populateCompetitions(initEventId, initCompId);
  }
});
