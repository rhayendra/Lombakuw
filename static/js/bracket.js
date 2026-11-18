/**
 * Lombaku Interactive Tournament Bracket Engine
 * Mendukung mode siswa (read-only interaktif) & mode panitia (Generate, Shuffle, Lock, Skor & Advance Winner).
 * Responsif di HP dengan mode Tab Per Babak maupun Horizontal Scroll + Zoom.
 */
document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("bracketApp");
  if (!root) return;

  const isAdminMode = root.dataset.adminMode === "true";
  const compSelect = document.getElementById("bracketCompSelect");
  const viewport = document.getElementById("bracketViewport");
  const canvas = document.getElementById("bracketCanvas");
  const championWrap = document.getElementById("bracketChampionBanner");
  const mobileTabs = document.getElementById("mobileRoundTabs");
  const lockBadge = document.getElementById("bracketLockBadge");

  // Controls
  const btnZoomIn = document.getElementById("btnBracketZoomIn");
  const btnZoomOut = document.getElementById("btnBracketZoomOut");
  const btnZoomReset = document.getElementById("btnBracketZoomReset");
  const btnMobileMode = document.getElementById("btnBracketMobileMode");

  // Admin controls
  const btnGenerate = document.getElementById("btnBracketGenerate");
  const btnShuffle = document.getElementById("btnBracketShuffle");
  const btnLock = document.getElementById("btnBracketLock");

  let currentCompId = parseInt(root.dataset.competitionId || "0", 10);
  let bracketState = null;
  let zoomLevel = 1;
  let mobileActiveRound = 1;
  let mobileTabbed = window.innerWidth <= 820;

  try {
    const initialEl = document.getElementById("initialBracketData");
    if (initialEl && initialEl.textContent.trim()) {
      bracketState = JSON.parse(initialEl.textContent);
    }
  } catch {
    bracketState = null;
  }

  function applyZoom() {
    if (!canvas) return;
    canvas.style.transform = `scale(${zoomLevel})`;
  }

  if (btnZoomIn) btnZoomIn.addEventListener("click", () => { zoomLevel = Math.min(1.25, +(zoomLevel + 0.1).toFixed(2)); applyZoom(); });
  if (btnZoomOut) btnZoomOut.addEventListener("click", () => { zoomLevel = Math.max(0.65, +(zoomLevel - 0.1).toFixed(2)); applyZoom(); });
  if (btnZoomReset) btnZoomReset.addEventListener("click", () => { zoomLevel = 1; applyZoom(); });

  if (btnMobileMode) {
    btnMobileMode.addEventListener("click", () => {
      mobileTabbed = !mobileTabbed;
      btnMobileMode.textContent = mobileTabbed ? "Mode: Per Babak" : "Mode: Geser Penuh";
      renderBracket();
    });
  }

  function renderBracket(highlightRound = null) {
    if (!canvas) return;

    if (!bracketState || !bracketState.rounds || !bracketState.rounds.length) {
      championWrap.innerHTML = "";
      mobileTabs.innerHTML = "";
      canvas.innerHTML = `
        <div class="glass-sub card-pad" style="min-width:300px;max-width:520px;margin:24px auto;text-align:center;">
          <div style="font-size:1.1rem;font-weight:600;margin-bottom:6px;">Bracket Belum Dibuat</div>
          <p style="color:var(--text-secondary);font-size:0.88rem;margin:0;">
            ${isAdminMode
              ? `Tersedia <strong>${bracketState ? bracketState.eligible_count : 0}</strong> peserta siap tanding. Tekan tombol <strong>Buat Bracket</strong> atau <strong>Shuffle</strong> di atas.`
              : "Panitia belum mempublikasikan bagan pertandingan untuk cabang lomba ini."}
          </p>
        </div>
      `;
      updateAdminHeader();
      return;
    }

    updateAdminHeader();

    // Champion Banner
    if (bracketState.champion) {
      championWrap.innerHTML = `
        <div class="champion-banner">
          <div style="display:flex;align-items:center;gap:14px;">
            <div style="width:46px;height:46px;border-radius:14px;background:rgba(245,181,68,0.22);border:1px solid rgba(245,181,68,0.5);display:flex;align-items:center;justify-content:center;font-size:1.35rem;">🏆</div>
            <div>
              <div style="font-size:0.72rem;letter-spacing:0.14em;text-transform:uppercase;color:#fcd34d;font-weight:700;">Juara Cabang ${LombakuUI.escapeHtml(bracketState.competition.name)}</div>
              <div style="font-size:1.3rem;font-weight:700;color:#fff;">${LombakuUI.escapeHtml(bracketState.champion)}</div>
            </div>
          </div>
          <span class="status-badge status-live">Champion Terkonfirmasi</span>
        </div>
      `;
    } else {
      championWrap.innerHTML = "";
    }

    // Mobile Round Tabs
    const totalRounds = bracketState.rounds.length;
    if (mobileActiveRound > totalRounds) mobileActiveRound = 1;
    mobileTabs.innerHTML = bracketState.rounds
      .map(
        (r) => `
          <button type="button" class="btn-glass btn-sm ${r.round_number === mobileActiveRound ? "btn-primary" : ""}" data-mobile-round="${r.round_number}">
            ${LombakuUI.escapeHtml(r.round_name)}
          </button>
        `
      )
      .join("");

    mobileTabs.querySelectorAll("[data-mobile-round]").forEach((btn) => {
      btn.addEventListener("click", () => {
        mobileActiveRound = parseInt(btn.dataset.mobileRound, 10);
        renderBracket();
      });
    });

    canvas.classList.toggle("mobile-tabbed-mode", mobileTabbed && window.innerWidth <= 820);

    canvas.innerHTML = bracketState.rounds
      .map((round) => {
        const isFinal = round.round_number === totalRounds;
        const isActiveMobile = round.round_number === mobileActiveRound;

        const matchesHtml = round.matches
          .map((m) => {
            const p1Win = m.winner_id && m.winner_id === m.participant1_id;
            const p2Win = m.winner_id && m.winner_id === m.participant2_id;
            const isLive = m.status === "LIVE";
            const statusClass =
              m.status === "LIVE"
                ? "status-live"
                : m.status === "COMPLETED"
                ? "status-accepted"
                : m.status === "BYE"
                ? "status-completed"
                : "status-registered";

            const justAdvanced = highlightRound && round.round_number === highlightRound;

            const adminControls = isAdminMode && m.status !== "BYE"
              ? `
                <div class="match-admin-bar" data-match-id="${m.id}">
                  <div class="match-score-inputs">
                    <input type="number" min="0" class="score-mini-input inp-score1" value="${m.score1}" aria-label="Skor 1">
                    <span style="font-size:0.7rem;color:var(--text-muted);">vs</span>
                    <input type="number" min="0" class="score-mini-input inp-score2" value="${m.score2}" aria-label="Skor 2">
                  </div>
                  <div class="match-action-btns">
                    <button type="button" class="mini-pill-btn btn-save-score" title="Simpan skor" data-no-click-sound>Simpan</button>
                    <button type="button" class="mini-pill-btn btn-toggle-live" title="Tandai Live" data-no-click-sound>${isLive ? "Stop Live" : "Set LIVE"}</button>
                  </div>
                  <div class="match-action-btns">
                    <button type="button" class="mini-pill-btn win-btn btn-win-1" data-no-click-sound ${!m.participant1_id ? "disabled style='opacity:0.4'" : ""}>★ Menang 1</button>
                    <button type="button" class="mini-pill-btn win-btn btn-win-2" data-no-click-sound ${!m.participant2_id ? "disabled style='opacity:0.4'" : ""}>★ Menang 2</button>
                  </div>
                </div>
              `
              : "";

            return `
              <div class="match-node ${isLive ? "is-live" : ""} ${justAdvanced ? "is-just-advanced" : ""}">
                <div class="match-meta-bar">
                  <span>Match #${m.match_order}${m.scheduled_time ? " · " + LombakuUI.escapeHtml(m.scheduled_time) : ""}</span>
                  <span class="status-badge ${statusClass}" style="padding:2px 8px;font-size:0.62rem;">
                    ${isLive ? '<span class="status-dot"></span>' : ""}${LombakuUI.escapeHtml(m.status)}
                  </span>
                </div>
                <div class="match-slot ${p1Win ? (isFinal ? "is-winner is-champion-slot" : "is-winner") : ""} ${m.participant1_label === "BYE" ? "is-bye" : ""}">
                  <span class="slot-name" title="${LombakuUI.escapeHtml(m.participant1_label)}">${LombakuUI.escapeHtml(m.participant1_label)}</span>
                  <span class="slot-score">${m.score1}</span>
                </div>
                <div class="match-slot ${p2Win ? (isFinal ? "is-winner is-champion-slot" : "is-winner") : ""} ${m.participant2_label === "BYE" ? "is-bye" : ""}">
                  <span class="slot-name" title="${LombakuUI.escapeHtml(m.participant2_label)}">${LombakuUI.escapeHtml(m.participant2_label)}</span>
                  <span class="slot-score">${m.score2}</span>
                </div>
                ${adminControls}
              </div>
            `;
          })
          .join("");

        return `
          <div class="bracket-round-col ${isActiveMobile ? "mobile-active-round" : ""}">
            <div class="bracket-round-header">${LombakuUI.escapeHtml(round.round_name)}</div>
            <div class="bracket-round-matches">${matchesHtml}</div>
          </div>
        `;
      })
      .join("");

    if (isAdminMode) bindAdminMatchEvents();
  }

  function updateAdminHeader() {
    if (!bracketState) return;
    const locked = Boolean(bracketState.bracket_locked);
    if (lockBadge) {
      lockBadge.className = `status-badge ${locked ? "status-locked" : "status-open"}`;
      lockBadge.innerHTML = `<span class="status-dot"></span> ${locked ? "Bracket Terkunci" : "Terbuka"}`;
    }
    if (btnLock) {
      btnLock.textContent = locked ? "Buka Kunci Bracket" : "Kunci Bracket";
    }
    if (btnShuffle) btnShuffle.disabled = locked;
    if (btnGenerate) btnGenerate.disabled = locked;
  }

  function bindAdminMatchEvents() {
    canvas.querySelectorAll(".match-admin-bar").forEach((bar) => {
      const matchId = bar.dataset.matchId;
      const s1Inp = bar.querySelector(".inp-score1");
      const s2Inp = bar.querySelector(".inp-score2");

      async function sendUpdate(payload, nextRoundHighlight = null) {
        try {
          const res = await fetch(`/api/admin/match/${matchId}/update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          const json = await res.json();
          if (!res.ok || !json.ok) {
            LombakuSound.play("error");
            LombakuUI.toast(json.error || "Gagal memperbarui pertandingan.", "error");
            return;
          }
          bracketState = json.bracket;
          if (json.is_champion) {
            LombakuSound.play("winner");
            LombakuUI.toast(`🏆 Selamat! ${json.winner_label} menjadi JUARA!`, "success", 5800);
          } else if (json.advanced) {
            LombakuSound.play("advance");
            LombakuUI.toast(`${json.winner_label} melaju ke babak berikutnya!`, "success");
          } else {
            LombakuSound.play(payload.status === "LIVE" ? "open" : "submit");
            LombakuUI.toast("Data pertandingan berhasil diperbarui.", "info");
          }
          renderBracket(nextRoundHighlight);
          if (json.is_champion) {
            LombakuUI.celebrate(championWrap, "winner");
          }
        } catch {
          LombakuSound.play("error");
          LombakuUI.toast("Gagal menghubungi server.", "error");
        }
      }

      const roundCol = bar.closest(".bracket-round-col");
      const roundIdx = Array.from(canvas.querySelectorAll(".bracket-round-col")).indexOf(roundCol) + 1;

      bar.querySelector(".btn-save-score").addEventListener("click", () => {
        sendUpdate({ score1: parseInt(s1Inp.value || "0", 10), score2: parseInt(s2Inp.value || "0", 10) });
      });

      bar.querySelector(".btn-toggle-live").addEventListener("click", (e) => {
        const setTo = e.target.textContent.includes("Stop") ? "PENDING" : "LIVE";
        sendUpdate({
          score1: parseInt(s1Inp.value || "0", 10),
          score2: parseInt(s2Inp.value || "0", 10),
          status: setTo,
        });
      });

      bar.querySelector(".btn-win-1").addEventListener("click", () => {
        sendUpdate(
          { score1: parseInt(s1Inp.value || "0", 10), score2: parseInt(s2Inp.value || "0", 10), winner_slot: 1 },
          roundIdx + 1
        );
      });

      bar.querySelector(".btn-win-2").addEventListener("click", () => {
        sendUpdate(
          { score1: parseInt(s1Inp.value || "0", 10), score2: parseInt(s2Inp.value || "0", 10), winner_slot: 2 },
          roundIdx + 1
        );
      });
    });
  }

  // Admin toolbar buttons
  if (btnGenerate) {
    btnGenerate.addEventListener("click", async () => {
      if (!currentCompId) return;
      const res = await fetch(`/api/admin/bracket/${currentCompId}/generate`, { method: "POST" });
      const json = await res.json();
      if (!json.ok) {
        LombakuSound.play("error");
        LombakuUI.toast(json.error, "error");
        return;
      }
      bracketState = json.bracket;
      LombakuSound.play("open");
      LombakuUI.toast(json.message, "success");
      renderBracket();
    });
  }

  if (btnShuffle) {
    btnShuffle.addEventListener("click", async () => {
      if (!currentCompId) return;
      canvas.classList.add("is-shuffling");
      LombakuSound.play("shuffle");
      try {
        const res = await fetch(`/api/admin/bracket/${currentCompId}/shuffle`, { method: "POST" });
        const json = await res.json();
        setTimeout(() => {
          canvas.classList.remove("is-shuffling");
          if (!json.ok) {
            LombakuSound.play("error");
            LombakuUI.toast(json.error, "error");
            return;
          }
          bracketState = json.bracket;
          LombakuUI.toast("Bracket berhasil diacak secara random!", "success");
          renderBracket();
        }, 480);
      } catch {
        canvas.classList.remove("is-shuffling");
        LombakuUI.toast("Gagal mengacak bracket.", "error");
      }
    });
  }

  if (btnLock) {
    btnLock.addEventListener("click", async () => {
      if (!currentCompId) return;
      const res = await fetch(`/api/admin/bracket/${currentCompId}/lock`, { method: "POST" });
      const json = await res.json();
      if (!json.ok) {
        LombakuSound.play("error");
        LombakuUI.toast(json.error, "error");
        return;
      }
      bracketState.bracket_locked = json.bracket_locked;
      LombakuSound.play(json.bracket_locked ? "lock" : "open");
      LombakuUI.toast(json.message, "info");
      updateAdminHeader();
    });
  }

  // Switch competition dropdown
  if (compSelect) {
    compSelect.addEventListener("change", () => {
      const target = isAdminMode ? `/admin/bracket?competition_id=${compSelect.value}` : `/bracket?competition_id=${compSelect.value}`;
      window.location.href = target;
    });
  }

  renderBracket();
});
