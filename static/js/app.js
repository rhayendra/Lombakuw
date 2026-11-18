/**
 * Lombaku Global UI Utilities (v2):
 * - Toast notifications
 * - Modal helper dengan audio open/close
 * - Animated counters
 * - Refined celebratory spark burst (registration success & champion)
 * - Subtle multi-tone ambient drifting particles
 */
const LombakuUI = (() => {
  function toast(message, type = "info", duration = 4200) {
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    const icons = { success: "✦", error: "✕", warning: "▲", info: "◈" };
    const colors = { success: "#46f2b6", error: "#fda4af", warning: "#ffb020", info: "#38d6ff" };

    const el = document.createElement("div");
    el.className = `toast-item toast-${type}`;
    el.innerHTML = `
      <span style="color:${colors[type] || colors.info};font-weight:700;line-height:1.2;">${icons[type] || "◈"}</span>
      <div style="flex:1;line-height:1.45;">${escapeHtml(message)}</div>
    `;
    container.appendChild(el);

    setTimeout(() => {
      el.style.transition = "opacity 0.3s ease, transform 0.3s ease";
      el.style.opacity = "0";
      el.style.transform = "translateX(16px)";
      setTimeout(() => el.remove(), 320);
    }, duration);
  }

  function escapeHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

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

  /**
   * Efek percikan cahaya elegan (non-norak, ringan) untuk momen emosional:
   * pendaftaran sukses & pengumuman juara.
   */
  function celebrate(originEl = null, mode = "success") {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const palette =
      mode === "winner"
        ? ["#ffb020", "#ff7a1a", "#38d6ff", "#c4b5fd", "#ffffff"]
        : ["#38d6ff", "#3b9eff", "#46f2b6", "#ffb020", "#ffffff"];

    let cx = window.innerWidth * 0.5;
    let cy = window.innerHeight * 0.32;
    if (originEl && originEl.getBoundingClientRect) {
      const rect = originEl.getBoundingClientRect();
      if (rect.width > 0) {
        cx = rect.left + rect.width * 0.5;
        cy = rect.top + Math.min(rect.height * 0.4, 80);
      }
    }

    const count = mode === "winner" ? 26 : 18;
    for (let i = 0; i < count; i++) {
      const spark = document.createElement("span");
      spark.className = "celebration-spark";
      const color = palette[i % palette.length];
      const size = 5 + Math.random() * 5;
      spark.style.width = `${size}px`;
      spark.style.height = `${size}px`;
      spark.style.left = `${cx}px`;
      spark.style.top = `${cy}px`;
      spark.style.background = color;
      spark.style.boxShadow = `0 0 12px ${color}`;
      document.body.appendChild(spark);

      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.4;
      const dist = 58 + Math.random() * (mode === "winner" ? 130 : 88);
      const dx = Math.cos(angle) * dist;
      const dy = Math.sin(angle) * dist - 22;

      spark.animate(
        [
          { transform: "translate(-50%, -50%) scale(0.4)", opacity: 0.95 },
          { transform: `translate(calc(-50% + ${dx * 0.72}px), calc(-50% + ${dy * 0.72}px)) scale(1.1)`, opacity: 0.9, offset: 0.55 },
          { transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy + 26}px)) scale(0.2)`, opacity: 0 },
        ],
        { duration: 780 + Math.random() * 340, easing: "cubic-bezier(0.22, 1, 0.36, 1)", fill: "forwards" }
      ).onfinish = () => spark.remove();
    }
  }

  function initCounters() {
    document.querySelectorAll("[data-counter]").forEach((el) => {
      const target = parseInt(el.dataset.counter, 10);
      if (Number.isNaN(target)) return;
      const duration = 720;
      const start = performance.now();
      function step(now) {
        const p = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased);
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }

  function initAmbientParticles() {
    const canvas = document.getElementById("ambientCanvas");
    if (!canvas) return;
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const ctx = canvas.getContext("2d");
    const isMobile = window.innerWidth < 768;
    const count = isMobile ? 16 : 30;
    let w = (canvas.width = window.innerWidth);
    let h = (canvas.height = window.innerHeight);

    const colors = [
      "rgba(96, 196, 255,",
      "rgba(154, 134, 255,",
      "rgba(255, 174, 84,",
    ];

    const particles = Array.from({ length: count }, (_, idx) => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: Math.random() * 1.7 + 0.65,
      vx: (Math.random() - 0.5) * 0.24,
      vy: -Math.random() * 0.22 - 0.05,
      a: Math.random() * 0.42 + 0.14,
      c: colors[idx % colors.length],
    }));

    window.addEventListener("resize", () => {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    });

    function draw() {
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.y < -10) { p.y = h + 10; p.x = Math.random() * w; }
        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `${p.c} ${p.a})`;
        ctx.fill();
      }
      requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initCounters();
    initAmbientParticles();

    document.addEventListener("click", (e) => {
      const closeBtn = e.target.closest("[data-close-modal]");
      if (closeBtn) {
        const modal = closeBtn.closest(".modal-backdrop");
        if (modal) closeModal(modal.id);
      } else if (e.target.classList.contains("modal-backdrop")) {
        closeModal(e.target.id);
      }
    });

    document.querySelectorAll("[data-flash-message]").forEach((node) => {
      toast(node.dataset.flashMessage, node.dataset.flashCategory || "info");
    });
  });

  return { toast, escapeHtml, openModal, closeModal, celebrate };
})();
