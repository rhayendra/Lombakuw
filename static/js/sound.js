/**
 * Lombaku Dynamic Liquid Glass Sound Engine (Web Audio API v2)
 *
 * Variasi suara khusus tiap interaksi:
 *  - click      : tap pendek, clean, dengan micro-pitch variation agar tidak monoton
 *  - nav        : glide transisi ringan (berbeda dari click)
 *  - submit     : chord positif & rewarding saat pendaftaran berhasil
 *  - open       : aktivasi energetic saat event/form dibuka
 *  - lock       : suara segel kaca saat event/bracket dikunci
 *  - shuffle    : kaskade dinamis randomization saat bracket diacak
 *  - advance    : nada naik bersih saat peserta melaju ke babak berikutnya
 *  - winner     : harmoni hangat & memorable saat pengumuman juara
 *  - error      : ketukan rendah singkat untuk validasi/error
 *  - modalOpen  : desiran lembut membuka panel modal
 *  - modalClose : desiran halus menutup panel modal
 *
 * Mendukung pengaturan tersimpan (localStorage):
 *  - ON / OFF
 *  - Volume Control (0 - 100%)
 *  - Sound Profile: Minimal | Balanced | Energetic
 * Tidak pernah melakukan autoplay sebelum interaksi pengguna.
 */
const LombakuSound = (() => {
  const KEY_ENABLED = "lombaku_sound_enabled";
  const KEY_VOLUME = "lombaku_sound_volume";
  const KEY_PROFILE = "lombaku_sound_profile";

  let ctx = null;
  let enabled = localStorage.getItem(KEY_ENABLED) !== "false";
  let volume = parseFloat(localStorage.getItem(KEY_VOLUME));
  if (Number.isNaN(volume)) volume = 0.65;
  volume = Math.max(0, Math.min(1, volume));

  let profile = localStorage.getItem(KEY_PROFILE) || "balanced";
  if (!["minimal", "balanced", "energetic"].includes(profile)) profile = "balanced";

  // Subtle controlled micro-pitch sequence for clicks (organic, never jarring)
  const clickMicroRatios = [1.0, 1.032, 0.978, 1.018, 0.992, 1.042];
  let clickIndex = 0;

  const profileParams = {
    minimal: { gainScale: 0.72, durScale: 0.78, harmonic: false, brightness: 0.94 },
    balanced: { gainScale: 1.0, durScale: 1.0, harmonic: true, brightness: 1.0 },
    energetic: { gainScale: 1.22, durScale: 1.08, harmonic: true, brightness: 1.1 },
  };

  function ensureContext() {
    if (!enabled || volume <= 0.001) return null;
    try {
      if (!ctx) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return null;
        ctx = new AudioCtx();
      }
      if (ctx.state === "suspended") {
        ctx.resume().catch(() => {});
      }
      return ctx;
    } catch {
      return null;
    }
  }

  function synthNote({
    freq = 600,
    endFreq = null,
    duration = 0.09,
    type = "sine",
    gain = 0.06,
    delay = 0,
    attack = 0.008,
    filterFreq = 4200,
  }) {
    const c = ensureContext();
    if (!c) return;
    const p = profileParams[profile];
    const now = c.currentTime + delay;
    const finalDur = Math.max(0.03, duration * p.durScale);
    const finalGain = Math.min(0.24, gain * volume * p.gainScale);
    if (finalGain <= 0.0005) return;

    const osc = c.createOscillator();
    const filter = c.createBiquadFilter();
    const amp = c.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq * p.brightness, now);
    if (endFreq !== null) {
      osc.frequency.exponentialRampToValueAtTime(Math.max(45, endFreq * p.brightness), now + finalDur);
    }

    filter.type = "lowpass";
    filter.frequency.setValueAtTime(filterFreq * p.brightness, now);

    amp.gain.setValueAtTime(0.0001, now);
    amp.gain.linearRampToValueAtTime(finalGain, now + attack);
    amp.gain.exponentialRampToValueAtTime(0.0001, now + finalDur);

    osc.connect(filter);
    filter.connect(amp);
    amp.connect(c.destination);

    osc.start(now);
    osc.stop(now + finalDur + 0.025);
  }

  const sounds = {
    click() {
      const ratio = clickMicroRatios[clickIndex % clickMicroRatios.length];
      clickIndex += 1;
      synthNote({
        freq: 760 * ratio,
        endFreq: 490 * ratio,
        duration: 0.048,
        type: "sine",
        gain: 0.055,
        attack: 0.004,
        filterFreq: 3200,
      });
      if (profileParams[profile].harmonic) {
        synthNote({
          freq: 1520 * ratio,
          endFreq: 1120 * ratio,
          duration: 0.03,
          type: "triangle",
          gain: 0.016,
          attack: 0.003,
          filterFreq: 3600,
        });
      }
    },

    nav() {
      // Soft airy two-note glass glide, distinctly smoother than click
      synthNote({ freq: 392, endFreq: 523.25, duration: 0.085, type: "sine", gain: 0.042, attack: 0.012, filterFreq: 2400 });
      if (profileParams[profile].harmonic) {
        synthNote({ freq: 587.33, endFreq: 659.25, duration: 0.09, type: "sine", gain: 0.026, delay: 0.032, attack: 0.012, filterFreq: 2600 });
      }
    },

    submit() {
      // Uplifting, rewarding major-9th confirmation bloom
      const notes = [523.25, 659.25, 783.99, 1174.66];
      notes.forEach((n, idx) => {
        if (idx === 3 && !profileParams[profile].harmonic) return;
        synthNote({
          freq: n,
          duration: idx === 3 ? 0.28 : 0.18,
          type: idx % 2 === 0 ? "sine" : "triangle",
          gain: idx === 3 ? 0.034 : 0.056,
          delay: idx * 0.062,
          attack: 0.01,
          filterFreq: 3800,
        });
      });
    },

    open() {
      // Energetic activation sweep (event opened / form unlocked)
      synthNote({ freq: 369.99, endFreq: 554.37, duration: 0.12, type: "sine", gain: 0.052, delay: 0 });
      synthNote({ freq: 554.37, endFreq: 739.99, duration: 0.14, type: "triangle", gain: 0.044, delay: 0.065 });
      if (profileParams[profile].harmonic) {
        synthNote({ freq: 1108.73, duration: 0.2, type: "sine", gain: 0.03, delay: 0.13 });
      }
    },

    lock() {
      // Clean damped glass seal
      synthNote({ freq: 440, endFreq: 277.18, duration: 0.095, type: "triangle", gain: 0.05, delay: 0, filterFreq: 1800 });
      synthNote({ freq: 277.18, endFreq: 196, duration: 0.12, type: "sine", gain: 0.045, delay: 0.055, filterFreq: 1400 });
    },

    shuffle() {
      // Dynamic rhythmic randomization cascade + crisp settle note
      const cascade = [440, 587.33, 523.25, 698.46, 659.25, 880, 783.99];
      cascade.forEach((n, idx) => {
        synthNote({
          freq: n,
          endFreq: n * 1.05,
          duration: 0.062,
          type: idx % 2 === 0 ? "sine" : "triangle",
          gain: 0.042 + idx * 0.002,
          delay: idx * 0.048,
          attack: 0.005,
          filterFreq: 3600,
        });
      });
      // Clean landing tone
      synthNote({
        freq: 1046.5,
        duration: 0.22,
        type: "sine",
        gain: 0.052,
        delay: cascade.length * 0.048 + 0.03,
        attack: 0.01,
      });
    },

    advance() {
      // Energetic upward progression chime
      synthNote({ freq: 587.33, duration: 0.11, type: "sine", gain: 0.055, delay: 0 });
      synthNote({ freq: 880, duration: 0.2, type: "triangle", gain: 0.055, delay: 0.075 });
      if (profileParams[profile].harmonic) {
        synthNote({ freq: 1174.66, duration: 0.22, type: "sine", gain: 0.03, delay: 0.14 });
      }
    },

    winner() {
      // Memorable, refined celebratory major chord shimmer (never arcade-like)
      const arpeggio = [523.25, 659.25, 783.99, 987.77, 1046.5];
      arpeggio.forEach((n, idx) => {
        synthNote({
          freq: n,
          duration: 0.42 - idx * 0.02,
          type: idx >= 3 ? "triangle" : "sine",
          gain: idx === 4 ? 0.055 : 0.046,
          delay: idx * 0.068,
          attack: 0.014,
          filterFreq: 4200,
        });
      });
      if (profile === "energetic") {
        synthNote({ freq: 1567.98, duration: 0.45, type: "sine", gain: 0.028, delay: 0.36, attack: 0.02 });
      }
    },

    error() {
      // Short, polite, low-register double pulse
      synthNote({ freq: 245, endFreq: 205, duration: 0.095, type: "triangle", gain: 0.052, delay: 0, filterFreq: 1100 });
      synthNote({ freq: 205, endFreq: 170, duration: 0.12, type: "sine", gain: 0.046, delay: 0.095, filterFreq: 950 });
    },

    modalOpen() {
      synthNote({ freq: 340, endFreq: 520, duration: 0.11, type: "sine", gain: 0.036, attack: 0.015, filterFreq: 2000 });
    },

    modalClose() {
      synthNote({ freq: 480, endFreq: 310, duration: 0.095, type: "sine", gain: 0.032, attack: 0.01, filterFreq: 1800 });
    },
  };

  function play(name) {
    if (!enabled || volume <= 0.001) return;
    if (sounds[name]) sounds[name]();
  }

  function setEnabled(val) {
    enabled = Boolean(val);
    localStorage.setItem(KEY_ENABLED, enabled ? "true" : "false");
    syncUI();
    if (enabled) play("open");
  }

  function setVolume(val) {
    volume = Math.max(0, Math.min(1, parseFloat(val) || 0));
    localStorage.setItem(KEY_VOLUME, String(volume));
    syncUI();
  }

  function setProfile(nextProfile) {
    if (!["minimal", "balanced", "energetic"].includes(nextProfile)) return;
    profile = nextProfile;
    localStorage.setItem(KEY_PROFILE, profile);
    syncUI();
    play("open");
  }

  function syncUI() {
    const muted = !enabled || volume <= 0.001;
    const triggerBtn = document.getElementById("audioPopoverBtn");
    if (triggerBtn) {
      triggerBtn.classList.toggle("is-muted", muted);
      const label = triggerBtn.querySelector(".sound-label");
      if (label) {
        const profLabel = profile.charAt(0).toUpperCase() + profile.slice(1);
        label.textContent = muted ? "Sound OFF" : profLabel;
      }
      const onIcon = triggerBtn.querySelector(".icon-sound-on");
      const offIcon = triggerBtn.querySelector(".icon-sound-off");
      if (onIcon) onIcon.style.display = muted ? "none" : "";
      if (offIcon) offIcon.style.display = muted ? "" : "none";
    }

    const sw = document.getElementById("audioEnabledSwitch");
    if (sw) sw.setAttribute("aria-checked", enabled ? "true" : "false");

    const slider = document.getElementById("audioVolumeSlider");
    if (slider) slider.value = Math.round(volume * 100);

    const volLabel = document.getElementById("audioVolumeValue");
    if (volLabel) volLabel.textContent = `${Math.round(volume * 100)}%`;

    document.querySelectorAll("[data-sound-profile]").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.soundProfile === profile);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    syncUI();

    const triggerBtn = document.getElementById("audioPopoverBtn");
    const popover = document.getElementById("audioPopover");

    if (triggerBtn && popover) {
      triggerBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const willOpen = !popover.classList.contains("open");
        popover.classList.toggle("open", willOpen);
        play(willOpen ? "modalOpen" : "modalClose");
      });

      document.addEventListener("click", (e) => {
        if (popover.classList.contains("open") && !e.target.closest(".audio-control-wrap")) {
          popover.classList.remove("open");
        }
      });
    }

    const sw = document.getElementById("audioEnabledSwitch");
    if (sw) {
      sw.addEventListener("click", () => setEnabled(!enabled));
    }

    const slider = document.getElementById("audioVolumeSlider");
    if (slider) {
      slider.addEventListener("input", () => setVolume(slider.value / 100));
      slider.addEventListener("change", () => play("click"));
    }

    document.querySelectorAll("[data-sound-profile]").forEach((btn) => {
      btn.addEventListener("click", () => setProfile(btn.dataset.soundProfile));
    });

    const previewBtn = document.getElementById("audioPreviewBtn");
    if (previewBtn) {
      previewBtn.addEventListener("click", () => play("submit"));
    }

    // Distinct global click vs navigation audio delegation
    document.addEventListener("click", (e) => {
      if (e.target.closest(".audio-control-wrap")) return;

      const navTarget = e.target.closest(".nav-pill-item, .mobile-nav-item, .admin-subnav a, .hero-rail-item, .orb-btn, .glass-tab-btn");
      if (navTarget && !navTarget.hasAttribute("data-no-click-sound")) {
        play("nav");
        return;
      }

      const btnTarget = e.target.closest("button, .btn-glass, .mini-pill-btn");
      if (btnTarget && !btnTarget.hasAttribute("data-no-click-sound") && !btnTarget.disabled) {
        play("click");
      }
    });
  });

  return {
    play,
    setEnabled,
    setVolume,
    setProfile,
    getState: () => ({ enabled, volume, profile }),
  };
})();
