/**
 * Lombaku Hero Experience Controller
 * Mengatur perpindahan event (left vertical rail & orbital < > switcher),
 * countdown real-time menuju pelaksanaan event, serta transisi halus.
 */
document.addEventListener("DOMContentLoaded", () => {
  const dataEl = document.getElementById("heroEventsData");
  if (!dataEl) return;

  let events = [];
  try {
    events = JSON.parse(dataEl.textContent || "[]");
  } catch {
    return;
  }
  if (!events.length) return;

  let currentIdx = Math.max(0, events.findIndex((e) => e.is_featured));
  if (currentIdx === -1) currentIdx = 0;

  const centerEl = document.getElementById("heroCenterStage");
  const titleEl = document.getElementById("heroEventTitle");
  const subtitleEl = document.getElementById("heroEventSubtitle");
  const statusBadgeEl = document.getElementById("heroStatusBadge");
  const emblemTagEl = document.getElementById("heroEmblemTag");
  const emblemSvgWrap = document.getElementById("heroEmblemSvg");
  const glowEl = document.getElementById("heroSculptureGlow");
  const satParticipants = document.getElementById("heroSatParticipants");
  const satCompetitions = document.getElementById("heroSatCompetitions");
  const orbCounter = document.getElementById("heroOrbCounter");
  const btnDetail = document.getElementById("heroBtnDetail");
  const btnRegister = document.getElementById("heroBtnRegister");

  // Bottom telemetry elements
  const cdDays = document.getElementById("cdDays");
  const cdHours = document.getElementById("cdHours");
  const cdMins = document.getElementById("cdMins");
  const cdSecs = document.getElementById("cdSecs");
  const cdEventDate = document.getElementById("cdEventDate");
  const cdRingProgress = document.getElementById("cdRingProgress");
  const telParticipants = document.getElementById("telParticipants");
  const telCompetitions = document.getElementById("telCompetitions");
  const telStatusReason = document.getElementById("telStatusReason");
  const telDetailLink = document.getElementById("telDetailLink");

  const emblemIcons = {
    quill: `
      <svg class="emblem-svg" viewBox="0 0 80 80" fill="none">
        <defs>
          <linearGradient id="gQuill" x1="12" y1="10" x2="68" y2="70" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#E6F7FF"/>
            <stop offset="55%" stop-color="#52D1FF"/>
            <stop offset="100%" stop-color="#3B82F6"/>
          </linearGradient>
        </defs>
        <circle cx="40" cy="40" r="31" stroke="rgba(255,255,255,0.18)" stroke-width="1.2" stroke-dasharray="4 5"/>
        <path d="M58 18C42 20 28 32 22 54L18 62L26 58C46 53 58 38 58 18Z" stroke="url(#gQuill)" stroke-width="2.4" fill="rgba(82,209,255,0.12)" stroke-linejoin="round"/>
        <path d="M22 54L46 30" stroke="#E6F7FF" stroke-width="2" stroke-linecap="round"/>
        <circle cx="56" cy="20" r="3" fill="#F5B544"/>
      </svg>`,
    flame: `
      <svg class="emblem-svg" viewBox="0 0 80 80" fill="none">
        <defs>
          <linearGradient id="gFlame" x1="18" y1="12" x2="62" y2="68" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#E0F2FE"/>
            <stop offset="50%" stop-color="#60A5FA"/>
            <stop offset="100%" stop-color="#2563EB"/>
          </linearGradient>
        </defs>
        <circle cx="40" cy="40" r="31" stroke="rgba(255,255,255,0.18)" stroke-width="1.2" stroke-dasharray="4 5"/>
        <path d="M26 22H54V33C54 42 48 48 40 48C32 48 26 42 26 33V22Z" stroke="url(#gFlame)" stroke-width="2.4" fill="rgba(96,165,250,0.14)"/>
        <path d="M26 27H19C19 34 22 38 26 39M54 27H61C61 34 58 38 54 39" stroke="#E0F2FE" stroke-width="2" stroke-linecap="round"/>
        <path d="M40 48V58M31 58H49" stroke="#E0F2FE" stroke-width="2.4" stroke-linecap="round"/>
        <circle cx="40" cy="34" r="4" fill="#F5B544"/>
      </svg>`,
    star: `
      <svg class="emblem-svg" viewBox="0 0 80 80" fill="none">
        <defs>
          <linearGradient id="gStar" x1="16" y1="14" x2="64" y2="66" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#FEF3C7"/>
            <stop offset="55%" stop-color="#F5B544"/>
            <stop offset="100%" stop-color="#EA580C"/>
          </linearGradient>
        </defs>
        <circle cx="40" cy="40" r="31" stroke="rgba(255,255,255,0.18)" stroke-width="1.2" stroke-dasharray="4 5"/>
        <polygon points="40,16 46.5,31.5 63,33 50.5,44 54.2,60.5 40,51.8 25.8,60.5 29.5,44 17,33 33.5,31.5" stroke="url(#gStar)" stroke-width="2.3" fill="rgba(245,181,68,0.15)" stroke-linejoin="round"/>
        <circle cx="40" cy="40" r="4" fill="#FFF"/>
      </svg>`,
  };

  function statusClass(st) {
    if (st === "OPEN") return "status-open";
    if (st === "ONGOING") return "status-ongoing";
    if (st === "LOCKED") return "status-locked";
    if (st === "COMPLETED") return "status-completed";
    return "status-closed";
  }

  function statusTagText(st) {
    if (st === "OPEN") return "PENDAFTARAN DIBUKA";
    if (st === "ONGOING") return "SEDANG BERLANGSUNG";
    if (st === "COMPLETED") return "EVENT SELESAI";
    if (st === "LOCKED") return "TERKUNCI";
    return "SEGERA HADIR";
  }

  function renderEvent(idx, animate = true) {
    const ev = events[idx];
    if (!ev) return;

    const apply = () => {
      titleEl.innerHTML = `${LombakuUI.escapeHtml(ev.name)} <span class="hero-event-year">2026</span>`;
      subtitleEl.textContent = ev.subtitle || ev.description;

      statusBadgeEl.className = `status-badge ${statusClass(ev.effective_status)}`;
      statusBadgeEl.innerHTML = `<span class="status-dot"></span> ${LombakuUI.escapeHtml(ev.effective_status)}`;

      emblemTagEl.textContent = statusTagText(ev.effective_status);
      emblemSvgWrap.innerHTML = emblemIcons[ev.icon_type] || emblemIcons.flame;
      glowEl.className = `sculpture-glow accent-${ev.theme_accent || "cyan"}`;

      if (satParticipants) satParticipants.textContent = ev.participant_count;
      if (satCompetitions) satCompetitions.textContent = ev.competition_count;
      if (orbCounter) orbCounter.textContent = `0${idx + 1} / 0${events.length}`;

      if (btnDetail) btnDetail.href = `/events/${ev.slug}`;
      if (telDetailLink) telDetailLink.href = `/events/${ev.slug}`;

      if (btnRegister) {
        btnRegister.href = `/register?event_id=${ev.id}`;
        if (ev.can_register) {
          btnRegister.classList.remove("is-disabled");
          btnRegister.textContent = "Daftar Lomba Sekarang";
        } else {
          btnRegister.classList.add("is-disabled");
          btnRegister.textContent = `Pendaftaran ${ev.effective_status}`;
        }
      }

      if (cdEventDate) cdEventDate.textContent = ev.event_date_label;
      if (telParticipants) telParticipants.textContent = ev.participant_count;
      if (telCompetitions) telCompetitions.textContent = ev.competition_count;
      if (telStatusReason) telStatusReason.textContent = ev.status_reason;

      // Update active rail button
      document.querySelectorAll(".hero-rail-item").forEach((btn, i) => {
        btn.classList.toggle("active", i === idx);
      });

      updateCountdown();
    };

    if (!animate) {
      apply();
      return;
    }

    centerEl.classList.add("is-switching");
    setTimeout(() => {
      apply();
      centerEl.classList.remove("is-switching");
    }, 180);
  }

  function updateCountdown() {
    const ev = events[currentIdx];
    if (!ev || !cdDays) return;
    const target = new Date(ev.event_date).getTime();
    const now = Date.now();
    const diff = Math.max(0, target - now);

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
    const mins = Math.floor((diff / (1000 * 60)) % 60);
    const secs = Math.floor((diff / 1000) % 60);

    cdDays.textContent = String(days).padStart(2, "0");
    if (cdHours) cdHours.textContent = `${String(hours).padStart(2, "0")}j`;
    if (cdMins) cdMins.textContent = `${String(mins).padStart(2, "0")}m`;
    if (cdSecs) cdSecs.textContent = `${String(secs).padStart(2, "0")}d`;

    if (cdRingProgress) {
      // Progress lingkaran estetis berdasarkan kedekatan hari (maks 45 hari)
      const pct = Math.max(0.12, Math.min(1, 1 - days / 45));
      const circumference = 2 * Math.PI * 26;
      cdRingProgress.style.strokeDasharray = `${circumference}`;
      cdRingProgress.style.strokeDashoffset = `${circumference * (1 - pct)}`;
    }
  }

  function switchTo(newIdx) {
    currentIdx = (newIdx + events.length) % events.length;
    renderEvent(currentIdx, true);
  }

  document.querySelectorAll(".hero-rail-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.dataset.eventIndex, 10);
      if (!Number.isNaN(idx) && idx !== currentIdx) switchTo(idx);
    });
  });

  const prevBtn = document.getElementById("heroPrevEvent");
  const nextBtn = document.getElementById("heroNextEvent");
  if (prevBtn) prevBtn.addEventListener("click", () => switchTo(currentIdx - 1));
  if (nextBtn) nextBtn.addEventListener("click", () => switchTo(currentIdx + 1));

  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea, select")) return;
    if (e.key === "ArrowLeft") switchTo(currentIdx - 1);
    if (e.key === "ArrowRight") switchTo(currentIdx + 1);
  });

  renderEvent(currentIdx, false);
  setInterval(updateCountdown, 1000);
});
