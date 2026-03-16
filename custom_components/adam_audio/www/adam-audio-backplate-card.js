/**
 * adam-audio-backplate-card.js
 * Custom Lovelace card replicating the physical backplate of ADAM Audio A-Series monitors.
 *
 * Card config (same schema as adam-audio-card):
 *
 *   type: custom:adam-audio-backplate-card
 *   title: Left Monitor
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

const BP_VERSION = "1.0.0";

/* ── EQ band definitions ─────────────────────────────────────────────────── */

const EQ_BANDS = {
  bass:     { label: "Bass",     min: -2, max: 1 },
  desk:     { label: "Desk",     min: -2, max: 0 },
  presence: { label: "Presence", min: -1, max: 1 },
  treble:   { label: "Treble",   min: -1, max: 1 },
};

/* ── SVG curves & LED layout ─────────────────────────────────────────────── */

// X positions for each EQ band in the SVG viewBox (0 0 320 80)
const BAND_X = { bass: 50, desk: 130, presence: 210, treble: 275 };

// Y positions: map dB value to vertical position (higher dB = higher on panel)
// Range: y=14 (top, highest dB) to y=66 (bottom, lowest dB)
function dbToY(db) {
  // Map from dB range [-2, +1] to y range [66, 14]
  // -2 → 66, -1 → 48.7, 0 → 31.3, +1 → 14
  return 66 - ((db + 2) / 3) * 52;
}

// Build LED positions for each band
function bandLeds(key) {
  const band = EQ_BANDS[key];
  const x = BAND_X[key];
  const leds = [];
  for (let db = band.min; db <= band.max; db++) {
    leds.push({ x, y: dbToY(db), db });
  }
  return leds;
}

// Generate the frequency-response curve SVG paths
// 4 curves that weave between LED positions, crossing between bands
function curvePaths() {
  // Curve 1: upper weave — high at bass, dips at desk, rises at presence/treble
  const c1 = `M 0,14 C 20,14 35,14 50,14 C 70,14 100,48 130,49 C 155,49 185,14 210,14 C 235,14 255,14 275,14 C 295,14 315,16 320,16`;
  // Curve 2: mid-upper — 0dB level, gentle undulation
  const c2 = `M 0,31 C 20,31 35,31 50,31 C 70,31 100,31 130,31 C 155,31 185,31 210,31 C 235,31 255,31 275,31 C 295,31 315,33 320,33`;
  // Curve 3: mid-lower weave — low at bass, rises at desk, dips at presence
  const c3 = `M 0,49 C 20,49 35,49 50,49 C 70,49 100,14 130,14 C 155,14 185,49 210,49 C 235,49 255,49 275,49 C 295,49 315,47 320,47`;
  // Curve 4: bottom — lowest dB positions
  const c4 = `M 0,66 C 20,66 35,66 50,66 C 70,66 100,66 130,66 C 155,66 185,66 210,66 C 235,66 255,66 275,66 C 295,66 315,64 320,64`;
  return [c1, c2, c3, c4];
}

/* ── CSS ─────────────────────────────────────────────────────────────────── */

const BP_STYLES = `
  :host {
    display: block;
    font-family: 'Helvetica Neue', Arial, sans-serif;
  }

  /* ── Backplate card ────────────────────────────────────────────────────── */
  .backplate {
    max-width: 360px;
    margin: 0 auto;
    background: linear-gradient(
      180deg,
      #2a2a2e 0%,
      #242428 30%,
      #1e1e22 60%,
      #1a1a1e 100%
    );
    border: 1px solid #3a3a3e;
    border-radius: 6px;
    overflow: hidden;
    color: #bbb;
    user-select: none;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,0.04),
      0 4px 16px rgba(0,0,0,0.5);
    /* Brushed metal texture */
    background-image:
      repeating-linear-gradient(
        0deg,
        transparent,
        transparent 1px,
        rgba(255,255,255,0.008) 1px,
        rgba(255,255,255,0.008) 2px
      );
  }

  .backplate.unavailable {
    opacity: 0.45;
    pointer-events: none;
  }

  /* ── Header ────────────────────────────────────────────────────────────── */
  .bp-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: rgba(0,0,0,0.25);
    border-bottom: 1px solid #333;
  }

  .bp-header-left {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .bp-brand {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #999;
  }

  .bp-name {
    font-size: 9px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #666;
  }

  .bp-header-right {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .bp-status-label {
    font-size: 8px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #555;
  }

  .bp-status-led {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #1a3a1a;
    transition: background 0.3s, box-shadow 0.3s;
  }

  .bp-status-led.online {
    background: #22ff22;
    box-shadow: 0 0 4px #22ff22, 0 0 8px rgba(34,255,34,0.4);
  }

  .bp-status-led.muted {
    background: #ff3333;
    box-shadow: 0 0 4px #ff3333, 0 0 8px rgba(255,51,51,0.4);
  }

  .bp-status-led.sleeping {
    animation: led-blink-green 1.2s ease-in-out infinite;
  }

  .bp-status-led.offline {
    background: #333;
    box-shadow: none;
  }

  @keyframes led-blink-green {
    0%, 100% { background: #22ff22; box-shadow: 0 0 4px #22ff22, 0 0 8px rgba(34,255,34,0.4); }
    50% { background: #0a4a0a; box-shadow: none; }
  }

  /* ── Panel body ────────────────────────────────────────────────────────── */
  .bp-panel {
    padding: 14px 16px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* ── Section title (engraved look) ─────────────────────────────────────── */
  .bp-section-title {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #555;
    text-shadow: 0 -1px 0 rgba(0,0,0,0.8), 0 1px 0 rgba(255,255,255,0.04);
    text-align: center;
    margin-bottom: 6px;
  }

  .bp-divider {
    height: 1px;
    background: #111;
    box-shadow: 0 1px 0 rgba(255,255,255,0.03);
  }

  /* ── Room Adaptation section ───────────────────────────────────────────── */
  .bp-room-adaptation {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .bp-room-adaptation.disabled {
    opacity: 0.35;
    pointer-events: none;
  }

  .bp-curves-container {
    position: relative;
    width: 100%;
  }

  .bp-curves-svg {
    width: 100%;
    height: auto;
    display: block;
  }

  .bp-curves-svg .curve-line {
    fill: none;
    stroke: #3a3a3a;
    stroke-width: 1;
    opacity: 0.7;
  }

  .bp-curves-svg .led-dot {
    cursor: pointer;
    transition: fill 0.2s, filter 0.2s;
  }

  .bp-curves-svg .led-dot.off {
    fill: #1a3a1a;
    filter: none;
  }

  .bp-curves-svg .led-dot.on {
    fill: #22ff22;
    filter: drop-shadow(0 0 3px #22ff22) drop-shadow(0 0 6px rgba(34,255,34,0.5));
  }

  .bp-curves-svg .led-dot:hover {
    fill: #44ff44;
    filter: drop-shadow(0 0 4px #44ff44);
  }

  .bp-eq-labels {
    display: flex;
    justify-content: space-around;
    padding: 0 8px;
  }

  .bp-eq-label {
    font-size: 8px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #555;
    text-shadow: 0 -1px 0 rgba(0,0,0,0.6), 0 1px 0 rgba(255,255,255,0.03);
    text-align: center;
    flex: 1;
  }

  /* ── Toggle area ───────────────────────────────────────────────────────── */
  .bp-toggle-area {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 4px 0;
    cursor: pointer;
  }

  .bp-toggle-area:hover .bp-toggle-label {
    color: #aaa;
  }

  .bp-toggle-label {
    font-size: 8px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #555;
    transition: color 0.15s;
  }

  .bp-toggle-indicator {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #1a3a1a;
    transition: all 0.2s;
  }

  .bp-toggle-indicator.on {
    background: #22ff22;
    box-shadow: 0 0 3px #22ff22, 0 0 6px rgba(34,255,34,0.4);
  }

  /* ── Audio IN section ──────────────────────────────────────────────────── */
  .bp-audio-in {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .bp-connectors {
    display: flex;
    justify-content: center;
    gap: 32px;
    align-items: center;
  }

  .bp-connector {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }

  .bp-connector svg {
    width: 48px;
    height: 48px;
  }

  .bp-connector-info {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .bp-connector-label {
    font-size: 8px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #666;
  }

  .bp-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    transition: all 0.2s;
    flex-shrink: 0;
  }

  .bp-led.off {
    background: #1a3a1a;
    box-shadow: none;
  }

  .bp-led.on {
    background: #22ff22;
    box-shadow: 0 0 3px #22ff22, 0 0 6px rgba(34,255,34,0.4);
  }

  .bp-led.red-on {
    background: #ff3333;
    box-shadow: 0 0 3px #ff3333, 0 0 6px rgba(255,51,51,0.4);
  }

  .bp-led.amber-on {
    background: #ffaa00;
    box-shadow: 0 0 3px #ffaa00, 0 0 6px rgba(255,170,0,0.4);
  }

  .bp-input-btn-area {
    display: flex;
    justify-content: center;
  }

  .bp-input-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 6px 14px;
    border-radius: 4px;
    transition: background 0.15s;
  }

  .bp-input-btn:hover {
    background: rgba(255,255,255,0.04);
  }

  .bp-input-btn:active {
    transform: scale(0.97);
  }

  .bp-input-btn-circle {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: radial-gradient(circle at 40% 35%, #3a3a3e, #1a1a1e 80%);
    border: 1px solid #555;
    box-shadow: inset 0 2px 3px rgba(0,0,0,0.5);
    flex-shrink: 0;
  }

  .bp-input-btn:active .bp-input-btn-circle {
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.8);
  }

  .bp-input-btn-label {
    font-size: 8px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #555;
  }

  /* ── Voicing section ───────────────────────────────────────────────────── */
  .bp-voicing {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .bp-voicing-options {
    display: flex;
    justify-content: center;
    gap: 20px;
  }

  .bp-voicing-opt {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    transition: background 0.12s;
  }

  .bp-voicing-opt:hover {
    background: rgba(255,255,255,0.04);
  }

  .bp-voicing-label {
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #555;
    transition: color 0.15s;
  }

  .bp-voicing-opt.active .bp-voicing-label {
    color: #ccc;
  }

  /* ── Utility strip (mute + power) ──────────────────────────────────────── */
  .bp-utility-strip {
    display: flex;
    justify-content: center;
    gap: 40px;
    padding: 6px 0 2px;
  }

  .bp-switch-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    cursor: pointer;
  }

  .bp-switch-group:hover .bp-switch-label {
    color: #aaa;
  }

  .bp-switch-label {
    font-size: 7px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #555;
    transition: color 0.15s;
  }

  /* ── Toggle (DIP) switch for MUTE ──────────────────────────────────────── */
  .bp-toggle-sw {
    width: 18px;
    height: 28px;
    background: #111;
    border: 1px solid #444;
    border-radius: 3px;
    position: relative;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.6);
  }

  .bp-toggle-sw .toggle-handle {
    position: absolute;
    width: 14px;
    height: 12px;
    left: 1px;
    background: linear-gradient(180deg, #666, #444);
    border: 1px solid #555;
    border-radius: 2px;
    transition: top 0.15s ease;
    box-shadow: 0 1px 2px rgba(0,0,0,0.4);
  }

  .bp-toggle-sw.off .toggle-handle {
    top: 1px;
  }

  .bp-toggle-sw.on .toggle-handle {
    top: 13px;
  }

  /* ── Rocker switch for POWER ───────────────────────────────────────────── */
  .bp-rocker-sw {
    width: 36px;
    height: 20px;
    background: #111;
    border: 1px solid #444;
    border-radius: 3px;
    position: relative;
    overflow: hidden;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.6);
  }

  .bp-rocker-body {
    position: absolute;
    inset: 1px;
    display: flex;
    transition: transform 0.15s ease;
    transform-origin: center center;
  }

  .bp-rocker-body .rocker-half {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 6px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #555;
  }

  .bp-rocker-sw.on .bp-rocker-body {
    background: linear-gradient(90deg, #333 0%, #222 40%, #181818 100%);
  }

  .bp-rocker-sw.off .bp-rocker-body {
    background: linear-gradient(90deg, #181818 0%, #222 60%, #333 100%);
  }

  .bp-rocker-sw.on .rocker-half.on-label {
    color: #aaa;
  }

  .bp-rocker-sw.off .rocker-half.off-label {
    color: #aaa;
  }

  .bp-rocker-sw .rocker-divider {
    width: 1px;
    height: 100%;
    background: #444;
    flex-shrink: 0;
  }

  /* ── Touch optimization ────────────────────────────────────────────────── */
  .bp-switch-group,
  .bp-voicing-opt,
  .bp-toggle-area,
  .bp-input-btn,
  .bp-curves-svg .led-dot {
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }
`;

/* ── SVG: XLR connector ──────────────────────────────────────────────────── */

const SVG_XLR = `
<svg viewBox="0 0 48 48" fill="none">
  <circle cx="24" cy="24" r="20" fill="#111" stroke="#555" stroke-width="1"/>
  <circle cx="24" cy="24" r="16" fill="none" stroke="#333" stroke-width="0.5"/>
  <!-- 3 pins -->
  <circle cx="24" cy="15" r="2.5" fill="#666" stroke="#888" stroke-width="0.5"/>
  <circle cx="17" cy="28" r="2.5" fill="#666" stroke="#888" stroke-width="0.5"/>
  <circle cx="31" cy="28" r="2.5" fill="#666" stroke="#888" stroke-width="0.5"/>
  <!-- Keyway notch -->
  <rect x="22" y="36" width="4" height="4" rx="1" fill="#222" stroke="#444" stroke-width="0.5"/>
</svg>`;

/* ── SVG: RCA connector ──────────────────────────────────────────────────── */

const SVG_RCA = `
<svg viewBox="0 0 48 48" fill="none">
  <circle cx="24" cy="24" r="14" fill="none" stroke="#555" stroke-width="1.5"/>
  <circle cx="24" cy="24" r="9" fill="none" stroke="#444" stroke-width="0.5"/>
  <circle cx="24" cy="24" r="3" fill="#666" stroke="#888" stroke-width="0.5"/>
</svg>`;

/* ── Card element ────────────────────────────────────────────────────────── */

class AdamAudioBackplateCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._rendered = false;
  }

  /* ── HACS / Lovelace metadata ───────────────────────────────────────── */

  static getConfigElement() {
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

  /* ── Config ─────────────────────────────────────────────────────────── */

  setConfig(config) {
    if (!config.entities) throw new Error("adam-audio-backplate-card: 'entities' is required.");
    this._config = config;
    this._rendered = false;
  }

  get _entities() { return this._config.entities || {}; }

  /* ── HA state ───────────────────────────────────────────────────────── */

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this._build();
      this._rendered = true;
    }
    this._update();
  }

  /* ── Build DOM once ─────────────────────────────────────────────────── */

  _build() {
    const shadow = this.shadowRoot;
    shadow.innerHTML = "";

    const style = document.createElement("style");
    style.textContent = BP_STYLES;
    shadow.appendChild(style);

    const tpl = document.createElement("div");
    tpl.innerHTML = this._template();
    shadow.appendChild(tpl.firstElementChild);

    this._attachListeners();
  }

  _template() {
    return `
    <ha-card class="backplate">

      <!-- Header -->
      <div class="bp-header">
        <div class="bp-header-left">
          <span class="bp-brand">ADAM Audio</span>
          <span class="bp-name" id="bp-name">${this._config.title || "A-Series"}</span>
        </div>
        <div class="bp-header-right">
          <span class="bp-status-label">Status</span>
          <span class="bp-status-led" id="status-led"></span>
        </div>
      </div>

      <!-- Panel -->
      <div class="bp-panel">

        <!-- Room Adaptation -->
        <div class="bp-room-adaptation" id="room-adaptation">
          <div class="bp-section-title">Room Adaptation</div>
          <div class="bp-curves-container">
            ${this._curveSvg()}
          </div>
          <div class="bp-toggle-area" id="room-toggle">
            <span class="bp-toggle-indicator" id="toggle-ind"></span>
            <span class="bp-toggle-label">Toggle</span>
          </div>
          <div class="bp-eq-labels">
            <span class="bp-eq-label">Bass</span>
            <span class="bp-eq-label">Desk</span>
            <span class="bp-eq-label">Presence</span>
            <span class="bp-eq-label">Treble</span>
          </div>
        </div>

        <div class="bp-divider"></div>

        <!-- Audio IN -->
        <div class="bp-audio-in">
          <div class="bp-section-title">Audio IN</div>
          <div class="bp-connectors">
            <div class="bp-connector">
              ${SVG_XLR}
              <div class="bp-connector-info">
                <span class="bp-led off" id="led-xlr"></span>
                <span class="bp-connector-label">XLR bal.</span>
              </div>
            </div>
            <div class="bp-connector">
              ${SVG_RCA}
              <div class="bp-connector-info">
                <span class="bp-led off" id="led-rca"></span>
                <span class="bp-connector-label">RCA unbal.</span>
              </div>
            </div>
          </div>
          <div class="bp-input-btn-area">
            <button class="bp-input-btn" id="btn-input">
              <span class="bp-input-btn-circle"></span>
              <span class="bp-input-btn-label">Input Select</span>
            </button>
          </div>
        </div>

        <div class="bp-divider"></div>

        <!-- Voicing -->
        <div class="bp-voicing">
          <div class="bp-section-title">Voicing</div>
          <div class="bp-voicing-options" id="voicing-options">
            <div class="bp-voicing-opt" data-value="Pure">
              <span class="bp-led off" id="led-pure"></span>
              <span class="bp-voicing-label">Pure</span>
            </div>
            <div class="bp-voicing-opt" data-value="UNR">
              <span class="bp-led off" id="led-unr"></span>
              <span class="bp-voicing-label">UNR</span>
            </div>
            <div class="bp-voicing-opt" data-value="Ext">
              <span class="bp-led off" id="led-ext"></span>
              <span class="bp-voicing-label">Ext</span>
            </div>
          </div>
        </div>

        <div class="bp-divider"></div>

        <!-- Utility strip: Mute + Power -->
        <div class="bp-utility-strip">
          <div class="bp-switch-group" id="sw-mute">
            <span class="bp-led off" id="led-mute"></span>
            <div class="bp-toggle-sw off" id="toggle-mute">
              <div class="toggle-handle"></div>
            </div>
            <span class="bp-switch-label">Mute</span>
          </div>
          <div class="bp-switch-group" id="sw-power">
            <span class="bp-led off" id="led-power"></span>
            <div class="bp-rocker-sw on" id="rocker-power">
              <div class="bp-rocker-body">
                <span class="rocker-half on-label">On</span>
                <span class="rocker-divider"></span>
                <span class="rocker-half off-label">Off</span>
              </div>
            </div>
            <span class="bp-switch-label">Power</span>
          </div>
        </div>

      </div>
    </ha-card>`;
  }

  /* ── EQ curves SVG ──────────────────────────────────────────────────── */

  _curveSvg() {
    const paths = curvePaths();
    let svg = `<svg class="bp-curves-svg" viewBox="0 0 320 80" preserveAspectRatio="xMidYMid meet">`;

    // Draw curve paths
    for (const d of paths) {
      svg += `<path d="${d}" class="curve-line"/>`;
    }

    // Draw LED dots for each band
    for (const key of ["bass", "desk", "presence", "treble"]) {
      const leds = bandLeds(key);
      for (const led of leds) {
        svg += `<circle cx="${led.x}" cy="${led.y}" r="4.5"
          class="led-dot off"
          data-key="${key}" data-db="${led.db}"
          id="led-${key}-${led.db < 0 ? 'n' + Math.abs(led.db) : led.db}" />`;
      }
    }

    svg += `</svg>`;
    return svg;
  }

  /* ── Bind listeners ─────────────────────────────────────────────────── */

  _attachListeners() {
    const root = this.shadowRoot;

    // EQ LED dots — click to set value
    root.querySelectorAll(".led-dot").forEach((dot) => {
      dot.addEventListener("click", () => {
        const key = dot.dataset.key;
        const db = parseInt(dot.dataset.db, 10);
        const entityId = this._entities[key];
        if (entityId) {
          this._callNumber(entityId, db);
        }
      });
    });

    // Room adaptation toggle — toggles voicing to/from Ext
    root.getElementById("room-toggle").addEventListener("click", () => {
      const voicing = this._stateValue(this._entities.voicing);
      if (voicing === "Ext") {
        this._callSelect(this._entities.voicing, "Pure");
      } else {
        this._callSelect(this._entities.voicing, "Ext");
      }
    });

    // Input select button — toggle between RCA and XLR
    root.getElementById("btn-input").addEventListener("click", () => {
      const current = this._stateValue(this._entities.input);
      const next = current === "XLR" ? "RCA" : "XLR";
      this._callSelect(this._entities.input, next);
    });

    // Voicing options — click to select
    root.getElementById("voicing-options").addEventListener("click", (e) => {
      const opt = e.target.closest(".bp-voicing-opt");
      if (!opt) return;
      this._callSelect(this._entities.voicing, opt.dataset.value);
    });

    // Mute toggle switch
    root.getElementById("sw-mute").addEventListener("click", () => {
      const isMuted = this._stateIs(this._entities.mute, "on");
      this._callSwitch(this._entities.mute, !isMuted);
    });

    // Power/sleep rocker switch
    root.getElementById("sw-power").addEventListener("click", () => {
      const isSleeping = this._stateIs(this._entities.sleep, "on");
      this._callSwitch(this._entities.sleep, !isSleeping);
    });
  }

  /* ── Update DOM from HA state ───────────────────────────────────────── */

  _update() {
    if (!this._hass) return;
    const root = this.shadowRoot;
    const e = this._entities;

    // Availability
    const available = this._isAvailable(e.mute);
    root.querySelector(".backplate").classList.toggle("unavailable", !available);

    const isMuted = this._stateIs(e.mute, "on");
    const isSleeping = this._stateIs(e.sleep, "on");

    // Status LED — sleep takes priority
    const statusLed = root.getElementById("status-led");
    statusLed.className = "bp-status-led";
    if (!available) {
      statusLed.classList.add("offline");
    } else if (isSleeping) {
      statusLed.classList.add("sleeping");
    } else if (isMuted) {
      statusLed.classList.add("muted");
    } else {
      statusLed.classList.add("online");
    }

    // Voicing
    const voicingVal = this._stateValue(e.voicing);
    const voicingMap = { Pure: "led-pure", UNR: "led-unr", Ext: "led-ext" };
    for (const [key, id] of Object.entries(voicingMap)) {
      const el = root.getElementById(id);
      el.className = "bp-led " + (voicingVal === key ? "on" : "off");
    }
    root.querySelectorAll(".bp-voicing-opt").forEach((opt) => {
      opt.classList.toggle("active", opt.dataset.value === voicingVal);
    });

    // Room adaptation toggle indicator + disabled state
    const roomActive = voicingVal !== "Ext";
    root.getElementById("toggle-ind").className =
      "bp-toggle-indicator" + (roomActive ? " on" : "");
    root.getElementById("room-adaptation").classList.toggle("disabled",
      !roomActive && available);

    // But keep the toggle area itself clickable even when disabled
    if (!roomActive && available) {
      const toggleArea = root.getElementById("room-toggle");
      toggleArea.style.pointerEvents = "auto";
      toggleArea.style.opacity = "1";
    }

    // EQ LED dots
    for (const key of ["bass", "desk", "presence", "treble"]) {
      const val = parseInt(this._stateValue(e[key]) ?? "0", 10);
      const band = EQ_BANDS[key];
      for (let db = band.min; db <= band.max; db++) {
        const id = `led-${key}-${db < 0 ? 'n' + Math.abs(db) : db}`;
        const dot = root.getElementById(id);
        if (dot) {
          dot.classList.remove("on", "off");
          dot.classList.add(db === val ? "on" : "off");
        }
      }
    }

    // Input source LEDs
    const inputVal = this._stateValue(e.input);
    root.getElementById("led-xlr").className =
      "bp-led " + (inputVal === "XLR" ? "on" : "off");
    root.getElementById("led-rca").className =
      "bp-led " + (inputVal === "RCA" ? "on" : "off");

    // Mute toggle switch + LED
    const toggleMute = root.getElementById("toggle-mute");
    toggleMute.className = "bp-toggle-sw " + (isMuted ? "on" : "off");
    root.getElementById("led-mute").className =
      "bp-led " + (isMuted ? "red-on" : "off");

    // Power rocker switch + LED
    const rockerPower = root.getElementById("rocker-power");
    rockerPower.className = "bp-rocker-sw " + (isSleeping ? "off" : "on");
    root.getElementById("led-power").className =
      "bp-led " + (isSleeping ? "amber-on" : "on");
  }

  /* ── HA helpers ─────────────────────────────────────────────────────── */

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

  /* ── Card size hint ─────────────────────────────────────────────────── */

  getCardSize() { return 7; }
}

try {
  customElements.define("adam-audio-backplate-card", AdamAudioBackplateCard);
} catch (e) {
  if (!e.message.includes("already been used")) {
    console.error("Failed to register adam-audio-backplate-card:", e);
  }
}

// Register with HACS / custom card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: "adam-audio-backplate-card",
  name: "ADAM Audio Backplate Card",
  description: "Backplate-style control card replicating the physical panel of ADAM Audio A-Series monitors.",
  preview: false,
  documentationURL: "https://github.com/Perhan35/hass-adam-audio-control",
});

console.info(
  `%c ADAM AUDIO BACKPLATE %c v${BP_VERSION} `,
  "background:#22ff22;color:#111;padding:2px 6px;border-radius:3px 0 0 3px;font-weight:bold",
  "background:#1a1a1e;color:#22ff22;padding:2px 6px;border-radius:0 3px 3px 0"
);
