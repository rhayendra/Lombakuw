/**
 * Lombaku Minimal Browser Helper (~80 baris)
 * Seluruh logika, validasi, rendering halaman, dan bracket dijalankan oleh Python + Jinja2.
 * File ini HANYA menangani interaksi browser ringan yang tidak praktis dilakukan di server:
 *  1. Detik live countdown
 *  2. Auto-hide flash toast & memutar sound cue hasil aksi server Python
 *  3. Buka/tutup modal & zoom bracket
 */
const LombakuUI = (() => {
  function openModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add("open");
    document.body.style.overflow = "hidden";
    if (window.LombakuSound) LombakuSound.play("modalOpen");
  }

  function closeModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("open");
    document.body.style.overflow = "";
    if (window.LombakuSound) LombakuSound.play("modalClose");
  }

  document.addEventListener("DOMContentLoaded", () => {
    // 1. Auto-dismiss server-rendered Flask flash toasts
    document.querySelectorAll("[data-auto-dismiss]").forEach((el) => {
      const ms = parseInt(el.dataset.autoDismiss, 10) || 4500;
      setTimeout(() => {
        el.style.transition = "opacity 0.3s ease, transform 0.3s ease";
        el.style.opacity = "0";
        el.style.transform = "translateX(16px)";
        setTimeout(() => el.remove(), 320);
      }, ms);
    });

    // 2. Putar sound cue hasil redirect Python (hanya jika audio sudah diizinkan browser)
    const cue = document.body.dataset.soundCue;
    if (cue && window.LombakuSound) {
      LombakuSound.play(cue);
    }

    // 3. Live 1-second countdown ticker (nilai awal sudah dirender oleh Python)
    const cdBox = document.querySelector("[data-countdown-target]");
    if (cdBox && cdBox.dataset.countdownTarget) {
      const targetMs = new Date(cdBox.dataset.countdownTarget).getTime();
      const dEl = cdBox.querySelector('[data-cd="days"]');
      const hEl = cdBox.querySelector('[data-cd="hours"]');
      const mEl = cdBox.querySelector('[data-cd="mins"]');
      const sEl = cdBox.querySelector('[data-cd="secs"]');
      if (!Number.isNaN(targetMs)) {
        setInterval(() => {
          const diff = Math.max(0, targetMs - Date.now());
          if (dEl) dEl.textContent = String(Math.floor(diff / 86400000)).padStart(2, "0");
          if (hEl) hEl.textContent = `${String(Math.floor((diff / 3600000) % 24)).padStart(2, "0")}j`;
          if (mEl) mEl.textContent = `${String(Math.floor((diff / 60000) % 60)).padStart(2, "0")}m`;
          if (sEl) sEl.textContent = `${String(Math.floor((diff / 1000) % 60)).padStart(2, "0")}d`;
        }, 1000);
      }
    }

    // 4. Delegasi buka/tutup modal
    document.addEventListener("click", (e) => {
      const openBtn = e.target.closest("[data-open-modal]");
      if (openBtn) {
        openModal(openBtn.dataset.openModal);
        return;
      }
      const closeBtn = e.target.closest("[data-close-modal]");
      if (closeBtn) {
        const modal = closeBtn.closest(".modal-backdrop");
        if (modal) closeModal(modal.id);
        return;
      }
      if (e.target.classList.contains("modal-backdrop")) {
        closeModal(e.target.id);
      }
    });

    // 5. Zoom bracket (+ / - / 100%)
    const canvas = document.getElementById("bracketCanvas");
    if (canvas) {
      let zoom = 1;
      document.querySelectorAll("[data-zoom]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const act = btn.dataset.zoom;
          if (act === "in") zoom = Math.min(1.25, +(zoom + 0.1).toFixed(2));
          else if (act === "out") zoom = Math.max(0.65, +(zoom - 0.1).toFixed(2));
          else zoom = 1;
          canvas.style.transform = `scale(${zoom})`;
        });
      });
    }
  });

  return { openModal, closeModal };
})();
