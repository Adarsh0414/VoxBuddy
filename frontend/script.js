const logEl = document.getElementById("log");
const stateBox = document.getElementById("stateBox");
const ttSlider = document.getElementById("turnTaking");
const cohSlider = document.getElementById("coherence");
const ttVal = document.getElementById("ttVal");
const cohVal = document.getElementById("cohVal");

ttSlider.addEventListener("input", () => (ttVal.textContent = ttSlider.value));
cohSlider.addEventListener("input", () => (cohVal.textContent = cohSlider.value));

let sessionId = null;
let ws = null;

// FIFO queue correlating each outgoing utterance with its response, since
// this demo's WebSocket is simple ordered request/response.
const pendingMeta = [];

function logEvent(text) {
  const div = document.createElement("div");
  div.className = "entry";
  div.style.borderLeftColor = "#3a3f4b";
  div.style.color = "#8a8f9c";
  div.textContent = text;
  logEl.appendChild(div);
  logEl.scrollTop = logEl.scrollHeight;
}

function renderState(data) {
  const others = data.active_partner_ids.filter((id) => id !== data.primary_partner_id);
  stateBox.textContent =
    `primary_partner_id: ${data.primary_partner_id ?? "(none)"}\n` +
    `other group members: ${others.length ? others.join(", ") : "(none)"}\n` +
    `speakers_tracked:  ${data.speakers_tracked}`;
}

function renderTurn(data, meta) {
  const div = document.createElement("div");
  div.className = `entry ${data.role}`;

  const row1 = document.createElement("div");
  row1.className = "row1";
  row1.innerHTML =
    `<span>${meta.speakerLabel ?? ""}</span>` +
    `<span class="role-badge">${data.role}</span>` +
    `<span>conf ${data.confidence}</span>` +
    `<span>${data.latency_ms} ms</span>` +
    (data.partner_switched ? `<span class="switch-badge">PARTNER SWITCH</span>` : "") +
    (data.partner_joined ? `<span class="switch-badge" style="color:#34c77b">JOINED GROUP</span>` : "");

  const text = document.createElement("div");
  text.className = "text";
  text.textContent = meta.utteranceText ? `"${meta.utteranceText}"` : "";

  div.appendChild(row1);
  div.appendChild(text);

  const translated = document.createElement("div");
  translated.className = "translated";
  if (data.translated_text) {
    translated.textContent = `→ ${data.translated_text}`;
  } else {
    translated.style.color = "#565b68";
    translated.textContent = `(filtered by CIE — ${data.notes})`;
  }
  div.appendChild(translated);

  logEl.appendChild(div);
  logEl.scrollTop = logEl.scrollHeight;
}

function connect() {
  sessionId = crypto.randomUUID();
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${protocol}://${location.host}/ws/${sessionId}`);

  ws.onopen = () => logEvent(`Session started (${sessionId.slice(0, 8)}...)`);
  ws.onclose = () => logEvent("Session closed.");

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const meta = pendingMeta.shift() || {};
    renderTurn(data, meta);
    renderState(data);
  };
}

function sendUtterance(speakerLabel, text, targetLang, turnTaking, coherence) {
  pendingMeta.push({ speakerLabel, utteranceText: text });
  ws.send(
    JSON.stringify({
      speaker_label: speakerLabel,
      text,
      target_lang: targetLang,
      turn_taking_score: turnTaking,
      semantic_coherence_score: coherence,
    })
  );
}

document.getElementById("sendBtn").addEventListener("click", () => {
  const speakerLabel = document.getElementById("speakerLabel").value.trim() || "speaker";
  const text = document.getElementById("utteranceText").value.trim();
  if (!text) return;
  const targetLang = document.getElementById("targetLang").value;
  sendUtterance(speakerLabel, text, targetLang, parseFloat(ttSlider.value), parseFloat(cohSlider.value));
});

document.getElementById("resetBtn").addEventListener("click", () => {
  logEl.innerHTML = "";
  if (ws) ws.close();
  connect();
});

const MARKET_SCENARIO = [
  { speaker: "shopkeeper", text: "namaste, kitne ka hai yeh?", tt: 0.9, coh: 0.9, delay: 400 },
  { speaker: "shopkeeper", text: "aap kahan se ho?", tt: 0.85, coh: 0.85, delay: 1200 },
  { speaker: "random_vendor_nearby", text: "aloo le lo, sasta aloo", tt: 0.1, coh: 0.05, delay: 1200 },
  { speaker: "shopkeeper", text: "accha, France se!", tt: 0.85, coh: 0.8, delay: 1200 },
  // Second legitimate voice — room available in the 2-slot group, joins directly.
  { speaker: "shopkeeper_spouse", text: "aur yeh dekhiye, bahut accha hai", tt: 0.9, coh: 0.9, delay: 1400 },
  // Group is now full (2/2) — a same-confidence voice is correctly rejected,
  // since nobody's absent and there's no free slot.
  { speaker: "another_random_vendor", text: "sasta sasta, dekh lo", tt: 0.9, coh: 0.9, delay: 1000 },
  // Wait past the 8s absence timeout so the spouse's slot becomes
  // replaceable, then a new customer takes it — moderate confidence (0.9/0.9)
  // requires two confirming turns from the same voice (see cie/engine.py).
  { speaker: "new_customer", text: "excusez-moi, avez-vous ceci en bleu?", tt: 0.9, coh: 0.9, delay: 9000 },
  { speaker: "new_customer", text: "avez-vous ceci en bleu?", tt: 0.9, coh: 0.9, delay: 1400 },
];

document.getElementById("scenarioBtn").addEventListener("click", async () => {
  logEvent("Running market-stall scenario...");
  for (const [i, step] of MARKET_SCENARIO.entries()) {
    if (step.delay >= 5000) {
      logEvent(`(waiting ${(step.delay / 1000).toFixed(1)}s — clearing the partner-absence timeout before the next speaker)`);
    }
    await new Promise((r) => setTimeout(r, step.delay));
    sendUtterance("scenario:" + step.speaker, step.text, "en", step.tt, step.coh);
  }
});

connect();
