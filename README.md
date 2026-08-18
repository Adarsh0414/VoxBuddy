<div align="center">

# VoxBuddy

**Real-time, hands-free speech translation for travelers — talk, and let your earbuds do the rest.**

VoxBuddy listens through your Bluetooth earbuds, detects who you're actually talking to, translates the conversation live, and speaks the translation back into your ear — no phone screen, no typing, no manual language selection.

</div>

---

## The problem

Existing translation apps make you stop the conversation, pull out your phone, hold it up like a walkie-talkie, and hand it back and forth. That's slow, awkward, and breaks eye contact exactly when you need it most — asking for directions, haggling at a market, or just having a real conversation with someone who doesn't share your language.

## What VoxBuddy does differently

You start a conversation once, then put your phone away. VoxBuddy:

1. **Listens continuously** through your connected earbuds (Bluetooth Classic or BLE)
2. **Figures out who's actually talking to you** — not background noise, not a stranger walking past — using a real signal-fusion engine, not just "loudest voice wins"
3. **Translates what they say in real time**, with rolling conversation context so translations stay coherent turn-to-turn, not isolated sentence-by-sentence guesses
4. **Speaks the translation back into your earbuds**, in a voice you picked, so you never have to look at a screen mid-conversation

---

## The core differentiator: the Conversation Intelligence Engine (CIE)

Most "live translate" demos work great in a silent room with one other speaker. Real conversations aren't like that — there's background noise, other people talking nearby, and the person you're talking to might pause, step away, or hand you off to someone else (a shopkeeper's colleague, a second family member joining in).

The CIE (`backend/cie/`) is the part of VoxBuddy built specifically to handle that:

- **Partner identification via signal fusion** — combines voice similarity, turn-taking fit, and semantic coherence rather than trusting any single signal alone
- **Hysteresis** — won't flip who it thinks your "partner" is on one noisy read
- **Bystander rejection** — a stranger's voice nearby doesn't hijack the conversation
- **Multi-partner conversation groups** — supports up to two active partners at once (a couple, two colleagues), with fast-track/confirmation logic for replacing a member who's gone quiet
- **Self-voice enrollment** — your own voice is registered once at session start and permanently excluded from partner candidacy, so you can never accidentally become "the partner" in your own conversation
- **Incoherence recovery** — self-heals if the conversation state drifts, instead of getting permanently stuck

This engine is fully unit-tested and is the one part of the system that is **not** behind a vendor API — it's original logic.

---

## Features

**Real-time pipeline**
- Live microphone capture → streaming ASR → context-aware translation → TTS playback, end to end
- Adaptive voice-activity gating (skips forwarding silence/ambient noise, not full noise cancellation)
- WebSocket auto-reconnect with exponential backoff — a dropped connection resumes the *same* conversation state instead of restarting

**Authentication**
- Passwordless OTP login via email or phone (hashed codes, single-use, rate-limited, auto-expiring)
- Google Sign-In as an alternative, verified server-side against Google's own public keys
- Bearer-token sessions, optionally backed by Redis for horizontal scaling (SQLite by default, zero setup)

**Conversation history & stats**
- Every conversation is persisted (SQLite) and scoped to the logged-in user
- Real day-streak, per-language conversation counts, and total talk time — computed from actual history, not placeholder numbers

**Mobile app**
- Installable PWA (manifest + service worker, real home-screen icon, full-screen launch)
- Native Android app (Capacitor) with a foreground service to keep listening alive when backgrounded, native Bluetooth audio device detection, and adaptive launcher icons
- iOS project scaffolded (Xcode project generated; full native build requires macOS)

**Vendor-agnostic pipeline**
- Every AI stage (ASR, translation, TTS) sits behind a clean interface (`backend/agents/base.py`) with a working mock and a real vendor adapter, swappable purely via environment variables — no orchestration code changes needed to go from demo mode to production

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, WebSockets, SQLite |
| Speech-to-text | [AssemblyAI](https://www.assemblyai.com/) streaming API |
| Translation | [Anthropic Claude](https://www.anthropic.com/) or [Google Gemini](https://ai.google.dev/) (context-aware, either is a drop-in choice) |
| Text-to-speech | [ElevenLabs](https://elevenlabs.io/) |
| Auth | Custom OTP (SMTP or Brevo for email, Fast2SMS or Brevo for SMS) + Google Sign-In |
| Session storage | SQLite (default) or Redis (optional, for scaling auth tokens) |
| Frontend | Vanilla JS single-page app, PWA (manifest + service worker) |
| Mobile shell | [Capacitor](https://capacitorjs.com/) — real Android Studio/Gradle project + Xcode project |
| Deployment | [Render](https://render.com/) (`render.yaml` blueprint included) |
| Testing | pytest — 180+ backend tests |

---

## Architecture

```
┌─────────────┐        WebSocket (audio)         ┌──────────────────────────┐
│   Mobile /   │ ───────────────────────────────▶ │        FastAPI            │
│  Web client  │                                   │                            │
│  (earbuds    │ ◀─────────────────────────────── │  /ws/{session}/audio      │
│   mic + TTS  │        translated audio           │        │                   │
│   playback)  │                                   │        ▼                   │
└─────────────┘                                   │  Streaming ASR Agent       │
                                                    │  (AssemblyAI / mock)       │
                                                    │        │ final transcript  │
                                                    │        ▼                   │
                                                    │  Conversation              │
                                                    │  Intelligence Engine (CIE) │
                                                    │  — partner? bystander?     │
                                                    │        │ accepted turn     │
                                                    │        ▼                   │
                                                    │  Translation Agent         │
                                                    │  (Claude / Gemini / mock)  │
                                                    │        │ translated text   │
                                                    │        ▼                   │
                                                    │  TTS Agent                 │
                                                    │  (ElevenLabs / mock)       │
                                                    │        │ audio bytes       │
                                                    │        ▼                   │
                                                    │  SQLite persistence        │
                                                    └──────────────────────────┘
```

Every stage in the middle column is a small interface (`agents/base.py`) with a real adapter and a zero-config mock, selected at runtime by environment variable — so the whole pipeline runs end-to-end with no API keys at all, or with real vendors once configured.

---

## Project structure

```
voxbuddy/
├── backend/
│   ├── app.py                    FastAPI app — REST + WebSocket API
│   ├── cie/                      Conversation Intelligence Engine (real, original logic)
│   ├── agents/                   ASR / Translation / TTS interfaces, mocks, and real vendor adapters
│   ├── session/                  Per-session pipeline orchestration + streaming bridge
│   ├── auth_store.py             OTP auth, users, sessions
│   ├── otp_providers.py          SMTP / Brevo / Fast2SMS OTP delivery
│   ├── persistence.py            Conversation history (SQLite)
│   ├── token_store.py            Session tokens (SQLite or Redis)
│   └── tests/                    180+ pytest tests
├── frontend/
│   ├── app-preview.html          The real product UI — Login, Home, Conversation, History, Settings...
│   ├── index.html                CIE developer/testing dashboard
│   ├── manifest.json / sw.js     PWA install + service worker
│   └── privacy.html, terms.html  Legal pages
├── mobile/
│   ├── android/                  Real Android Studio/Gradle project (Capacitor)
│   │   └── .../AudioDevicePlugin.java, ConversationForegroundService.java   Native plugins
│   └── ios/                      Xcode project (Capacitor) — build requires macOS
├── docs/
│   ├── VoxBuddy_PRD_and_Architecture.md
│   ├── vendor_decision.md
│   ├── MOBILE_BUILD.md
│   ├── PLAY_STORE_PUBLISHING.md
│   └── TESTING_REAL_PIPELINE.md
├── render.yaml                   Render deployment blueprint
└── PROGRESS.md                   Full build log — what's done, tested, and what's next
```

---

## Getting started (local development)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open **http://127.0.0.1:8000/app** — this is the real product UI, served with zero configuration. Every AI stage runs in mock mode by default (no API keys needed) so the whole flow — login, conversation, history — works out of the box.

### Enabling real AI providers

Copy `.env.example` to `.env` in `backend/` and fill in whichever vendors you want live:

| Stage | Env vars | Notes |
|---|---|---|
| Translation | `VOXBUDDY_TRANSLATION_PROVIDER=anthropic\|gemini` + matching API key | Either vendor, pick one |
| Speech-to-text | `VOXBUDDY_ASR_PROVIDER=assemblyai` + `ASSEMBLYAI_API_KEY` | Real mic transcription |
| Text-to-speech | `VOXBUDDY_TTS_PROVIDER=elevenlabs` + `ELEVENLABS_API_KEY` | Also needs real voice IDs in `agents/tts_elevenlabs.py` |
| OTP email | `VOXBUDDY_OTP_EMAIL_PROVIDER=smtp\|brevo` + credentials | Falls back to console-printed codes if unset |
| OTP SMS | `VOXBUDDY_OTP_SMS_PROVIDER=fast2sms\|brevo` + credentials | Optional |
| Google Sign-In | `GOOGLE_CLIENT_ID` (+ `GOOGLE_CLIENT_SECRET` for native) | Sign-in button hides itself if unset |
| Redis sessions | `VOXBUDDY_SESSION_STORE=redis` + `REDIS_URL` | Optional; SQLite is the zero-config default |

Every one of these defaults to a working mock — nothing is required to run and explore the app.

### Testing on your phone over WiFi

```bash
uvicorn app:app --host 0.0.0.0 --reload
```

Then open `http://<your-pc-local-ip>:8000/app` from your phone on the same network. Install it to your home screen (Chrome: menu → "Install app"; Safari: Share → "Add to Home Screen") for a full-screen, native-feeling launch.

### Native Android / iOS

`mobile/` is a real Capacitor project — an actual Android Studio/Gradle project and an actual Xcode project, both pointed at your deployed backend URL (`mobile/capacitor.config.ts`). See `docs/MOBILE_BUILD.md` for the full build guide. iOS specifically requires building on macOS with Xcode — there's no way around that platform requirement.

### Deploying

`render.yaml` is a ready-to-use [Render](https://render.com/) blueprint — connect the repo, set your real vendor API keys in Render's dashboard (they're intentionally *not* committed to the blueprint), and it deploys as one FastAPI service serving both the API and the frontend.

---

## Testing

```bash
cd backend
pytest tests/ -v
```

180+ tests covering the CIE's partner-identification logic, streaming pipeline wiring, auth (OTP + Google Sign-In), persistence, TTS/ASR error handling, and session token storage.

---

## What's real vs. what's a mock

Every AI vendor integration (ASR, translation, TTS, OTP delivery) is written as a real, complete adapter against that vendor's documented API — not a stub. Each one also ships with a working mock so the app runs fully offline with zero API keys for development and demos. See `PROGRESS.md` for the full, honestly-tracked breakdown of what's been live-tested against real vendor traffic versus what's built-and-correct-but-unverified.

---

## Roadmap

- [ ] Real-hardware Bluetooth pairing verification (code is written against `@capacitor-community/bluetooth-le`, untested on physical BLE hardware)
- [ ] Full offline degraded mode
- [ ] Speaker diarization / embeddings with a real vendor (currently mocked)
- [ ] Google Play Store publishing (guide ready in `docs/PLAY_STORE_PUBLISHING.md`)

---

## Author

Built by **Adarsh Kumar Singh** — B.Tech CSE, VIT Bhopal.

- GitHub: [@Adarsh0414](https://github.com/Adarsh0414)
- Repo: [github.com/Adarsh0414/VoxBuddy](https://github.com/Adarsh0414/VoxBuddy)
