/**
 * backplate-card.js
 * Custom Lovelace card for ADAM Audio A-Series monitors replicating the physical backplate.
 */

(function () {
  const CARD_VERSION = "1.0.1";


  const STYLES = `
  :host {
    display: block;
    --bp-bg: #1c1c1c;
    --bp-text: #e0e0e0;
    --bp-green: #22c55e;
    --bp-green-glow: rgba(34, 197, 94, 0.6);
    --bp-led-off: #111;
    --bp-btn-face: linear-gradient(135deg, #3a3a3a, #1a1a1a);
    --bp-btn-edge: #0a0a0a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }

  .card {
    background: var(--bp-bg);
    background-image: url('data:image/svg+xml;utf8,<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"><filter id="noiseFilter"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(%23noiseFilter)" opacity="0.08"/></svg>');
    border-radius: 12px;
    border: 1px solid #333;
    box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    overflow: hidden;
    color: var(--bp-text);
    user-select: none;
    padding-bottom: 20px;
  }

  /* Header */
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(0,0,0,0.3);
    border-bottom: 1px solid #2a2a2a;
  }
  .title {
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 0.5px;
  }
  .power-row {
    display: flex;
    gap: 8px;
  }
  .power-toggle {
    background: #2a2a2a;
    border: 1px solid #111;
    border-radius: 4px;
    color: #aaa;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    padding: 4px 10px;
    cursor: pointer;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 1px 2px rgba(0,0,0,0.3);
  }
  .power-toggle:active {
    background: #1e1e1e;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
  }
  .power-toggle.active-mute {
    color: #ef4444;
    text-shadow: 0 0 5px rgba(239,68,68,0.5);
  }
  .power-toggle.active-sleep {
    color: #f59e0b;
    text-shadow: 0 0 5px rgba(245,158,11,0.5);
  }

  /* Body */
  .body {
    padding: 0px 10px 0px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* Room Adaptation */
  .room-adaptation {
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
  }
  .section-title {
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-top: 4px;
    text-align: center;
    color: #eee;
  }

  .eq-graphic {
    position: relative;
    width: 315px;
    height: 120px;
    margin: 0 auto;
  }

  .eq-graphic svg {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
  }

  .led {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--bp-led-off);
    box-shadow: inset 0 2px 3px rgba(0,0,0,0.8), 0 1px 0 rgba(255,255,255,0.1);
    transition: background 0.2s, box-shadow 0.2s;
  }
  .led.on {
    background: var(--bp-green);
    box-shadow: 0 0 6px var(--bp-green-glow), inset 0 1px 2px rgba(255,255,255,0.4);
  }

  .eq-led {
    position: absolute;
    transform: translate(-50%, -50%);
    width: 10px;
    height: 10px;
  }

  .hardware-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--bp-btn-face);
    border: 2px solid var(--bp-btn-edge);
    box-shadow: 0 4px 6px rgba(0,0,0,0.6), inset 0 1px 2px rgba(255,255,255,0.1);
    cursor: pointer;
    transition: transform 0.1s, box-shadow 0.1s;
    outline: none;
  }
  .hardware-btn:active {
    transform: translateY(2px);
    box-shadow: 0 1px 2px rgba(0,0,0,0.6), inset 0 2px 4px rgba(0,0,0,0.8);
  }

  .eq-labels {
    position: relative;
    width: 315px;
    height: 60px;
    margin: 4px auto 0;
  }

  .eq-col-label {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    width: 60px;
  }
  .eq-label-text {
    font-size: 11px;
    font-weight: 600;
    color: #ccc;
  }

  /* Dividers */
  .section-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.1);
    margin: 8px 0;
    width: 100%;
  }

  .vertical-divider {
    width: 1px;
    background: rgba(255, 255, 255, 0.1);
    height: 134px;
    margin-left: 0px;
    margin-right: 8px;
  }

  /* Bottom Row: Audio IN + Voicing */
  .bottom-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  /* Audio IN */
  .audio-in {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .audio-in-content {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .input-jacks {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .jack-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .xlr-port {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: #0a0a0a;
    border: 4px solid #555;
    position: relative;
    box-shadow: inset 0 8px 12px rgba(0,0,0,1), 0 2px 4px rgba(100,100,100,0.2), 0 4px 8px rgba(0,0,0,0.6);
  }
  .xlr-pins {
    position: absolute;
    width: 5px; height: 5px;
    background: #d4af37;
    border-radius: 50%;
    box-shadow: -1px -1px 2px rgba(0,0,0,0.8);
  }
  .xlr-pin-1 { top: 16px; left: 11px; }
  .xlr-pin-2 { top: 16px; right: 11px; }
  .xlr-pin-3 { bottom: 10px; left: 18.5px; }

  .rca-port {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #b89b47;
    position: relative;
    box-shadow: 0 4px 6px rgba(0,0,0,0.6), inset 0 2px 4px rgba(255,255,255,0.4);
    margin-left: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .rca-inner {
    width: 14px;
    height: 14px;
    background: #eee;
    border-radius: 50%;
    border: 2px solid #8c7322;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .rca-hole {
    width: 6px;
    height: 6px;
    background: #000;
    border-radius: 50%;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.9);
  }

  .jack-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #ddd;
    font-weight: 600;
  }

  .input-select-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin-top: 10px;
  }

  /* Voicing */
  .voicing {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
  .voicing-leds {
    display: flex;
    gap: 16px;
  }
  .v-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    color: #ccc;
  }
  .v-title-label {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .card.unavailable { opacity: 0.5; pointer-events: none; }
`;

  class BackplateCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = {};
      this._hass = null;
      this._rendered = false;
    }

    static getStubConfig() {
      return {
        title: "Left Monitor",
        entities: {
          mute: "switch.left_mute",
          sleep: "switch.left_sleep",
          input: "select.left_input_source",
          voicing: "select.left_voicing",
          bass: "number.left_bass",
          desk: "number.left_desk",
          presence: "number.left_presence",
          treble: "number.left_treble",
        },
      };
    }

    setConfig(config) {
      if (!config.entities) throw new Error("backplate-card: 'entities' is required.");
      this._config = config;
      this._rendered = false;
    }

    get _entities() { return this._config.entities || {}; }

    set hass(hass) {
      this._hass = hass;
      if (!this._rendered) {
        this._build();
        this._rendered = true;
      }
      this._update();
    }

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
        <div class="title" id="device-name">${this._config.title || "Monitor"}</div>
        <div class="power-row">
          <button class="power-toggle" id="btn-mute">Mute</button>
          <button class="power-toggle" id="btn-sleep">Sleep</button>
        </div>
      </div>

      <div class="body">

        <!-- Room Adaptation -->
        <div class="room-adaptation">
          <div class="section-title">Room Adaptation</div>

          <div class="eq-graphic">
            <svg viewBox="0 0 315 120" style="overflow: visible;">
               <!-- Central reference line -->
               <line x1="20" y1="60" x2="295" y2="60" stroke="rgba(255, 255, 255, 1)" stroke-width="1.5"/>

               <g fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="1.5">
                 <!-- Bass paths (horizontal start → peak → center line) -->
                 <path d="M 20 43 H 45 C 62 43, 62 60, 82 60"/>
                 <path d="M 20 77 H 45 C 62 77, 62 60, 82 60"/>
                 <path d="M 20 94 H 45 C 62 94, 62 60, 82 60"/>

                 <!-- Desk paths -->
                 <path d="M 82 60 C 101 60, 101 77, 120 77 C 139 77, 139 60, 158 60"/>
                 <path d="M 82 60 C 101 60, 101 94, 120 94 C 139 94, 139 60, 158 60"/>

                 <!-- Presence paths -->
                 <path d="M 158 60 C 176 60, 176 43, 195 43 C 214 43, 214 60, 232 60"/>
                 <path d="M 158 60 C 176 60, 176 77, 195 77 C 214 77, 214 60, 232 60"/>

                 <!-- Treble paths (center line → peak → horizontal end) -->
                 <path d="M 232 60 C 251 60, 251 43, 270 43 H 295"/>
                 <path d="M 232 60 C 251 60, 251 77, 270 77 H 295"/>
               </g>
            </svg>

            <!-- Bass LEDs -->
            <div class="led eq-led" id="led-bass-1" style="left:45px; top:43px;"></div>
            <div class="led eq-led" id="led-bass-0" style="left:45px; top:60px;"></div>
            <div class="led eq-led" id="led-bass--1" style="left:45px; top:77px;"></div>
            <div class="led eq-led" id="led-bass--2" style="left:45px; top:94px;"></div>

            <!-- Desk LEDs -->
            <div class="led eq-led" id="led-desk-0" style="left:120px; top:60px;"></div>
            <div class="led eq-led" id="led-desk--1" style="left:120px; top:77px;"></div>
            <div class="led eq-led" id="led-desk--2" style="left:120px; top:94px;"></div>

            <!-- Presence LEDs -->
            <div class="led eq-led" id="led-presence-1" style="left:195px; top:43px;"></div>
            <div class="led eq-led" id="led-presence-0" style="left:195px; top:60px;"></div>
            <div class="led eq-led" id="led-presence--1" style="left:195px; top:77px;"></div>

            <!-- Treble LEDs -->
            <div class="led eq-led" id="led-treble-1" style="left:270px; top:43px;"></div>
            <div class="led eq-led" id="led-treble-0" style="left:270px; top:60px;"></div>
            <div class="led eq-led" id="led-treble--1" style="left:270px; top:77px;"></div>
          </div>

          <div class="eq-labels">
             <div class="eq-col-label" style="left: 45px;"><button class="hardware-btn" id="btn-bass"></button><span class="eq-label-text">Bass</span></div>
             <div class="eq-col-label" style="left: 120px;"><button class="hardware-btn" id="btn-desk"></button><span class="eq-label-text">Desk</span></div>
             <div class="eq-col-label" style="left: 195px;"><button class="hardware-btn" id="btn-presence"></button><span class="eq-label-text">Presence</span></div>
             <div class="eq-col-label" style="left: 270px;"><button class="hardware-btn" id="btn-treble"></button><span class="eq-label-text">Treble</span></div>
          </div>
        </div>

        <div class="section-divider"></div>

        <div class="bottom-row">

          <div style="flex:3;">
              <div class="section-title">Audio IN</div>
              <!-- Audio IN -->
              <div class="audio-in">
                 <div class="audio-in-content">
                     <div class="input-jacks">
                         <div class="jack-row" style="margin-left: 12px;">
                             <div class="rca-port"><div class="rca-inner"><div class="rca-hole"></div></div></div>
                             <div class="jack-label">
                                <div class="led" id="led-input-rca"></div>
                                <span>RCA unbal.</span>
                             </div>
                         </div>
                         <div class="jack-row">
                             <div class="xlr-port">
                                <div class="xlr-pins xlr-pin-1"></div>
                                <div class="xlr-pins xlr-pin-2"></div>
                                <div class="xlr-pins xlr-pin-3"></div>
                             </div>
                             <div class="jack-label">
                                <div class="led" id="led-input-xlr"></div>
                                <span>XLR bal.</span>
                             </div>
                         </div>
                     </div>

                     <div class="input-select-btn">
                        <button class="hardware-btn" id="btn-input"></button>
                        <span class="eq-label-text">Input Select</span>
                     </div>
                 </div>
              </div>
          </div>

          <div class="vertical-divider"></div>

          <div style="flex:2;">
              <div class="section-title">Voicing</div>
              <!-- Voicing -->
              <div class="voicing">
                 <div class="voicing-leds">
                     <div class="v-item"><div class="led" id="led-voicing-pure"></div><span>Pure</span></div>
                     <div class="v-item"><div class="led" id="led-voicing-unr"></div><span>UNR</span></div>
                     <div class="v-item"><div class="led" id="led-voicing-ext"></div><span>Ext</span></div>
                 </div>
                 <button class="hardware-btn" id="btn-voicing"></button>
              </div>
          </div>

        </div>
      </div>
    </ha-card>`;
    }

    _attachListeners() {
      const root = this.shadowRoot;

      // Power
      root.getElementById("btn-mute").addEventListener("click", () => {
        const isMuted = this._stateIs(this._entities.mute, "on");
        this._callSwitch(this._entities.mute, !isMuted);
      });

      root.getElementById("btn-sleep").addEventListener("click", () => {
        const isSleeping = this._stateIs(this._entities.sleep, "on");
        this._callSwitch(this._entities.sleep, !isSleeping);
      });

      // Room Adaptation EQ Buttons
      root.getElementById("btn-bass").addEventListener("click", () => {
        this._cycleNumber(this._entities.bass, [1, 0, -1, -2]);
      });
      root.getElementById("btn-desk").addEventListener("click", () => {
        this._cycleNumber(this._entities.desk, [0, -1, -2]);
      });
      root.getElementById("btn-presence").addEventListener("click", () => {
        this._cycleNumber(this._entities.presence, [1, 0, -1]);
      });
      root.getElementById("btn-treble").addEventListener("click", () => {
        this._cycleNumber(this._entities.treble, [1, 0, -1]);
      });

      // Input Select
      root.getElementById("btn-input").addEventListener("click", () => {
        this._cycleSelect(this._entities.input, ["RCA", "XLR"]);
      });

      // Voicing
      root.getElementById("btn-voicing").addEventListener("click", () => {
        this._cycleSelect(this._entities.voicing, ["Pure", "UNR", "Ext"]);
      });
    }

    _update() {
      if (!this._hass) return;
      const root = this.shadowRoot;
      const e = this._entities;

      const available = this._isAvailable(e.mute);
      root.querySelector(".card").classList.toggle("unavailable", !available);

      const isSleeping = this._stateIs(e.sleep, "on");
      const isMuted = this._stateIs(e.mute, "on");

      const btnMute = root.getElementById("btn-mute");
      btnMute.classList.toggle("active-mute", isMuted);

      const btnSleep = root.getElementById("btn-sleep");
      btnSleep.classList.toggle("active-sleep", isSleeping);

      // Update Room Adaptation LEDs
      [1, 0, -1, -2].forEach(v => this._setLed(`led-bass-${v}`, false));
      const bassVal = parseInt(this._stateValue(e.bass), 10);
      if (!isNaN(bassVal)) this._setLed(`led-bass-${bassVal}`, true);

      [0, -1, -2].forEach(v => this._setLed(`led-desk-${v}`, false));
      const deskVal = parseInt(this._stateValue(e.desk), 10);
      if (!isNaN(deskVal)) this._setLed(`led-desk-${deskVal}`, true);

      [1, 0, -1].forEach(v => this._setLed(`led-presence-${v}`, false));
      const presVal = parseInt(this._stateValue(e.presence), 10);
      if (!isNaN(presVal)) this._setLed(`led-presence-${presVal}`, true);

      [1, 0, -1].forEach(v => this._setLed(`led-treble-${v}`, false));
      const trebVal = parseInt(this._stateValue(e.treble), 10);
      if (!isNaN(trebVal)) this._setLed(`led-treble-${trebVal}`, true);

      // Audio IN LEDs
      const inputVal = this._stateValue(e.input);
      this._setLed("led-input-rca", inputVal === "RCA");
      this._setLed("led-input-xlr", inputVal === "XLR");

      // Voicing LEDs
      const voicingVal = this._stateValue(e.voicing);
      this._setLed("led-voicing-pure", voicingVal === "Pure");
      this._setLed("led-voicing-unr", voicingVal === "UNR");
      this._setLed("led-voicing-ext", voicingVal === "Ext");
    }

    _setLed(id, isOn) {
      const el = this.shadowRoot.getElementById(id);
      if (!el) return;
      if (isOn) {
        el.classList.add("on");
      } else {
        el.classList.remove("on");
      }
    }

    /* HA State helpers */

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

    _cycleNumber(entityId, valuesArray) {
      if (!entityId || !this._hass) return;
      let current = parseInt(this._stateValue(entityId), 10);
      if (isNaN(current)) current = valuesArray[0];

      const idx = valuesArray.indexOf(current);
      const nextVal = (idx === -1 || idx === valuesArray.length - 1) ? valuesArray[0] : valuesArray[idx + 1];

      this._hass.callService("number", "set_value", {
        entity_id: entityId,
        value: String(nextVal),
      });
    }

    _cycleSelect(entityId, valuesArray) {
      if (!entityId || !this._hass) return;
      const current = this._stateValue(entityId);

      let idx = valuesArray.findIndex(v => v.toLowerCase() === (current || "").toLowerCase());
      const nextVal = (idx === -1 || idx === valuesArray.length - 1) ? valuesArray[0] : valuesArray[idx + 1];

      this._hass.callService("select", "select_option", {
        entity_id: entityId,
        option: nextVal,
      });
    }

    getCardSize() { return 6; }
  }

  try {
    customElements.define("backplate-card", BackplateCard);
  } catch (e) {
    if (!e.message.includes("already been used")) {
      console.error("Failed to register backplate-card:", e);
    }
  }

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "backplate-card",
    name: "ADAM Audio Backplate Card",
    description: "Mimics the physical backplate of the ADAM Audio A-Series monitor.",
    preview: false,
    documentationURL: "https://github.com/Perhan35/hass-adam-audio-control",
  });

  console.info(
    `%c ADAM AUDIO BACKPLATE %c v${CARD_VERSION} `,
    "background:#22c55e;color:#111;padding:2px 6px;border-radius:3px 0 0 3px;font-weight:bold",
    "background:#1c1e21;color:#22c55e;padding:2px 6px;border-radius:0 3px 3px 0"
  );
})();
