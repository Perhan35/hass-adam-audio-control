/**
 * adam-audio-card.js
 * Custom Lovelace card for ADAM Audio A-Series monitors.
 *
 * Card config example (add to resources as /local/adam-audio-card.js):
 *
 *   type: custom:adam-audio-card
 *   title: Left Monitor         # optional override
 *   entities:
 *     mute:     switch.left_mute
 *     sleep:    switch.left_sleep
 *     input:    select.left_input_source
 *     voicing:  select.left_voicing
 *     bass:     number.left_bass
 *     desk:     number.left_desk
 *     presence: number.left_presence
 *     treble:   number.left_treble
 */

const CARD_VERSION = "1.0.0";

/* ── CSS ─────────────────────────────────────────────────────────────────── */

const STYLES = `
  :host {
    --adam-bg:         #111214;
    --adam-surface:    #1c1e21;
    --adam-surface2:   #25282d;
    --adam-border:     #2e3238;
    --adam-orange:     #ff6a00;
    --adam-orange-dim: #7a3300;
    --adam-text:       #e8eaed;
    --adam-muted:      #6b7280;
    --adam-online:     #22c55e;
    --adam-offline:    #ef4444;
    --adam-sleep:      #f59e0b;
    --adam-radius:     10px;
    --adam-font:       'DM Mono', 'Roboto Mono', 'Courier New', monospace;
    display: block;
    font-family: var(--adam-font);
  }

  .card {
    background: var(--adam-bg);
    border: 1px solid var(--adam-border);
    border-radius: var(--adam-radius);
    overflow: hidden;
    color: var(--adam-text);
    user-select: none;
  }

  /* ── Header ─────────────────────────────────────────────────────────────── */
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px 12px;
    background: var(--adam-surface);
    border-bottom: 1px solid var(--adam-border);
    gap: 12px;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .speaker-icon {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
    color: var(--adam-orange);
  }

  .title-block { min-width: 0; }

  .device-name {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--adam-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .brand {
    font-size: 10px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--adam-orange);
    margin-top: 1px;
  }

  .status-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 4px 10px;
    border-radius: 100px;
    background: rgba(255,255,255,0.05);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .status-pill.online  .status-dot { background: var(--adam-online); box-shadow: 0 0 6px var(--adam-online); }
  .status-pill.offline .status-dot { background: var(--adam-offline); }
  .status-pill.sleep   .status-dot { background: var(--adam-sleep); box-shadow: 0 0 6px var(--adam-sleep); }

  /* ── Body ───────────────────────────────────────────────────────────────── */
  .body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 12px; }

  /* ── Power row ──────────────────────────────────────────────────────────── */
  .power-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

  .power-btn {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 11px 10px;
    border-radius: 8px;
    border: 1px solid var(--adam-border);
    background: var(--adam-surface2);
    color: var(--adam-muted);
    font-family: var(--adam-font);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.15s ease;
    overflow: hidden;
  }

  .power-btn::before {
    content: '';
    position: absolute;
    inset: 0;
    background: transparent;
    transition: background 0.15s;
  }

  .power-btn:hover::before { background: rgba(255,255,255,0.04); }
  .power-btn:active         { transform: scale(0.97); }

  .power-btn.active-mute {
    border-color: var(--adam-offline);
    color: var(--adam-offline);
    background: rgba(239,68,68,0.1);
  }

  .power-btn.active-sleep {
    border-color: var(--adam-sleep);
    color: var(--adam-sleep);
    background: rgba(245,158,11,0.1);
  }

  .power-btn svg { width: 16px; height: 16px; flex-shrink: 0; }

  /* ── Segment selectors ──────────────────────────────────────────────────── */
  .control-row { display: flex; flex-direction: column; gap: 4px; }

  .control-label {
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--adam-muted);
    padding-left: 2px;
  }

  .segment {
    display: flex;
    background: var(--adam-surface2);
    border: 1px solid var(--adam-border);
    border-radius: 7px;
    padding: 3px;
    gap: 3px;
  }

  .seg-btn {
    flex: 1;
    padding: 7px 6px;
    border-radius: 5px;
    border: none;
    background: transparent;
    color: var(--adam-muted);
    font-family: var(--adam-font);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    cursor: pointer;
    transition: all 0.12s ease;
    text-transform: uppercase;
  }

  .seg-btn:hover   { background: rgba(255,255,255,0.06); color: var(--adam-text); }
  .seg-btn.active  { background: var(--adam-orange); color: #fff; }

  input[type=range] {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 4px;
    border-radius: 2px;
    background: var(--adam-border);
    outline: none;
    cursor: pointer;
  }

  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--adam-orange);
    border: 2px solid var(--adam-bg);
    box-shadow: 0 0 0 1px var(--adam-orange);
    cursor: pointer;
    transition: transform 0.1s;
  }

  input[type=range]::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--adam-orange);
    border: 2px solid var(--adam-bg);
    cursor: pointer;
  }

  input[type=range]:active::-webkit-slider-thumb { transform: scale(1.2); }

  /* ── EQ section ─────────────────────────────────────────────────────────── */
  .eq-section { display: flex; flex-direction: column; gap: 2px; }

  .eq-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    padding: 6px 2px;
    border: none;
    background: transparent;
    color: var(--adam-muted);
    font-family: var(--adam-font);
    font-size: 9px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    width: 100%;
    transition: color 0.15s;
  }

  .eq-toggle:hover { color: var(--adam-text); }

  .eq-toggle-chevron {
    width: 14px;
    height: 14px;
    transition: transform 0.2s ease;
  }

  .eq-toggle-chevron.open { transform: rotate(180deg); }

  .eq-controls {
    display: flex;
    flex-direction: column;
    gap: 8px;
    overflow: hidden;
    max-height: 0;
    transition: max-height 0.3s ease, opacity 0.2s ease;
    opacity: 0;
  }

  .eq-controls.open { max-height: 300px; opacity: 1; }

  .eq-row {
    display: grid;
    grid-template-columns: 64px 1fr 36px;
    align-items: center;
    gap: 10px;
  }

  .eq-label {
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--adam-muted);
    text-align: right;
  }

  .eq-value {
    font-size: 11px;
    font-weight: 600;
    color: var(--adam-text);
    text-align: right;
    letter-spacing: 0.04em;
    min-width: 28px;
  }

  .eq-value.zero { color: var(--adam-muted); }

  input.eq-slider[type=range] {
    height: 3px;
  }

  input.eq-slider[type=range]::-webkit-slider-thumb {
    width: 14px;
    height: 14px;
  }

  /* ── Divider ─────────────────────────────────────────────────────────────── */
  .divider { height: 1px; background: var(--adam-border); margin: 0 -16px; }

  /* ── Unavailable overlay ─────────────────────────────────────────────────── */
  .card.unavailable { opacity: 0.5; pointer-events: none; }
`;

/* ── SVG icons ──────────────────────────────────────────────────────────────── */

const ICON_SPEAKER = `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="4" width="18" height="16" rx="2"/>
    <circle cx="12" cy="11" r="3"/>
    <circle cx="12" cy="11" r="1"/>
    <circle cx="7" cy="7" r="1" fill="currentColor" stroke="none"/>
  </svg>`;

const ICON_MUTE_ON = `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="1" y1="1" x2="23" y2="23"/>
    <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/>
    <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>`;

const ICON_MUTE_OFF = `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>`;

const ICON_SLEEP_ON = `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>`;

const ICON_SLEEP_OFF = `
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1" x2="12" y2="3"/>
    <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/>
    <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
  </svg>`;

const ICON_CHEVRON = `
  <svg class="eq-toggle-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="6 9 12 15 18 9"/>
  </svg>`;

/* ── Card element ───────────────────────────────────────────────────────────── */

class AdamAudioCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._eqOpen = false;
    this._rendered = false;
  }

  /* ── HACS / Lovelace metadata ─────────────────────────────────────────── */

  static getConfigElement() {
    // Visual editor stub — extend later for GUI editing
    return document.createElement("div");
  }

  static getStubConfig() {
    return {
      title: "Studio Monitor",
      entities: {
        mute:     "switch.left_mute",
        sleep:    "switch.left_sleep",
        input:    "select.left_input_source",
        voicing:  "select.left_voicing",
        bass:     "number.left_bass",
        desk:     "number.left_desk",
        presence: "number.left_presence",
        treble:   "number.left_treble",
      },
    };
  }

  /* ── Config ───────────────────────────────────────────────────────────── */

  setConfig(config) {
    if (!config.entities) throw new Error("adam-audio-card: 'entities' is required.");
    this._config = config;
    this._rendered = false;
  }

  get _entities() { return this._config.entities || {}; }

  /* ── HA state ─────────────────────────────────────────────────────────── */

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this._build();
      this._rendered = true;
    }
    this._update();
  }

  /* ── Build DOM once ───────────────────────────────────────────────────── */

  _build() {
    const shadow = this.shadowRoot;
    shadow.innerHTML = "";

    const style = document.createElement("style");
    style.textContent = STYLES;
    shadow.appendChild(style);

    const tpl = document.createElement("div");
    tpl.innerHTML = this._template();
    shadow.appendChild(tpl.firstElementChild);

    this._attachListeners();
  }

  _template() {
    return `
    <ha-card class="card">
      <div class="header">
        <div class="header-left">
          <div class="speaker-icon">${ICON_SPEAKER}</div>
          <div class="title-block">
            <div class="device-name" id="device-name">${this._config.title || "Monitor"}</div>
            <div class="brand">ADAM Audio · A-Series</div>
          </div>
        </div>
        <div class="status-pill online" id="status-pill">
          <span class="status-dot"></span>
          <span id="status-text">Online</span>
        </div>
      </div>

      <div class="body">

        <!-- Power row -->
        <div class="power-row">
          <button class="power-btn" id="btn-mute">
            <span id="icon-mute">${ICON_MUTE_OFF}</span>
            <span id="label-mute">Unmuted</span>
          </button>
          <button class="power-btn" id="btn-sleep">
            <span id="icon-sleep">${ICON_SLEEP_OFF}</span>
            <span id="label-sleep">Active</span>
          </button>
        </div>

        <!-- Input selector -->
        <div class="control-row">
          <div class="control-label">Input</div>
          <div class="segment" id="seg-input">
            <button class="seg-btn" data-value="RCA">RCA</button>
            <button class="seg-btn" data-value="XLR">XLR</button>
          </div>
        </div>

        <!-- Voicing selector -->
        <div class="control-row">
          <div class="control-label">Voicing</div>
          <div class="segment" id="seg-voicing">
            <button class="seg-btn" data-value="Pure">Pure</button>
            <button class="seg-btn" data-value="UNR">UNR</button>
            <button class="seg-btn" data-value="Ext">Ext</button>
          </div>
        </div>

        <div class="divider"></div>

        <!-- EQ section -->
        <div class="eq-section">
          <button class="eq-toggle" id="eq-toggle">
            <span>EQ</span>
            <span id="eq-chevron">${ICON_CHEVRON}</span>
          </button>
          <div class="eq-controls" id="eq-controls">
            ${this._eqRow("bass",     "Bass",     -2,  1)}
            ${this._eqRow("desk",     "Desk",     -2,  0)}
            ${this._eqRow("presence", "Presence", -1,  1)}
            ${this._eqRow("treble",   "Treble",   -1,  1)}
          </div>
        </div>

      </div>
    </ha-card>`;
  }

  _eqRow(key, label, min, max) {
    return `
      <div class="eq-row">
        <div class="eq-label">${label}</div>
        <input type="range" class="eq-slider" id="slider-${key}"
          min="${min}" max="${max}" step="1" value="0" />
        <div class="eq-value zero" id="val-${key}">0 dB</div>
      </div>`;
  }

  /* ── Bind listeners ───────────────────────────────────────────────────── */

  _attachListeners() {
    const root = this.shadowRoot;

    // Mute toggle
    root.getElementById("btn-mute").addEventListener("click", () => {
      const isMuted = this._stateIs(this._entities.mute, "on");
      this._callSwitch(this._entities.mute, !isMuted);
    });

    // Sleep toggle
    root.getElementById("btn-sleep").addEventListener("click", () => {
      const isSleeping = this._stateIs(this._entities.sleep, "on");
      this._callSwitch(this._entities.sleep, !isSleeping);
    });

    // Input segment
    root.getElementById("seg-input").addEventListener("click", (e) => {
      const btn = e.target.closest(".seg-btn");
      if (!btn) return;
      this._callSelect(this._entities.input, btn.dataset.value);
    });

    // Voicing segment
    root.getElementById("seg-voicing").addEventListener("click", (e) => {
      const btn = e.target.closest(".seg-btn");
      if (!btn) return;
      this._callSelect(this._entities.voicing, btn.dataset.value);
    });

    // EQ sliders
    ["bass", "desk", "presence", "treble"].forEach((key) => {
      const slider = root.getElementById(`slider-${key}`);
      slider.addEventListener("change", () => {
        this._callNumber(this._entities[key], parseInt(slider.value, 10));
      });
      slider.addEventListener("input", () => {
        this._updateEqValue(key, parseInt(slider.value, 10));
      });
    });

    // EQ toggle
    root.getElementById("eq-toggle").addEventListener("click", () => {
      this._eqOpen = !this._eqOpen;
      root.getElementById("eq-controls").classList.toggle("open", this._eqOpen);
      root.getElementById("eq-chevron")
        .querySelector(".eq-toggle-chevron")
        .classList.toggle("open", this._eqOpen);
    });
  }

  /* ── Update DOM from HA state ─────────────────────────────────────────── */

  _update() {
    if (!this._hass) return;
    const root = this.shadowRoot;
    const e = this._entities;

    // Availability / status
    const available = this._isAvailable(e.mute);
    root.querySelector(".card").classList.toggle("unavailable", !available);

    const isSleeping = this._stateIs(e.sleep, "on");
    const isMuted    = this._stateIs(e.mute, "on");

    const pill = root.getElementById("status-pill");
    const statusText = root.getElementById("status-text");
    pill.className = "status-pill " + (!available ? "offline" : isSleeping ? "sleep" : "online");
    statusText.textContent = !available ? "Offline" : isSleeping ? "Sleep" : "Online";

    // Mute button
    const btnMute = root.getElementById("btn-mute");
    btnMute.classList.toggle("active-mute", isMuted);
    root.getElementById("icon-mute").innerHTML = isMuted ? ICON_MUTE_ON : ICON_MUTE_OFF;
    root.getElementById("label-mute").textContent = isMuted ? "Muted" : "Unmuted";

    // Sleep button
    const btnSleep = root.getElementById("btn-sleep");
    btnSleep.classList.toggle("active-sleep", isSleeping);
    root.getElementById("icon-sleep").innerHTML = isSleeping ? ICON_SLEEP_ON : ICON_SLEEP_OFF;
    root.getElementById("label-sleep").textContent = isSleeping ? "Sleeping" : "Active";

    // Input segment
    const inputVal = this._stateValue(e.input);
    root.querySelectorAll("#seg-input .seg-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.value === inputVal);
    });

    // Voicing segment
    const voicingVal = this._stateValue(e.voicing);
    root.querySelectorAll("#seg-voicing .seg-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.value === voicingVal);
    });

    // EQ sliders
    ["bass", "desk", "presence", "treble"].forEach((key) => {
      const slider = root.getElementById(`slider-${key}`);
      if (!slider.matches(":active")) {
        const val = parseInt(this._stateValue(e[key]) ?? "0", 10);
        slider.value = val;
        this._updateEqValue(key, val);
      }
    });
  }

  _updateEqValue(key, val) {
    const el = this.shadowRoot.getElementById(`val-${key}`);
    if (!el) return;
    el.textContent = val === 0 ? "0 dB" : (val > 0 ? `+${val} dB` : `${val} dB`);
    el.classList.toggle("zero", val === 0);
  }

  /* ── HA helpers ──────────────────────────────────────────────────────────── */

  _stateObj(entityId) {
    return entityId && this._hass ? this._hass.states[entityId] : undefined;
  }

  _stateIs(entityId, value) {
    const s = this._stateObj(entityId);
    return s ? s.state === value : false;
  }

  _stateValue(entityId) {
    const s = this._stateObj(entityId);
    return s ? s.state : null;
  }

  _isAvailable(entityId) {
    const s = this._stateObj(entityId);
    return !!s && s.state !== "unavailable" && s.state !== "unknown";
  }

  _callSwitch(entityId, turnOn) {
    if (!entityId || !this._hass) return;
    this._hass.callService("switch", turnOn ? "turn_on" : "turn_off", {
      entity_id: entityId,
    });
  }

  _callSelect(entityId, option) {
    if (!entityId || !this._hass) return;
    this._hass.callService("select", "select_option", {
      entity_id: entityId,
      option,
    });
  }

  _callNumber(entityId, value) {
    if (!entityId || !this._hass) return;
    this._hass.callService("number", "set_value", {
      entity_id: entityId,
      value: String(value),
    });
  }

  /* ── Card size hint ──────────────────────────────────────────────────────── */

  getCardSize() { return 5; }
}

try {
  customElements.define("adam-audio-card", AdamAudioCard);
} catch (e) {
  if (!e.message.includes("already been used")) {
    console.error("Failed to register adam-audio-card:", e);
  }
}

// Register with HACS / custom card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: "adam-audio-card",
  name: "ADAM Audio Card",
  description: "Control card for ADAM Audio A-Series studio monitors.",
  preview: false,
  documentationURL: "https://github.com/Perhan35/hass-adam-audio-control",
});

console.info(
  `%c ADAM AUDIO CARD %c v${CARD_VERSION} `,
  "background:#ff6a00;color:#fff;padding:2px 6px;border-radius:3px 0 0 3px;font-weight:bold",
  "background:#1c1e21;color:#ff6a00;padding:2px 6px;border-radius:0 3px 3px 0"
);
