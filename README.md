# VoxBuddy — Phase 1 (single-folder, run locally in VS Code)

This folder is the whole Phase 1 deliverable: backend (real CIE + mocked
AI agents) and a browser frontend demo, served together by one FastAPI
process. One command runs everything; the same layout is deployable as-is
(e.g. to Render, same pattern as your other projects).

```
voxbuddy/
  backend/
    app.py            <- FastAPI app: REST + WebSocket API, serves frontend/
    cie/               <- the real Conversation Intelligence Engine
    agents/            <- ASR/Translation/TTS/embedding interfaces + mocks
    session/           <- per-session pipeline orchestration
    tests/             <- CIE unit tests
    requirements.txt
  frontend/
    index.html          <- CIE dev/testing dashboard
    product-preview.html <- visual mockup of the REAL product screens (served at /preview)
    style.css
    script.js            <- WebSocket client + scripted market-stall scenario
  docs/
    VoxBuddy_PRD_and_Architecture.md   <- full Phase 1 PRD/architecture
    vendor_decision.md                  <- Phase 2 AI vendor research
  PROGRESS.md          <- what's done / what's left, check this first
  .gitignore
```

## Run it (VS Code / terminal)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open **http://127.0.0.1:8000/** — that's the whole demo, backend and
frontend from one process.

Click **"Run market-stall scenario"** to watch the CIE handle three staged
scenarios live: (1) partner established → bystander correctly ignored →
partner resumes, (2) a **second legitimate voice joins the conversation**
(e.g. the shopkeeper's spouse) while the first partner stays active — real
group support, not a single-partner model — with a subsequent bystander
correctly rejected once the group is full, and (3) a group member who's
gone quiet gets **replaced**, either after two confirming turns (moderate
confidence) or immediately (overwhelming confidence). Note: scenario 2/3
require the ~8s partner-absence timeout to actually elapse in real time, so
the button pauses partway through — that's intentional, see the comment in
`script.js`.

Or drive it by hand: type any utterance, set the sliders (these stand in
for signals real audio agents would produce — turn-taking fit, semantic
coherence), and send it. Same `speaker_label` = same "voice" across sends,
so you can simulate a person leaving and returning.

## Viewing this on your phone

Three different pages now, three different purposes:

- **`http://<your-pc-ip>:8000/`** — the CIE dev/testing dashboard. Good for
  checking the engine works, not what the real app looks like.
- **`http://<your-pc-ip>:8000/app`** — **the real product direction, and
  now genuinely wired to the backend, not just a static mockup.** Opens on
  a real **Login screen** — email or phone, your choice, OTP-based (no
  passwords). Zero-config by default: the code prints to the server
  console and, in dev mode, autofills in the UI so you can test the whole
  flow without a Brevo account (see "Real authentication" below). After
  logging in: Home (start conversation, stats, recent activity), History
  (searchable conversation list — now scoped to YOUR conversations only),
  Transcript Detail, Profile (shows your real email/phone), Settings,
  Setup, and the minimal Conversation-Active screen — glassmorphism
  design, persistent bottom navigation. Tapping "Start Conversation" opens
  a real WebSocket and runs a scripted exchange through the actual CIE.
  Ending a call persists it under your account (SQLite,
  `backend/persistence.py` + `backend/auth_store.py`) — History and stats
  are real and per-user. Your session survives a page reload (token in
  `localStorage`); sign out from Profile to test the login flow again.
  Profile's avatar/name are real now; "day streak" and badges are still
  flavor/mock.

**Install it to your home screen** (real PWA now, not just a bookmark):
on Android Chrome, open `/app` and tap the menu → "Install app" (or you'll
see an install banner). On iOS Safari, tap Share → "Add to Home Screen".
Either way you get a real VoxBuddy icon and it launches full-screen, no
browser address bar — the closest this gets to feeling like a native app
without actually being one (see `PROGRESS.md` for the honest line between
the two).

### Real authentication

Email or phone, your choice — OTP, no passwords. Works with zero config:

```bash
uvicorn app:app --reload
```

The OTP prints to your terminal by default. Set `VOXBUDDY_AUTH_DEV_MODE=1`
(see `.env.example`) and the code also comes back in the API response, so
the login screen autofills it for you — no need to read server logs while
testing.

To send real emails/texts instead, get a [Brevo](https://www.brevo.com)
account (one free API key covers both channels) and set in `.env`:
```
VOXBUDDY_OTP_PROVIDER=brevo
VOXBUDDY_BREVO_API_KEY=...
VOXBUDDY_BREVO_SENDER_EMAIL=you@yourdomain.com
```

- **`http://<your-pc-ip>:8000/preview`** — the earlier, narrower 3-screen
  sketch (Setup/Conversation/Transcript only). Superseded by `/app` — kept
  for reference.

To open any of these from your phone's browser over your home WiFi:

1. Start the server so it listens on your network, not just your PC:
   ```bash
   uvicorn app:app --host 0.0.0.0 --reload
   ```
2. Find your PC's local IP:
   - Windows (PowerShell): `ipconfig` → look for "IPv4 Address" (something
     like `192.168.1.42`)
3. On your phone (same WiFi network), open `http://192.168.1.42:8000/app`
   in any browser.

If it doesn't load, Windows Firewall is probably blocking the port —
allow Python/uvicorn through the firewall for private networks, or
temporarily allow port 8000.

## Tracking progress

`PROGRESS.md` in the repo root is a checklist against the PRD's 5 phases —
what's done and tested, what's built but unverified, what hasn't started.
Check that first before asking "is X done yet."

## Run the tests

```bash
cd backend
pytest tests/ -v
```

## What's real vs. mocked

The **CIE** (`backend/cie/`) is real, tested logic — partner identification
fusion, hysteresis, bystander rejection, **multi-partner conversation
groups** (up to 2 concurrent partners in v1 — a couple at a market stall,
two colleagues in a meeting), member-replacement with fast-track/
confirmation hysteresis, and incoherence recovery.

The **streaming pipeline architecture** (`backend/session/streaming_manager.py`)
is also real — it bridges event-callback-based ASR (partial results, then a
final result per turn — how real vendors actually work, not the simpler
request/response shape the batch demo uses) into the same CIE + Translation
+ TTS pipeline. Both the mock (`agents/mock_streaming_asr.py`) and the real
AssemblyAI scaffold (`agents/asr_assemblyai.py`) implement the identical
protocol, so this is a tested integration point, not just a stub.

**ASR/Translation/TTS/speaker-embedding vendor calls are mocked** behind
vendor-agnostic interfaces (`backend/agents/base.py`) so real providers can
be dropped in during Phase 2 without touching orchestration code — with
translation already having one real, working implementation (see below).

Also real: **self-voice enrollment** (`cie.enroll_self()` /
`session.enroll_self()` / `POST /api/session/{id}/enroll_self`) — the user's
own voice is registered once at session start and permanently excluded from
partner candidacy, fixing a real bug where the user's own speech could
consume a conversation-group slot. `simulate.py` demonstrates it directly.

## Phase 2: real translation (optional)

Translation now has a real, tested provider — Claude, called with rolling
conversation context so it actually satisfies FR-6 (context-aware
translation), not just isolated-sentence MT. See `docs/vendor_decision.md`
for the full vendor research (ASR, translation, TTS, diarization) behind
this choice.

To turn it on:

```bash
cp .env.example .env
# edit .env:
#   VOXBUDDY_TRANSLATION_PROVIDER=anthropic
#   ANTHROPIC_API_KEY=sk-ant-...
```

Restart `uvicorn app:app --reload` and the demo now calls real Claude for
translation. Leave `.env` absent or `VOXBUDDY_TRANSLATION_PROVIDER=mock` to
keep everything offline/free, which is still the default.

ASR (`backend/agents/asr_assemblyai.py`) and TTS
(`backend/agents/tts_elevenlabs.py`) are scaffolded against real vendor
SDKs but **not yet live-tested** (no credentials in this build
environment). The streaming *interface* gap flagged earlier — the old ASR
protocol was request/response, but real vendors work via event callback —
is closed: `agents/base.py`'s `StreamingASRAgent` protocol, a working mock
(`agents/mock_streaming_asr.py`), and the bridge into the existing
pipeline (`session/streaming_manager.py`) are all implemented and covered
by 7 tests. `agents/asr_assemblyai.py` now conforms to that exact protocol
— swapping the mock for the real adapter should require no changes
downstream, once there's a real API key to verify it against.

## Native Android + iOS (real project scaffolds, not built here)

`mobile/` — a real Capacitor project, generated with Capacitor's own
official CLI: an actual Android Studio/Gradle project and an actual Xcode
project, both with full icon/splash assets already generated for every
required size on both platforms. This sandbox is Linux with no Android
SDK and no macOS, so the actual builds couldn't complete here — confirmed
live (Gradle itself couldn't even download; iOS fundamentally requires a
Mac, an Apple platform rule with no workaround). Full honest guide,
exactly what to do on your own machine for each platform:
`docs/MOBILE_BUILD.md`.

## Publishing to Google Play

Short version: **yes, possible, via Trusted Web Activity** (Google's
official PWA-to-Android-app path) — **Apple App Store is not possible**
for a PWA, they reject "repackaged websites" outright. Full step-by-step
guide, written honestly for exactly where this project stands right now:
`docs/PLAY_STORE_PUBLISHING.md`. A real privacy policy page is already
built (`/privacy` — edit the placeholder contact email before publishing).

## Resilience: reconnection + Redis-backed sessions

Two Phase 3/4 items, both real and live-tested, not just written:

**WebSocket reconnection.** If the connection drops unexpectedly mid
-conversation (network blip, backend restart), the app auto-reconnects
with exponential backoff and resumes the *same* CIE state — the
previously-established partner is still recognized afterward, not
re-detected from scratch. A deliberate "End Call" does not trigger this.
Verified by forcing a live drop mid-conversation and confirming both the
reconnect and the state preservation.

**Redis-backed auth tokens** (optional — sqlite is the zero-config
default). Scoped honestly: this covers bearer session tokens, not live
conversation state — see `backend/token_store.py`'s architectural note for
why those are different problems (a live conversation is bound to one open
WebSocket on one process; the correct production fix for scaling *that* is
sticky sessions at a load balancer, not Redis). To turn it on:
```
VOXBUDDY_SESSION_STORE=redis
VOXBUDDY_REDIS_URL=redis://localhost:6379/0
```
Requires a running Redis (`redis-server`, or any managed Redis in
production). Verified live: requested a token with this enabled, confirmed
via `redis-cli` that it physically exists as a Redis key (not in
`voxbuddy.db`), and confirmed `/api/auth/me` resolves it correctly.

## Publishing / next steps

- This is a single deployable service (FastAPI serving its own static
  frontend), so it can go straight onto Render the same way CampusVibe/
  CallBeacon are hosted — `uvicorn app:app --host 0.0.0.0 --port $PORT`
  (set `VOXBUDDY_TRANSLATION_PROVIDER`/`ANTHROPIC_API_KEY` as Render env vars
  if using real translation, plus the auth/Redis vars above as needed).
- What's left genuinely needs resources this build environment doesn't
  have: live-testing real streaming ASR (AssemblyAI), TTS (ElevenLabs), and
  OTP delivery (Brevo) all need real vendor credentials; a real native
  mobile app needs an actual Android/iOS toolchain and device to test on,
  neither of which exist here. Everything in this repo that COULD be
  built and verified without those has been — see `PROGRESS.md` for the
  full honest breakdown of what's real vs. what's still mock or scaffolded.
- See `docs/VoxBuddy_PRD_and_Architecture.md` for the full product/system
  design this implements against, and `docs/vendor_decision.md` for the
  Phase 2 AI vendor research and rationale.
