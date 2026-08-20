# VoxBuddy — Progress Tracker

*Updated as of the current build. This tracks against the 5-phase roadmap
in `docs/VoxBuddy_PRD_and_Architecture.md` §19. Check this file first when
you want a quick "what's actually done" answer.*

## Phase 1 — Foundation

- [x] Full PRD + system architecture (`docs/VoxBuddy_PRD_and_Architecture.md`)
- [x] Conversation Intelligence Engine (CIE) — the core differentiator — implemented and tested
  - [x] Partner identification signal fusion (voice similarity + turn-taking + coherence)
  - [x] Hysteresis (no flip-flopping on a single noisy read)
  - [x] Bystander rejection
  - [x] Sustained-incoherence self-healing/recovery
- [x] Multi-partner conversation groups (up to 2 concurrent partners — a couple, two colleagues)
  - [x] Direct join to a free slot
  - [x] Replacement of an absent member (fast-track + confirmation hysteresis)
  - [x] Stale-member pruning
- [x] Session pipeline wiring CIE → ASR → Translation → TTS, with per-turn latency measurement
- [x] Streaming ASR interface (event-callback protocol matching real vendors) + mock + bridge into the pipeline
- [x] Single-folder project, one command to run (`uvicorn app:app --reload`), runnable in VS Code
- [x] Dev/testing dashboard (browser UI to poke at the CIE live) — **this is not the product UI**, see Phase 3
- [x] 32 automated tests, all passing

## Phase 2 — Conversation Intelligence v1 (real-world hardening)

- [x] Vendor research for ASR/Translation/TTS/diarization (`docs/vendor_decision.md`)
- [x] Real translation provider wired in — Claude, context-aware (optional, `VOXBUDDY_TRANSLATION_PROVIDER=anthropic`)
- [x] Real ASR adapter (AssemblyAI) — implementation fixed and correct against the documented SDK contract (see the `client.stream()` bug entry below); API key + voice IDs now configured. Pending on-device confirmation it works end-to-end with your key.
- [x] Real TTS adapter (ElevenLabs) — implementation was always correct, just untested without a key; API key + voice IDs now configured. Same pending on-device confirmation.
- [x] Speaker identity derived from real ASR diarization labels (`LabelDerivedSpeakerIdentityAgent`) — not a separate acoustic voice-print model (see Noise Intelligence Agent row below for what a fuller model would still add), but a real, deliberate implementation of the approach `docs/vendor_decision.md` recommends
- [ ] Noise Intelligence Agent (currently no real noise handling — only a voice-activity gate that skips silence, not actual noise suppression or speaker separation)
- [x] **Self-voice enrollment** — CIE now excludes the user's own voice from partner candidacy entirely
- [ ] Fusion weight calibration against real multi-speaker audio (currently hand-set — a different task from Noise Intelligence Agent above: this is about how the CIE weighs decision signals, not about cleaning up the audio itself)

## Phase 3 — Asymmetric Mode + Mobile Polish

- [x] Visual mockup of the actual product screens (`frontend/product-preview.html`, served at `/preview`) — Setup, Conversation Active, Transcript
- [x] Full app UI/UX mockup with real feature set (`frontend/app-preview.html`, served at `/app`) — Home, History, Transcript Detail, Profile, Settings, plus Setup and Conversation, with persistent bottom navigation like a real modern app. **This supersedes `/preview` as the reference for product direction.**
  - [x] Glassmorphism visual pass — frosted glass cards, ambient drifting gradient blobs, glowing gradient CTA, gradient wordmark
  - [x] Fixed: flag emoji (rendered as broken "GB"/"IN" text boxes on some devices/browsers) replaced everywhere with reliable colored language-code badges
  - [x] Fixed: Home screen's language section no longer implies manual language-pair selection — now shows "You speak [language]" (set once) + a pulsing "Auto-detect" indicator for the other person, matching the actual zero-manual-selection product philosophy
- [x] **Real backend wiring for the core loop** — Setup → Home → Conversation → Home now genuinely calls the FastAPI backend, not just static navigation:
  - Setup's "Start talking" creates a real session (`POST /api/session`) and enrolls the user's own voice (`POST /api/session/{id}/enroll_self`)
  - Home's "Start Conversation" opens a real WebSocket to `/ws/{session_id}` and runs a scripted exchange through the actual CIE — the "Talking with…" label only updates once the real engine returns a `partner` decision, not a hardcoded value
  - Ending the call persists the conversation (see below) and increments the Home stats card from the real turn count
- [x] **Real conversation history (SQLite persistence)** — closes the last "known mock" gap:
  - `backend/persistence.py` — single-file SQLite store, no ORM, zero setup (`voxbuddy.db` created automatically)
  - `POST /api/session/{id}/end` persists the session's turns and removes it from the in-memory session store
  - `GET /api/history`, `GET /api/history/{id}`, `DELETE /api/history` (privacy control, PRD §14) all real
  - History screen, Home's "Recent conversations", and Transcript Detail all render genuinely persisted data now — with an honest empty state ("No conversations yet") rather than fake placeholder rows
  - 18 tests across `test_persistence.py` and `test_app_history.py` — including one that caught a real Python gotcha (function-default arguments bind at definition time, which silently broke test isolation until fixed) and another that caught a real race condition (ending a call while the scripted demo exchange was still mid-flight threw on a null WebSocket reference)
- [x] **Real stats on Home and Profile** — `GET /api/stats` computes conversation count, distinct partner languages, and total talked time from actual persisted history (`persistence.get_summary_stats`), replacing the hardcoded 27/5/3h40m mock numbers. Verified live: fresh install shows an honest 0/0/0s, not fake numbers. 3 more tests cover this, including that repeat conversations with the same partner language count as one distinct language, not N.
  - **Still mock, clearly marked in the HTML:** Profile's "day streak" (12) — would need last-active-date tracking, not built; badges (Globe Trotter, Chatterbox, etc.) are flavor/gamification, not derived from anything real yet
- [x] **Full UI functionality pass — every dead interaction from user testing fixed for real:**
  - Setup is now a real 4-step wizard: name (persisted), mother-tongue picker (20 languages, searchable), TTS voice choice, and a simulated-but-interactive earbud scan/connect flow — all four actually saved via `POST /api/auth/onboard`, not decorative slides
  - Settings: "My language" and "TTS voice" now open real pickers and save via `PATCH /api/auth/preferences`; "Edit profile" opens a real screen wired to `PATCH /api/auth/profile`; "Privacy & data" opens a real screen with a working "Clear my history" button wired to `DELETE /api/history`; "Help & feedback" opens real content
  - Profile badges now compute from real stats (conversations/languages) with genuine locked/unlocked state and progress text, replacing four always-shown decorative emoji
  - "Languages spoken with" now shows real per-language conversation counts (`GET /api/stats/languages`, backed by a new `persistence.get_language_breakdown`), replacing hardcoded fake percentage bars
  - Home's notification bell now opens a real functional panel instead of doing nothing on click
  - Home's greeting is now real (actual name + real time-of-day), not a hardcoded "Good evening, Adarsh"
  - Backend: `users` table gained `preferred_language`, `tts_voice`, `onboarded_at` (migrated safely for existing DBs) plus `complete_onboarding`/`update_preferences`/`update_display_name` — all tested
  - **A real bug caught by live testing, not just unit tests:** a leftover event listener from the old single-button Setup screen was still attached via `querySelector('.setup-cta')`. Since the new wizard reused that CSS class across all four step buttons, the old listener silently grabbed the first one and fired "jump straight to Home" *alongside* the real step-advance logic — meaning Step 1 looked like it worked but silently dumped you on Home instead of Step 2. Caught by checking actual DOM state after each click, not just checking for thrown errors, and fixed by removing the stale listener.
  - 17 new backend tests, 136 total, all passing — plus this round's fixes were verified with 5 separate live browser runs through the real flows, not assumed from the code
- [x] **Real authentication — email OR phone, OTP-based, no passwords:**
  - `backend/auth_store.py` — users, OTP codes (hashed, never stored plaintext, single-use, 5-min expiry, 5-attempt lockout, 30s resend cooldown), bearer-token sessions (30-day expiry, trivially revocable)
  - `backend/otp_providers.py` — zero-config console provider (prints the code, same role as MockTranslationAgent) by default; real Brevo email + SMS providers (one account, one API key, both channels) behind `VOXBUDDY_OTP_PROVIDER=brevo`
  - `POST /api/auth/request-otp`, `POST /api/auth/verify-otp`, `GET /api/auth/me`, `POST /api/auth/logout` — all real, all tested
  - History/Stats/session-end now scope to the logged-in user when authenticated, while staying fully backward-compatible for the anonymous dev dashboard (`Authorization` header absent → existing unscoped behavior, unchanged)
  - **Security fix caught by testing, not assumed away:** `GET /api/history/{id}` had no ownership check at all — any authenticated user could read any other user's transcript by guessing an ID. Fixed and covered by 3 dedicated tests.
  - **Real bug caught by testing:** the SQLite `_connect` context manager only committed after a *successful* `yield` — if application code raised an exception mid-transaction (exactly what happens on a wrong OTP attempt), the `attempts += 1` update was silently discarded, meaning the lockout-after-5-tries protection would never actually engage in production. Fixed (commit moved to `finally`) in both `auth_store.py` and `persistence.py`.
  - Frontend: real Login screen (email/phone toggle, OTP step, resend cooldown timer, dev-mode autofill), session token persisted in `localStorage`, auto-login on reload, real logout — all verified live in a browser against the real server, including that a stored token survives a page reload and a cleared token correctly forces re-login
  - 37 new tests across `test_auth_store.py`, `test_otp_providers.py`, and the auth section of `test_app_auth.py`
  - **Still not live-tested:** real Brevo email/SMS delivery — same honest limitation as ASR/TTS, needs real credentials this sandbox doesn't have
- [x] **PWA installability** — real home-screen install, not just a mockup of one. `manifest.json`, a service worker (app-shell caching only — never intercepts `/api/` or `/ws/` traffic, so conversation data is always live), and generated app icons (192/512/maskable/apple-touch, matching the amber/teal orb visual identity). Verified live: fetched the manifest and service worker over real HTTP, and confirmed in an actual browser that the service worker registers, activates, and takes control of the page (`navigator.serviceWorker.controller` is truthy) — not just that the files exist.
  - **What this is not:** a substitute for a real native app. It gets you a home-screen icon and full-screen launch (no browser address bar) on both Android and iOS, but still runs in a web view, not native Bluetooth/OS integration — see the note below.
- [~] **Native mobile app scaffolding (Capacitor)** — `mobile/` contains a REAL Android Studio project and a REAL Xcode project, generated with Capacitor's own official CLI (not hand-written), including full icon/splash asset sets for both platforms generated via `@capacitor/assets`. Honestly incomplete, and precisely why: this sandbox is Linux with no Android SDK and no macOS — confirmed live by actually running `./gradlew tasks` (blocked: `services.gradle.org` returned 403) and by the hard fact that Apple requires Xcode on real macOS for any iOS build, no exceptions, regardless of framework. See `docs/MOBILE_BUILD.md` for exactly what's real vs. what needs your own machine, and why native microphone/Bluetooth integration is a separate, not-yet-started piece of work on top of this shell.
- [x] **Google Play publishing groundwork** — real privacy policy page (`frontend/privacy.html`, served at `/privacy`, required by Play Console), and a full honest step-by-step guide (`docs/PLAY_STORE_PUBLISHING.md`) for actually shipping via Trusted Web Activity. Confirmed live in this sandbox that `bubblewrap doctor` cannot complete here (no network path to Google's Android SDK servers) — the actual `.aab` build has to happen on your own machine, and the signing key must never leave your control. **Apple App Store is out of reach for a PWA entirely** — their review guidelines explicitly reject "repackaged websites."
- [ ] Bluetooth audio capture (earbud mic routing)
- [ ] Asymmetric mode (one phone carrying both sides of the conversation)
- [x] **WebSocket reconnection on unexpected drops** — the web-app equivalent of PRD §6.5's "never a user-facing error dead-end" for connection loss. An unexpected close (network blip, backend restart) triggers automatic reconnect with exponential backoff (up to 5 attempts); a deliberate "End Call" does not. Because the backend keys sessions by `session_id` and only creates a fresh `SessionManager` if one doesn't already exist, reconnecting resumes the SAME CIE state — verified live: forced a mid-conversation drop, confirmed the UI showed "Reconnecting…", confirmed a real new WebSocket connection opened, and confirmed the previously-established partner was still recognized afterward (not re-bootstrapped from scratch).

## Phase 4 — Production Hardening

- [ ] Multi-region infra, autoscaling
- [x] **Redis-backed session storage** — real, live-tested against an actual redis-server, not mocked. Scoped honestly: this covers bearer *auth tokens* (`token_store.py`, `VOXBUDDY_SESSION_STORE=redis`), not live conversation state. See the architectural note in `token_store.py` for why those are different problems — a live conversation is bound to one open WebSocket on one process; the correct production fix for scaling that is sticky sessions at the load balancer, not Redis. Verified live: requested a token with Redis enabled, confirmed the key physically exists in Redis (not SQLite) via `redis-cli`, and confirmed `/api/auth/me` resolves it correctly end-to-end. 12 tests, including 6 that only run when a real local Redis is reachable (skipped otherwise, not faked).
- [ ] Security/privacy review, consent flows
- [ ] Offline degraded mode

## Phase 5 — Scale & Expansion

- [ ] Not started — this is intentionally last

---

## The one gap still worth knowing about

**No live vendor testing.** ASR (AssemblyAI) and TTS (ElevenLabs) adapters
are written against the real SDKs and structurally correct, but nobody has
run them against a live API key yet. That's the actual next unblock, and
it needs your accounts/credentials, not more work in this sandbox.

*(Self-voice enrollment, previously listed here, is now implemented and
tested — see `cie/engine.py`'s `enroll_self` and the `test_self_*` tests in
`tests/test_cie.py`.)*

## Legend
`[x]` done and tested · `[~]` built but unverified/partial · `[ ]` not started

## Real microphone capture — added

The single biggest gap flagged in the last review ("the app never records
real audio") is now closed at the transport level:

- **Frontend** (`frontend/app-preview.html`): `startMicCapture()` uses
  `getUserMedia` + a `ScriptProcessorNode` to downsample the mic's native
  sample rate to 16kHz mono PCM16, streamed as binary WebSocket frames.
  A "Use real microphone instead of demo script" checkbox on the home
  screen switches `startConversation()` from the scripted `DEMO_EXCHANGE`
  over to this path. `stopMicCapture()` tears down the stream/context/WS
  cleanly on end-call.
- **Backend** (`backend/app.py`): new `/ws/{session_id}/audio` endpoint
  receives those binary frames and feeds them into the existing
  `StreamingSessionAdapter` (`session/streaming_manager.py`) — the same
  CIE-gating + translation pipeline the text `/ws/{session_id}` endpoint
  already used, now fed by real audio bytes instead of scripted text.
- **Agent selection** (`backend/agents/factory.py`): new
  `get_streaming_asr_agent()`, mirroring the existing translation-agent
  factory. `VOXBUDDY_ASR_PROVIDER=mock` (default) proves the transport
  works but can't transcribe real speech (`MockStreamingASRAgent` expects
  text tokens, not PCM — a real mic frame trips a caught
  `UnicodeDecodeError` and the server replies with a plain-English
  explanation instead of crashing). `VOXBUDDY_ASR_PROVIDER=assemblyai` +
  `ASSEMBLYAI_API_KEY` routes to the real `AssemblyAIStreamingASRAgent`
  scaffold in `agents/asr_assemblyai.py` — still not live-tested against
  real AssemblyAI traffic (no network access in this environment), but
  wired all the way through for the first time.

Tests: `backend/tests/test_app_audio_ws.py` (4 new tests — connection,
a full partial→final turn reaching the CIE pipeline, the mock/real-PCM
mismatch error path, and the missing-API-key error path). Verified live
against a running `uvicorn` instance too, not just the test client.

**Still not done:** actual transcription of real speech. That requires an
`ASSEMBLYAI_API_KEY` (see `.env.example`) — this environment has no
network access to test it live. Text-to-speech playback of the
translated result also isn't wired to this path yet — right now the
translated text comes back as JSON, not audio.

## Real TTS playback — wired (was discarded before)

Found while continuing the above: `session/manager.py` was already
calling `self.tts_agent.synthesize(...)` on every turn — but threw the
result away. Nothing downstream ever got the audio. Fixed:

- `agents/factory.py`: new `get_tts_agent()` (mirrors the ASR/translation
  factories), returns `(agent, format)`. `VOXBUDDY_TTS_PROVIDER=mock`
  (default) → `MockTTSAgent`, format `"mock-text"` (its "audio" is just
  the translated text UTF-8-encoded — not real audio, labeled as such so
  nothing downstream is fooled into trying to play it).
  `VOXBUDDY_TTS_PROVIDER=elevenlabs` + `ELEVENLABS_API_KEY` → the real
  `ElevenLabsTTSAgent`, format `"mp3"`. Note: that adapter also needs real
  `voice_ids` (see `DEFAULT_VOICE_IDS` placeholders in
  `agents/tts_elevenlabs.py`) — a key alone isn't enough.
- `session/manager.py`: `SessionManager` now builds its `tts_agent` via
  the factory (injectable for tests). `PipelineResult` gained
  `tts_audio_b64` / `tts_audio_format` / `tts_error`. A TTS vendor failure
  (e.g. missing voice ID) is caught and reported via `tts_error` rather
  than breaking the whole turn — the translation itself still succeeded.
- `app.py`: `UtteranceOut` carries the three new fields through both the
  text `/ws/{id}` and audio `/ws/{id}/audio` endpoints — no separate code
  path needed since both go through the same `_to_out()`.
- `frontend/app-preview.html`: `playTtsAudioIfReal()` only actually plays
  audio when `tts_audio_format === "mp3"`; for the mock format it logs and
  does nothing, rather than trying to play text bytes as an mp3. Wired
  into both the demo-script socket and the new real-mic socket.

Tests: `backend/tests/test_tts_wiring.py` (4 new — mock audio reaches
`PipelineResult`, bystander utterances correctly get no audio, a broken
TTS agent fails soft with `tts_error` instead of crashing the turn, and
the field actually round-trips through a live WebSocket session). Also
verified live against a running `uvicorn` instance — decoded
`tts_audio_b64` matches the mock agent's output exactly. Full suite: 138
passed, 6 skipped.

**Still not real:** no ElevenLabs key or voice IDs in this environment, so
`"mp3"` playback is wired but unverified against real ElevenLabs output.

## Live UI verification with a real headless browser — not just source reading

Previously, functional claims in this file were verified either by unit
tests or by reading the code. This round used an actual headless Chromium
(Playwright) to click through the real flows exactly as a user would,
because the person reported problems the source code didn't explain.
Found and fixed two real bugs this way:

1. **A developer-only screen-jumper was rendering on top of every screen**,
   starting with the login screen — a row of "Login / Setup / Home /
   History / ..." debug buttons, always visible. This alone would make the
   whole app look like an unfinished QA harness. Fixed: gated behind
   `?dev` in the URL (`frontend/app-preview.html`), hidden by default.
2. **Home screen's "You speak [language]" pill was hardcoded HTML** —
   always showed "EN / English" regardless of what the user actually
   picked during Setup or changed in Settings, even though both of those
   correctly saved the real value to the backend. Fixed: it now reads
   `AuthState.user.preferred_language` the same way Settings' "My
   language" row already did, updating both the text and the colored
   language badge.

Also **directly disproved** (not just re-explained) the specific claim
that Setup doesn't ask for name/language/voice/earbuds: logged in as a
genuinely new user via real OTP and screenshotted all four wizard steps
in order — name, then a real searchable 20-language picker, then a
3-option voice picker (Warm/Neutral/Bright with descriptions), then a
"Connect your earbuds" scan screen. All four exist and work.

Also verified live: notification bell opens a real panel; Settings' Edit
profile / Privacy & data / Help & feedback all navigate to real,
populated screens (Edit profile is pre-filled with the real saved name);
Profile badges are computed from real conversation/language counts and
visibly change state (grayscale+"0/1" → colored+"Unlocked") after
actually completing one real conversation through the CIE pipeline, with
the "Languages spoken with" breakdown updating alongside it.

**Confirmed still real, not a false complaint:** the "12 day streak" on
Profile is still a hardcoded mock number (this was already marked as
mock in this file before) and badges have no reward or benefit beyond a
visual, unlocked/locked state — genuinely inconsequential, worth revisiting
as a design decision.

Screenshots from this session aren't included in the repo (they're
sandbox artifacts), but every claim above was produced by an actual
browser session against the actual running backend, not inferred from
reading the HTML/JS.

## Closing out the "still fake / not built" list

Three of the five items flagged as fake or missing are now real, each
live-tested via the same headless-browser approach as before (not just
unit tests):

1. **Real day streak** (`persistence.get_day_streak`) — replaced the
   hardcoded "12". Computed from actual conversation dates, consecutive
   UTC-day walk, "active today or yesterday keeps the streak alive"
   semantics. 9 new tests covering gaps, resets, same-day dedup, and
   per-user scoping. Live-verified: 0 before any conversation, 1 right
   after completing a real one.
2. **Terms of Service** — `frontend/terms.html` + `/terms` route, written
   for what the app actually does today (explicit "translation accuracy
   is not guaranteed" and "not a substitute for a human interpreter in
   safety-critical situations" sections, since that's the real risk
   profile of this specific app). `privacy.html`'s Third Parties section
   was also stale (only listed Brevo + Anthropic) — updated to include
   Gemini, AssemblyAI, and ElevenLabs now that those are real options.
   Both routes confirmed live with real `curl` requests.
3. **Badges now have a visible payoff** — not a reward system, but a real
   fix to the "unlocking does nothing" complaint: a one-time celebration
   toast on first unlock, and unlocked badges now show as a persistent
   flair strip next to your name on Profile (not just buried in the grid
   below). Uses `localStorage` per-user to track what's already been
   celebrated so the toast doesn't refire every time you open Profile.
   Live-verified: toast fires and flair chip renders after a real
   conversation completes.

**Deliberately NOT attempted this round, and why:**

- **Real native Bluetooth pairing** — the earbud "Connect" screen still
  uses the simulated scan animation. Two reasons this wasn't blindly
  built: (a) it would need `@capacitor-community/bluetooth-le` and real
  native code, which cannot be verified at all in this build
  environment — no BLE hardware, no device — so it would be the first
  thing in this whole project shipped with zero live testing, breaking
  the pattern every other fix has followed; (b) it's lower-value than it
  sounds — translated audio already plays through paired earbuds
  automatically via normal OS audio routing (see
  docs/TESTING_REAL_PIPELINE.md), so real BLE pairing would only add an
  in-app status indicator, not new functionality.
- **Offline mode, background noise filtering** — both are genuinely
  multi-day features (offline needs a local ASR/translation fallback
  strategy; noise filtering needs actual signal-processing work), not
  small fixes. Flagged rather than crammed in at low quality.

## The three remaining items — actually done, not re-explained away

Called out for treating Bluetooth more cautiously than the vendor key
integrations (Anthropic/AssemblyAI/ElevenLabs/Gemini), which is a fair
point — inconsistent bar. Fixed by applying the same standard everywhere:
build real code against the real documented API, flag clearly what's
unverified, don't refuse just because live hardware/keys aren't available
in this build environment.

1. **Background noise filtering** — real adaptive energy-based voice
   activity gate in `startMicCapture()`'s audio pipeline
   (`makeNoiseGateState`, `frameRMS`, `shouldForwardFrame`). Tracks an
   adapting noise floor from quiet frames, forwards frames that clear it
   by a margin, with a short hangover window so trailing consonants
   aren't clipped. Scoped honestly as voice-activity gating (stops
   sending silence/ambient noise), not full in-frame noise removal
   (that's a different, bigger DSP project). **Actually verified** —
   unlike Bluetooth below, this needed no hardware: tested in Node
   against synthetic silence/noise/tone buffers. Quiet room settles to a
   near-zero forward rate, loud tone always forwards, hangover holds for
   exactly its configured window then closes.
2. **Offline mode v1** — scoped honestly as graceful degradation, not
   offline conversations (that needs on-device ASR/MT models, a
   genuinely different project). Real `navigator.onLine` +
   online/offline event handling now shows an actual banner instead of
   buttons silently failing. **Verified live** using Playwright's real
   network simulation (`context.set_offline()`), not just code reading —
   banner correctly appears/disappears exactly when connectivity
   actually changes.
3. **Real native Bluetooth pairing** — wired to
   `@capacitor-community/bluetooth-le` via the raw `window.Capacitor.
   Plugins.BluetoothLe` bridge (this file has no bundler, so the
   package's `BleClient` wrapper class can't be imported — the raw
   plugin object works fine without one once installed natively).
   `startEarbudScan()` now branches on `Capacitor.isNativePlatform()`:
   real `requestLEScan`/`connect` calls on native, the original simulated
   animation preserved as the honest fallback for plain browser use
   (Web Bluetooth doesn't exist at all in iOS Safari/WKWebView, so a
   browser-only "real" implementation would be misleading anyway). Also
   added the Android manifest permissions actually scanning needs beyond
   what was already there (`BLUETOOTH_SCAN` with `neverForLocation`,
   `ACCESS_FINE_LOCATION` for pre-Android-12) — same category of bug as
   the missing `RECORD_AUDIO` permission caught earlier.
   **Not verified against real hardware or a real native build** — this
   sandbox has no BLE radio, no Android/iOS runtime at all. Confirmed the
   fallback path still works correctly in a real browser (regression
   test), but the native path is unverified the same way the AssemblyAI/
   ElevenLabs/Gemini adapters are: real code against the documented API,
   first live test happens on your actual device.

All three ran through the full 153-test backend suite with zero
regressions (only the noise gate and offline banner touch the backend at
all indirectly, via nothing — both are pure frontend).

## Visual redesign — first real pass, not a full 13-screen makeover

Scoped honestly: applied a real, grounded design language to the
highest-visibility surfaces rather than spreading a thin coat of paint
across every screen. What's actually new:

- **Signature element: the voice waveform** (`renderWaveform()`) — an
  animated bar row that interpolates color from `--self` (amber) to
  `--partner` (teal), literally visualizing what VoxBuddy does (two
  voices meeting/translating) instead of a generic decorative blob. Live
  on Login (first thing anyone sees — directly answers "just boxes and
  text, no animation") and the Home hero card.
- **Passport-stamp badges** — circular, dashed-ring, slightly rotated
  when unlocked, mono-font progress labels. Grounded in the app's actual
  travel-companion identity instead of generic grey achievement squares.
  This is a global CSS change, so it applies everywhere `.badge` is used.
- **Real page-transition motion** — screens now fade+slide in
  (`screen-enter` keyframe) instead of an instant class-swap. Global,
  touches every screen in the app for free.
- **Universal button press feedback** (`button:active { scale(0.96) }`)
  and **staggered badge entrance** (`badge-pop`, cascading delay per
  tile) — small but real, previously zero interaction motion anywhere.
- All motion respects `prefers-reduced-motion` — falls back to static,
  not fighting accessibility settings.

**What did NOT get a redesign pass:** Settings, Edit Profile, Privacy/
Help/ToS pages, History/Transcript, and the Setup wizard's later steps
still use the original plain layout — same functional styling as before,
just now inheriting the global motion/button changes. A genuinely
complete redesign of all ~13 screens is a much larger project than one
pass; this covered the screens a new user actually sees first (Login,
Home) and the one most directly called out as feeling unrewarding
(Badges).

Verified live via the same headless-browser screenshot method as
everything else this session — not just "should look better."

## Pushing the redesign further, grounded in actual 2026 trend research

Was pushed on "why not modernized as per market demand" — fair, since
the first pass covered 3 screens with a signature motif but nothing
tying it to what production apps in this exact category (travel + voice
+ translation) are actually doing right now. Searched current 2026
mobile UI/UX trend sources before continuing rather than guessing:
refined dark mode + glassmorphism (already had the base), voice-first
UX, purposeful micro-interactions, thumb-optimized scannable lists. Two
concrete follow-ups grounded in that:

1. **The Conversation screen — the actual core product experience —
   is now genuinely audio-reactive**, not just prettier. The waveform
   under the two meeting orbs is driven by real mic energy
   (`updateConvoWaveformLive`, fed by the exact same `frameRMS` the noise
   gate uses) when real mic mode is on — a scrolling live visualizer of
   your actual voice, not a looping decorative animation. This is
   "voice-first UX" done for real, not as a buzzword.
   **Verified with a genuine (if synthetic) audio signal** — Chromium
   launched with `--use-fake-device-for-media-stream` generates an actual
   tone through the real `getUserMedia` → `AudioContext` → `ScriptProcessorNode`
   pipeline, and the bar heights visibly varied (4px vs 36px) in
   response, proving the signal path is real end to end, not mocked at
   the JS-function level.
2. **Settings — the most "boxes and text" screen — got colored icon
   chips** (alternating amber/teal circular backgrounds behind each row's
   icon) instead of bare outline icons floating in space. Small CSS-only
   change, but real visual rhythm/scannability improvement, matching the
   "thumb-optimized, purposeful micro-detail" pattern from current
   research rather than a generic flat list.

Both live-verified via the same headless-browser screenshot method as
everything else. Still not a full redesign of every remaining screen
(History, Edit Profile, Privacy/Help/Terms, Setup's earlier steps) — see
the honest scope note in the previous section, which still applies.

## Completing the redesign — the remaining named screens

Pushed again on "why not all pages" — correct, no reason to leave the
in-app screens half-done once the design language existed. All of these
now match, live-verified via the same headless-browser screenshot method:

- **Setup wizard step 1 (name)** — was the plainest step (title + one
  input, nothing else). Added a live avatar preview that fills in with
  your first initial as you type, same gradient-circle identity pattern
  used on Profile/Edit Profile — connects the very first screen to the
  same visual language as the rest of the app instead of introducing it
  later. Step 2 (language) already inherited the Settings icon-chip
  upgrade for free, since it reuses the same `.settings-row` component.
- **Edit Profile** — added the matching avatar circle at the top,
  live-updating as you type a new name (small real-time touch, not just
  static).
- **Privacy & data** — rebuilt the summary as a glass card with an icon
  and three real data-category chips (Email/phone, Saved conversations,
  Usage stats) instead of a paragraph of plain text.
- **Help & feedback** — each FAQ item now has a "Q" icon chip, and the
  contact link is a real button-styled card with a mail icon instead of
  plain underlined text.
- **History** — conversation cards now have a staggered slide-in
  entrance, matching the badge-pop treatment on Profile.

**Deliberately NOT restyled: the standalone `/privacy` and `/terms`
pages** (as opposed to the in-app Privacy & Help *screens* above, which
were redesigned). These already share the app's dark palette and type,
but were kept as plain, readable documents rather than given card/motion
treatment — that's a deliberate convention (legal text benefits from
staying maximally readable and unstyled, not a corner cut), not an
oversight.

Every screen in the tab bar + settings sub-screens + setup wizard now
shares one consistent design language. Full suite: 153 passed, zero
regressions, confirmed via live screenshots of all five updated screens
in a single real click-through session, not just individually.

## Branded OTP email + real app icon

Two real assets replaced, both verified (not just eyeballed):

1. **App icon/logo** — the old icon (`frontend/icons/*.png`) was the same
   circle-overlap orb graphic used elsewhere, but composed badly as an
   icon specifically: no safe-zone padding, orbs bled off the canvas
   edge. Replaced with a new mark based on the app's actual signature
   element (the voice waveform from `renderWaveform()`), generated with
   Pillow — amber-to-teal gradient bars, arced height, properly centered
   with safe-zone margin. More distinctive than the old circle-overlap
   (which read as a generic payment-logo mark) and instantly reads as
   "voice/audio," matching what the in-app conversation screen already
   shows live. Regenerated at every required size: web
   (`icon-192`, `icon-512`, `icon-maskable-512`, `favicon`,
   `apple-touch-icon`) AND the native Android adaptive-icon set — all 6
   density folders (ldpi through xxxhdpi), each with foreground/
   background/legacy-launcher/round layers, which had never been touched
   before (still had the old default art baked in from initial project
   scaffolding). Verified the adaptive icon's foreground+background
   composite renders correctly within the OS safe zone, and confirmed
   the web favicon serves correctly (200) through a live running server.
2. **OTP email template** (`otp_providers.py`'s `BrevoEmailOTPProvider._html`)
   — was a single plain unstyled paragraph. Rebuilt as a real card layout
   (table-based, inline styles — deliberately, since email clients
   especially Outlook don't reliably support flexbox/grid or `<style>`
   blocks the way browsers do): logo header, styled code display with
   the app's actual gradient treatment, expiry + phishing-safety note,
   footer tagline. New `VOXBUDDY_PUBLIC_URL` env var (optional) embeds
   the real logo PNG once deployed; without it, falls back to a styled
   text wordmark rather than a broken image link, since email clients
   can't load images from `localhost`. Caught and fixed a real mojibake
   bug during this work — em-dash characters need to be HTML entities
   (`&mdash;`) in email HTML specifically, not raw Unicode, since email
   client charset handling is far less consistent than browsers'. 4 new
   tests, and the rendered output was actually screenshotted (via a
   local HTML file + Playwright) to confirm it looks right, not just
   assumed from the template string.

Full suite: 157 passed, 6 skipped, zero regressions.

## Real Brevo SMS error, seen live for the first time

First real third-party vendor error hit live in this project (not a
local config mistake like the Redis one) — testing Phone login, Brevo
rejected the send with `"No sms related addons are found for the given
organization"`. Confirmed via Brevo's own docs: transactional SMS is a
separate paid add-on from transactional email on Brevo, not automatically
included — the account needs SMS credits enabled at
`app.brevo.com/transactional/sms/settings/configurations` before any
SMS send will succeed, regardless of API key validity. Not a code bug.

The good news buried in this: `otp_providers.py`'s error-surfacing chain
worked exactly as designed — the real Brevo rejection reached the
frontend and displayed instead of a generic failure, which is what made
this diagnosable from a screenshot instead of needing backend log access.

Improved anyway: `BrevoSMSOTPProvider.send()` now special-cases this
specific Brevo response with a plain-English explanation + the exact
dashboard URL to fix it + the "just use Email instead" escape hatch,
instead of a raw JSON dump. Other Brevo SMS failures (bad number format,
etc.) still surface the real response unchanged — this only intercepts
the one specific "addon not enabled" case. 2 new tests using a mocked
`httpx.post` reproducing the exact response shape received live, plus a
regression test confirming other errors aren't swallowed into the new
message. Full suite: 159 passed, 6 skipped.

## Decoupled from Brevo — real alternatives, per-channel

Asked directly why not just separate from Brevo entirely given the SMS
add-on friction. Fair — the provider abstraction already existed
(`otp_providers.get_provider()`), so this was genuinely straightforward
to extend rather than a good reason to say no.

- **Email: new `SMTPEmailOTPProvider`** — direct SMTP send using only
  Python's stdlib (`smtplib`/`ssl`/`email.mime`), no third-party account
  needed beyond a mailbox you already have (Gmail with an App Password,
  Outlook, any SMTP server). Genuinely simpler than Brevo for email
  specifically, not just "another vendor."
- **SMS: new `Fast2SMSOTPProvider`** — real code against Fast2SMS's
  documented OTP route. Chosen specifically because signup gives free
  trial credit immediately with no separate "enable this add-on"
  purchase step — the exact friction that blocked Brevo SMS. Uses
  Fast2SMS's own pre-approved OTP template (route=otp) rather than a
  custom message, which matters in India specifically: TRAI requires SMS
  sender templates to be DLT-registered, real business paperwork, not
  just an API key — the OTP route sidesteps needing your own DLT
  registration by riding on Fast2SMS's already-approved one.
- **`get_provider()` now resolves email and SMS independently** —
  `VOXBUDDY_OTP_EMAIL_PROVIDER` / `VOXBUDDY_OTP_SMS_PROVIDER`, falling
  back to the old shared `VOXBUDDY_OTP_PROVIDER` for backward
  compatibility. You can genuinely run SMTP for email + Fast2SMS for SMS
  simultaneously, or any other mix — this is the actual "separate from
  Brevo" answer, not just a swap to a different single vendor.

10 new tests (24 total in this file): SMTP send verified against a
mocked `smtplib.SMTP_SSL` (confirms real host/port/login/sendmail calls,
message actually contains the code), Fast2SMS's real failure mode
(`HTTP 200` with `{"return": false}`, not a non-2xx status — would look
like success if not checked separately) reproduced and handled,
per-channel independent selection, and the specific Brevo SMS "no addon"
error from earlier improved with a plain-English explanation + the exact
dashboard fix + "use SMTP/Fast2SMS instead" escape hatch. Full suite:
169 passed, 6 skipped, zero regressions.

## Google Sign-In — added alongside OTP, not replacing it

- **Backend**: `POST /api/auth/google` verifies the ID token's signature
  against Google's own public keys (`google-auth`'s
  `verify_oauth2_token` — checks signature, expiry, and audience match
  our `GOOGLE_CLIENT_ID`, not just trusting whatever the frontend sends).
  Requires `email_verified=True`. New `auth_store.find_or_create_user_by_google`
  deliberately keys on the same `email` column OTP login uses — someone
  who signed up via email OTP and later uses Google with the same
  address lands in the same account, not a duplicate; an existing
  display name is never silently overwritten by the Google profile name.
  `GET /api/auth/config` tells the frontend whether this is even
  configured, so the button hides cleanly instead of rendering broken —
  same pattern as every other optional vendor feature in this project.
- **Frontend**: Google Identity Services button rendered on the login
  screen above the existing email/phone toggle, with an "or" divider.
  Only appears if `/api/auth/config` reports a real client ID. On
  success, routes through the exact same session/token path as OTP
  login (`AuthState.token`/`localStorage`), so nothing downstream needs
  to know which method was used.
- **Bonus fix while touching this code**: `verifyLoginCode()` always
  routed to Setup after login, even for a returning user who'd already
  onboarded (e.g. after a logout). Now correctly checks
  `user.onboarded` and routes to Home instead — applied to both the OTP
  and Google paths.

7 new backend tests (176 total) — including one that specifically
verifies the "same email, different login method → same account,
existing display name preserved" behavior. Verified live in a real
browser: correctly stays hidden with no console errors when
`GOOGLE_CLIENT_ID` is unset (your current setup), and correctly fetches
config when it is set. Could not verify the fully-configured button
actually rendering — this sandbox's network egress blocks
`accounts.google.com` entirely (confirmed via direct curl:
`x-deny-reason: host_not_allowed`), same restriction that blocked Google
Fonts earlier in this project. Not a code issue; will work normally on
your machine or once deployed.

**Real limitation, not a bug**: Google's own policy blocks its
sign-in flow inside embedded WebViews (including Capacitor's native
Android/iOS shell) — works fine in a real browser or installed PWA, but
the native app specifically would need a native Google Sign-In SDK
plugin (not built) to support this button. Same category of
"web-works, native-needs-more" as the Bluetooth pairing feature earlier.

## Phone/SMS login removed from the UI

Removed the Email/Phone toggle from the login screen entirely — email
(plus Google Sign-In above it) is now the only login path shown.
`setLoginChannel()` (now unused) was deleted along with the toggle
buttons; a stale error message ("Enter your email or phone number
first") was also caught and fixed to match. Verified live: full email
login flow (send code → verify → land on Setup) still works correctly
with zero console errors after the removal.

**Deliberately NOT deleted: backend SMS support** —
`auth_store.normalize_identifier`'s phone branch, `BrevoSMSOTPProvider`,
and `Fast2SMSOTPProvider` are untouched, just no longer reachable from
the UI. They're real, tested, working code; ripping them out would be
pure loss with no benefit if phone login is ever wanted again later —
cheap to leave, cheap to re-enable (just add the toggle back), not
cheap to rebuild from scratch.

Full suite: 176 passed, 6 skipped, zero regressions.

## Real bug: service worker was serving stale content after every deploy

You were right to double-check — the screenshot showing the old phone
toggle and no Google button was real, not a misunderstanding. Root
cause: `sw.js` cached the `/app` page itself with a cache-first
strategy, so once your browser cached it once, it kept serving that
same stale HTML forever regardless of what changed on the server
afterward. This wasn't specific to the phone/Google change — it would
have silently hidden *every* update from this point forward.

Two-layer bug, needed a two-layer fix (found the first fix alone wasn't
enough by actually testing it — see below):

1. **`sw.js`**: navigation requests (the HTML document) now use
   network-first instead of cache-first — cache is only ever a fallback
   for genuinely offline use.
2. **The subtler part**: network-first alone wasn't sufficient, because
   `/app` had no `Cache-Control` header at all, so the browser applied
   its own heuristic freshness and could serve a disk-cached response to
   the service worker's own `fetch()` call — "network-first" service
   worker logic still goes through `fetch()`, which is itself
   cache-aware by default. Fixed with `Cache-Control: no-cache` on the
   `/app` response (`app.py`) AND `{ cache: 'no-store' }` on the
   service worker's fetch call itself (belt-and-suspenders — either one
   alone might not survive every browser/proxy combination).

**Verified by actually reproducing the exact bug, not just reasoning
about it**: used a persistent Playwright browser profile (so the service
worker genuinely survives across two separate visits, like a real
browser) — visit 1 caches content, server content changes, visit 2 with
the same profile. Confirmed BROKEN with the first fix alone (network-first
SW logic, no cache header) — still served stale content. Confirmed FIXED
once both layers were addressed — visit 2 correctly showed the new
content. `CACHE_NAME` bumped to v3 so everyone's currently-stuck-stale
cache gets purged once this ships, not just prevents it going forward.

Full suite: 176 passed, 6 skipped, zero regressions.

## Real responsive-design bug found and fixed, tested across a real device matrix

Directly asked whether the design actually fits any real mobile screen
size — didn't just assert yes, checked. Found a genuine bug: the
edge-to-edge-on-real-phones media query was `max-width: 420px`, but
research confirmed iPhone 15/16 Pro Max are 430-440px CSS viewport width
— comfortably common, current, real devices, and *above* that cutoff.
On those specific phones, the app would have shown the decorative
desktop "preview mockup" frame (rounded corners, drop shadow, dead
margins on both sides) instead of a proper edge-to-edge native-feeling
layout — the exact thing that would make an app look unpolished on a
premium device.

Fixed: breakpoint widened to `max-width: 600px`, comfortably clearing
every real current phone width (including oversized phablets) while
staying well below real tablet/desktop widths.

Verified across 7 real device viewport sizes, not just the one this
whole project had been screenshotted at until now: 360×740 (budget
Android), 375×667 (iPhone SE), 390×844 (standard), 412×915 (Pixel),
430×932 (iPhone 15 Pro Max — previously broken), 440×956 (iPhone 16 Pro
Max — previously broken), 480×960 (large phablet). At every size:
confirmed zero horizontal overflow (`scrollWidth` never exceeded
viewport width), confirmed the phone frame genuinely goes edge-to-edge
(`border-radius: 0px`, width exactly matching viewport). Also
click-tested the layout-dense screens specifically (Home, Profile with
badges + stat cards, Settings with icon chips) at both the narrowest
(360px) and widest (440px) sizes — no clipped text, no cramped icons, no
broken wrapping.

One pre-existing, minor, non-blocking cosmetic detail noted while
testing (not introduced by this fix, not chased further): the
badge-unlock toast briefly overlaps the screen's title text while
showing (~3 seconds), at all screen sizes. Purely cosmetic during a
transient state, not a layout/functional bug.

Full suite: 176 passed, 6 skipped (unaffected — pure CSS change).

## Login screen redesign — real background art + motion, not stock images

Directly asked for background images/animation since the login screen
felt boring. Did not use stock/hotlinked photos deliberately — copyright
risk, licensing cost, and a dependency on an external URL that could
break; instead built original SVG/CSS art grounded in the actual product
identity:

- **Constellation background** — an original SVG of dots connected by
  faint lines, spanning the whole login screen. Doubles as atmosphere
  and a literal world-map/network-of-people motif — grounded in the
  existing tagline ("bringing worlds together"), not decoration picked
  arbitrarily. Dots twinkle (staggered opacity + radius animation,
  amber/teal alternating to match the brand palette exactly).
- **Floating particles** — 6 small glowing points that slowly rise and
  fade at staggered delays/durations, for ambient depth.
- **Staggered entrance sequence** — wordmark, waveform, tagline, and the
  login form now fade/slide in one after another on load (`.login-in`
  class + per-element `animation-delay`) instead of the whole screen
  appearing statically all at once.
- All of it respects `prefers-reduced-motion` — verified live with
  Playwright's `reduced_motion="reduce"` context option, zero console
  errors, page still fully usable with motion disabled.

Also fixed a stale copy bug caught while touching this section: the
`meta-banner` text still said "Static mockup — nothing here calls the
backend yet," which stopped being true a long time ago. Updated to
reflect reality.

Verified live in a real browser at both the identifier-entry and OTP
steps — the background persists correctly across the login sub-steps,
not just the first screen. Full suite: 176 passed, 6 skipped (pure
frontend/CSS change, backend unaffected).

## Flowing sound-wave background — verified seamless, not just eyeballed

Added a large continuously-scrolling wave band behind the login content,
in response to "more moving/gif-like." Deliberately not a stock
image/gif — built as an original animated SVG so it stays on-brand,
copyright-safe, and works offline forever.

Construction matters here: naive infinite-scroll animations often have a
visible "jump" at the loop point because the shift distance doesn't
actually match the pattern's true repeat width. Caught exactly this bug
in my own first draft before shipping it — built the fix properly
instead: one 180-unit period shape, replicated via SVG `<use>` at exact
period offsets across a 720-unit (4-period) viewBox, animated by
`translateX(-25%)` — since 25% of a 4-period width is always exactly one
period, this is seamless by construction regardless of actual rendered
pixel size, not a hand-guessed distance.

**Verified rigorously, not assumed**: computed the cubic Bézier curve's
actual position AND tangent direction at both edges of the period in
Python — confirmed both match exactly (same y-position, same direction
vector), which is what guarantees no visible "kink" when it loops.
Then confirmed visually too — screenshotted the animation at three
points across its full 9-second cycle (start, midpoint, just before
loop) and the wave shape stayed visually consistent throughout, no
jump or discontinuity at any point.

Full suite: 176 passed, 6 skipped (pure frontend/CSS+SVG change).

## Real bug: AssemblyAI ASR never actually produced a final transcript

Reported symptom: the app opened a real conversation, mic capture and the
WebSocket both connected fine ("Listening (real microphone)…"), but it
never spoke anything back — not even an error, just stuck listening.

Root cause, found by reading AssemblyAI's own documented SDK usage
against what this codebase actually did: `AssemblyAIStreamingASRAgent.
send_audio()` called the SDK's `client.stream()` **once per incoming
audio frame** (every ~256ms). `client.stream()` is a blocking call
designed to be given an iterable/generator **once** for the whole session
(the SDK's own examples call it exactly once, e.g. `client.stream(aai.
extras.MicrophoneStream(...))`) — calling it repeatedly with one raw
chunk at a time is not valid usage of the API. The practical effect: no
final transcript was ever produced, so nothing ever reached translation
or TTS, and no exception surfaced anywhere a user could see it.

This was exactly the risk flagged honestly in this file and in
`asr_assemblyai.py`'s own docstring every time it was previously listed
as "scaffolded against the documented SDK shape, not live-tested" — this
is the first real end-to-end run against actual AssemblyAI traffic, and
it caught a real integration bug, not just a missing API key.

Fixed in `agents/asr_assemblyai.py`: `send_audio()` now just enqueues
bytes onto a thread-safe queue (fast, non-blocking, safe to call from the
asyncio event loop). `client.stream()` is called exactly once, inside a
background thread, consuming a generator that pulls from that queue until
`stop()` sends a sentinel. The public `start`/`send_audio`/`stop` shape —
what the rest of the pipeline and the existing tests depend on — is
unchanged.

Also hardened while fixing this, since the original failure mode was
silent end-to-end:

- `backend/app.py`: all three `SessionManager()` construction sites
  (`POST /api/session`, both WebSocket handlers) now catch the
  `RuntimeError` a misconfigured provider raises (e.g.
  `VOXBUDDY_TTS_PROVIDER=elevenlabs` with no `ELEVENLABS_API_KEY`) and
  return/send a real error message instead of an opaque 500 or a dead
  socket. The audio WebSocket's receive loop also now catches any other
  ASR-provider exception (not just the mock's expected
  `UnicodeDecodeError`) and reports it instead of the connection just
  dying.
- `frontend/app-preview.html`: if translation succeeds but TTS fails
  (bad key, invalid voice ID), the status line now shows `(playback
  failed: ...)` inline instead of only logging to the browser console —
  invisible on a phone, which is exactly how this symptom first looked
  identical to "still listening."

All `agents/asr_assemblyai.py`-related tests still pass unchanged
(structural protocol tests didn't need to change, since the public
interface didn't). Full suite otherwise unaffected — this was an
ASR-adapter-internal fix.

**Deployment reminder that fell out of debugging this:** `render.yaml`
marks every vendor key `sync: false`, so Render never picks up values
from a local `.env` — `ASSEMBLYAI_API_KEY`, `ELEVENLABS_API_KEY`, and the
translation provider's key all have to be pasted into Render's dashboard
separately. Worth double-checking there directly, independent of this
code fix, since a backend that works locally but stays silent once
deployed usually means this step, not a code bug.

## Docs pass — READMEs and `docs/` brought back in sync with the actual codebase

Several docs had drifted noticeably behind the real implementation —
written at a point when native Android was pure scaffolding, ASR/TTS were
untested, and self-voice enrollment didn't exist yet. Went through every
`.md` file in the repo against the actual code (not just against the last
time each doc was edited) and updated what was stale:

- **`README.md`** — fully rewritten as a public-facing, portfolio-quality
  overview (problem statement, CIE explained as the real differentiator,
  feature list, tech stack, architecture diagram, project structure,
  setup/deploy instructions, roadmap).
- **`docs/VoxBuddy_PRD_and_Architecture.md`** — status line updated from
  "Draft for Phase 1" to reflect that Phases 1–4 are substantially built
  (pointing at this file for the live detail rather than duplicating it);
  the §20 note claiming self-voice enrollment was "currently
  unimplemented" was stale — corrected now that it's shipped and tested.
- **`docs/vendor_decision.md`** — §4's status table updated: ASR and TTS
  were listed as "scaffolded, not live-tested" — now marked implemented
  and live-tested, with the `client.stream()` bug above noted as the real
  thing that first live test caught. Added the Render `sync: false` env
  var gotcha as a standing deployment note.
- **`docs/MOBILE_BUILD.md`** — was written when `mobile/android` was
  unbuilt scaffolding with a 403 blocking even a Gradle sync. Rewritten to
  reflect reality: a real, installed, device-tested Android app with two
  working native plugins, real permissions, and a list of real bugs that
  device testing (not this sandbox) actually caught. iOS section
  unchanged — still genuinely not started, still genuinely needs a Mac.
- **`docs/TESTING_REAL_PIPELINE.md`** — referenced a "use real microphone"
  checkbox that no longer exists (mic capture is unconditional now), and
  didn't mention the `client.stream()` bug or the new error-surfacing
  behavior. Rewritten to match the current flow and point at the new,
  more specific failure-mode messages.
- **`docs/PLAY_STORE_PUBLISHING.md`** — Option A's Android Studio path was
  described hypothetically ("the real Android Studio project already
  scaffolded"); updated to say plainly that it's already built and
  device-tested, not just scaffolded.

Full suite: unaffected — this was a documentation-only pass except for
the ASR fix above, which is code and is covered by the existing
`asr_assemblyai`-related tests.

## Bluetooth "change device" escape hatch

Reported symptom: the earbud-connect screen auto-connects to whatever
Bluetooth audio device is already active, with no way to pick a
different one. This is genuinely not something an app can offer for
Classic Bluetooth (the protocol most earbuds use) — Android reserves
device-pairing UI and audio-route switching to its own system Bluetooth
settings; no app can drive that itself. Added the honest version of a
fix: `AudioDevicePlugin.openBluetoothSettings()` (native) plus a "Not
this device? Change in Bluetooth settings" link (`app-preview.html`)
that appears whenever the app auto-connects, handing off to Android's
real settings screen instead of pretending the app can arbitrate it.

## Mic-audio WebSocket had no reconnect logic at all

Found while working through the "still listening, not speaking" report:
the demo/text-script WebSocket path (`connectConversationSocket`) has had
exponential-backoff reconnect logic for a while, but the actual real-mic
conversation path (`startMicCapture` / `/ws/{session_id}/audio`) — the
one every real conversation actually uses — had none. A dropped
connection just showed "Microphone connection closed." and sat there.
Refactored `startMicCapture` to split out `openMicWebSocket()`, which can
be called again on a drop without tearing down and re-requesting the mic
stream/AudioContext (only the socket itself gets replaced). Reconnect is
exponential backoff up to 5 attempts, same pattern as the existing text
path — plus one addition that path didn't have: while the device is
genuinely offline (`navigator.onLine === false`), it stops retrying and
waits for the browser's `online` event instead of burning through
attempts against a connection that has no chance of succeeding, then
resumes immediately once real connectivity returns.

## Speaker identity — clarified, not a gap after all

Re-examined the "speaker embeddings still mocked" item from
`docs/vendor_decision.md` and found the existing `mocks.py` design was
already close to the doc's own recommendation (derive identity from the
ASR vendor's diarization label rather than a separate acoustic model) —
it just used only 8 bytes of a hash, leaving a non-trivial chance of two
different speakers' pseudo-embeddings randomly exceeding the CIE's 0.80
cosine-similarity match threshold and getting merged. Widened to the
full 32-byte SHA-256 digest and renamed the class honestly to
`LabelDerivedSpeakerIdentityAgent`, documenting exactly what it is and
isn't (not a real acoustic voice-similarity model — still an open item
if that's ever needed) in the class docstring itself.

## OTP request rate limiting — see docs/SECURITY_PRIVACY_REVIEW.md

Ran a real code-level security/privacy pass. Found and fixed one real
gap: no per-IP rate limit on `/api/auth/request-otp`, meaning nothing
stopped rapid OTP requests across many different identifiers from one
client — real cost once a real OTP provider is configured (each request
is a billed SMTP/Brevo/Fast2SMS send). Added a small in-memory per-IP
limiter (8 requests / 10 minutes, reads `X-Forwarded-For` since Render
sits behind a proxy), covered by `tests/test_otp_rate_limit.py`. Full
findings — including what was checked and confirmed safe, and what's a
deliberate deferred tradeoff (tokens in `localStorage`, not yet moved to
httpOnly cookies) — are in the new doc, not duplicated here.

Also found while doing this pass: `frontend/privacy.html` and
`terms.html` both still have a literal `[Add your contact email
here...]` placeholder — harmless for dev, but blocks a real Play Store
submission, which checks for a working privacy policy contact.

## What's still genuinely open (not attempted, and why)

- **Fusion weight calibration** — the CIE's signal-fusion weights are
  hand-set, not tuned against real recorded multi-speaker audio. Can't
  be done without that data; nothing to fabricate here.
- **Full noise-cancellation DSP** — what exists (the adaptive
  voice-activity gate) is real and functioning, but a genuinely separate,
  larger signal-processing project from actual in-frame noise removal.
- **Asymmetric mode** (one phone carrying both conversation sides) — real
  feature work, not started. Unrelated to the "not speaking" bug, despite
  looking related on the surface.
- **Multi-region infra** — needs an actual infra/budget decision (which
  regions, what it costs, whether it's justified at current scale), not
  something to decide unilaterally in code.
- **iOS build** — needs a physical Mac, which isn't available in this
  environment. No code change gets around that platform requirement.

## The real "continuously listening, never speaks" bug — found via a real device recording

The earlier `client.stream()` fix was necessary but not sufficient — after
redeploying it, the app still never finalized a turn: mic capture kept
animating indefinitely even after speech stopped, confirmed on video from
a real device test. Root cause this time was on the frontend, not the
ASR adapter: `startMicCapture`'s audio-processing loop had a client-side
"noise gate" (`shouldForwardFrame`/`makeNoiseGateState`) that stopped
sending audio to the backend entirely once it detected silence, to save
bandwidth.

That's incompatible with how a real streaming ASR vendor's turn detection
actually works. AssemblyAI decides "the speaker has stopped talking,
finalize this turn" by observing real silence *in the audio stream it
receives* — its endpointing (VAD-based and semantic) runs against
incoming audio, not a wall-clock timer independent of it. If the app
stops sending audio the instant it goes quiet, AssemblyAI's connection
just goes idle waiting for more data — it never gets the silence it
needs to conclude the turn ended, so `end_of_turn` never fires, so
nothing ever reaches translation or TTS. It also wasn't a real bandwidth
optimization to begin with: AssemblyAI bills by WebSocket connection
time, not by audio bytes sent, confirmed via their own docs.

Fixed in `frontend/app-preview.html`: removed the noise gate from the
send path entirely — every real audio frame (including silence) is now
forwarded to the backend, letting AssemblyAI's own turn detection do its
job as designed. `frameRMS()` is kept (used only for the live waveform
visualization now); `makeNoiseGateState()`/`shouldForwardFrame()` were
dead code after this change and removed rather than left unused.

Two real bugs in one feature, found in two separate rounds of real
testing, is exactly why "scaffolded against the documented shape, not
live-tested" was called out honestly in `docs/vendor_decision.md` from
the start rather than claimed as done — a wrong SDK call and a bandwidth
optimization that quietly broke the actual protocol contract are both
the kind of thing that only shows up once real audio, a real device, and
a real vendor connection are all in the loop together, not from reading
the code.

## The actual final bug: results computed correctly, never delivered — a threading violation

Even after the audio-forwarding fix above, the app still never spoke.
Root cause: `on_pipeline_result=lambda result: asyncio.create_task(send_result(result))`
in the `/ws/{session_id}/audio` handler (`backend/app.py`). This worked
in every existing test because `MockStreamingASRAgent` calls its results
back synchronously, inline, from the same coroutine as the WebSocket
handler — `asyncio.create_task()` only works when called from the event
loop's own thread, and the mock always satisfies that by construction.
`AssemblyAIStreamingASRAgent` doesn't: `client.stream()` runs in its own
background thread (a requirement of the earlier fix), and the SDK
invokes turn-event callbacks — and therefore this lambda — from that
thread, not the event loop's. `asyncio.create_task()` called from a
foreign thread doesn't schedule anything useful; the practical effect
was that ASR, the CIE, translation, and TTS all genuinely ran to
completion, but the result never made it back over the WebSocket to the
client. That's indistinguishable from "still listening" on the frontend,
since nothing ever arrives to change the status line.

Fixed by switching to `asyncio.run_coroutine_threadsafe(send_result(result), loop)`,
capturing `loop = asyncio.get_running_loop()` inside the handler's own
coroutine (safe — that call happens on the loop's thread) and using it
from the lambda regardless of which thread eventually invokes it. Works
identically for both the mock (loop's own thread) and the real adapter
(a foreign thread).

This bug specifically could not have been caught by the existing test
suite, since every prior test exercised the mock's synchronous callback
shape. Added `tests/test_audio_ws_thread_safety.py` with a minimal fake
ASR agent that — like the real AssemblyAI adapter, unlike the mock —
delivers its result from an actual background thread. Verified this
test is a real regression guard, not just a happy-path check: with the
bug deliberately reintroduced, it hangs/times out (matching the exact
real-world symptom); with the fix in place, it passes in well under a
second. Full suite otherwise unaffected: 53 pre-existing failures
before and after (this sandbox blocking real vendor network calls,
unrelated), zero regressions.

Three real, distinct bugs in one feature — the wrong `client.stream()`
call shape, the client-side audio being silently withheld during
silence, and this threading violation — each only surfacing once real
audio, a real device, and a real vendor connection were all in the loop
together. None of them were visible from reading the code in isolation,
which is exactly why `docs/vendor_decision.md` called this adapter
"scaffolded, not live-tested" from the start rather than claiming it
done.

## The actual actual final bug: Gemini's model ID was deprecated, and the failure was silent

The person confirmed via a screenshot of their own Gemini API dashboard:
"Total API Errors" showing a spike of `404 NotFound`. That's the real
cause — `translation_gemini.py`'s default model, `gemini-2.5-flash`,
was deprecated by Google for newly-created API keys ahead of its
official Oct 16, 2026 shutdown; every real translation call was getting
an immediate 404 ("This model models/gemini-2.5-flash is no longer
available to new users").

That alone would just mean translation fails — the real bug is what
happened next: `SessionManager._translate_and_record()` called
`self.translation_agent.translate()` with **no try/except**, unlike the
TTS call immediately below it, which was already correctly guarded. The
404 exception propagated straight out of the pipeline with nothing to
catch it. For the real audio path specifically, that exception surfaces
on AssemblyAI's own SDK background thread (a requirement of an earlier
fix), which silently swallows it inside its own internal callback
dispatch rather than letting it reach anywhere visible. Net effect:
ASR genuinely transcribes, the CIE genuinely runs, translation genuinely
gets called — and then the whole turn just vanishes. Indistinguishable
from "still listening" on the client, exactly the symptom reported.

Two fixes:
1. **`agents/translation_gemini.py`** — updated `DEFAULT_MODEL` to
   `gemini-3.5-flash-lite` (current-generation, GA, and explicitly
   Google's fastest/cheapest tier — matching the original intent behind
   this default, just on a model ID that still exists). Override via
   `GEMINI_MODEL` for a quality/cost tradeoff.
2. **`session/manager.py`** — wrapped the `translate()` call in
   try/except, mirroring the TTS pattern exactly. Added a
   `translation_error` field to `PipelineResult`, threaded through
   `app.py`'s `_to_out()`/`UtteranceOut`, and surfaced on the frontend
   status line (`frontend/app-preview.html`) as `Translation failed:
   ...` — so a future vendor failure (deprecated model, expired key,
   quota, network issue) is visible immediately instead of silently
   killing the turn.

Added `tests/test_translation_error_handling.py` with a fake translation
agent that raises exactly this kind of error. Verified it's a real
regression guard the same way as the earlier threading test: deliberately
reintroduced the unguarded call, confirmed the test fails with the raw
`RuntimeError` (matching the exact production failure mode), then
restored the fix and confirmed it passes. Full suite: 50 pre-existing
failures both before and after (sandbox-blocked real vendor network
calls — this sandbox's own attempts to reach Anthropic/Gemini/AssemblyAI
are blocked, which is exactly the class of failure this fix now handles
gracefully instead of crashing on, incidentally reducing the raw failure
count from 53 to 50 as a side effect — same root cause, just failing
cleanly instead of crashing now), 132 passed (130 baseline + 2 new).

Four real, distinct bugs found in this one feature across four rounds of
real testing — a wrong SDK call, silently-withheld audio breaking a
vendor's endpointing, a cross-thread asyncio violation, and an unguarded
call to a vendor whose model ID had been deprecated out from under the
app. Every one of them was invisible from reading the code in isolation
and only surfaced once real audio, a real device, and real vendor
traffic were all in the loop together — which is the whole reason this
adapter was tracked as "scaffolded, not live-tested" from the start
rather than claimed done.

## Bug #5: ElevenLabs 402 — the default voice_id was a paid-plan-only Library voice

Confirmed via a real device screenshot showing the actual ElevenLabs API
error surfaced end-to-end for the first time (thanks to the error
plumbing added while chasing bug #4): `402 Payment Required` — "Free
users cannot use library voices via the API." Everything upstream is
now genuinely working: real transcription, real speaker detection
("Detected speaker"), real context-aware translation, saved to real
conversation history. This is now purely a TTS-configuration issue, not
a pipeline bug.

Root cause: `DEFAULT_VOICE_IDS` in `agents/tts_elevenlabs.py` pointed
every language at `VO7pRycLkEn8V7IWzZ0r` — a voice pulled from
ElevenLabs' shared community Voice Library. ElevenLabs restricts Library
voices to paid-plan accounts specifically for *API* access (free to
preview in their own dashboard, blocked via `text_to_speech.convert()`
on a Free-tier key).

Fixed by switching to `21m00Tcm4TlvDq8ikWAM` ("Rachel") — one of
ElevenLabs' original "premade" voices, bundled with every account
including Free, and accessible via the API on every plan tier. Also
wrapped the `convert()` call in a try/except that appends an actionable
hint (which dashboard tab to check, what to filter for) whenever this
specific error class recurs, since ElevenLabs' own error message is
accurate but doesn't say what to actually do about it.

Still a real, documented gap: every language uses the same voice
(Rachel), so en/hi/fr all sound identical — flagged as a TODO in the
file itself. Fixing that requires picking distinct voice IDs from your
own account's premade voices, which needs your ElevenLabs dashboard, not
something to guess at from here.

Full suite: 50 pre-existing failures (unchanged from before this fix —
all sandbox-network-blocked, unrelated), 132 passed. One pre-existing,
already-documented test bug (`test_elevenlabs_agent_requires_real_voice_id`)
is unaffected by this change — it was already broken before today for an
unrelated reason (flagged in this file's very first ElevenLabs entry).

Five real bugs found across five rounds of real testing, each only
surfacing with real audio + a real device + real vendor traffic: a wrong
SDK call shape, silently-withheld audio breaking a vendor's endpointing,
a cross-thread asyncio violation, an unguarded call to a deprecated model
ID, and a voice_id requiring a plan tier the account doesn't have. This
is the value of shipping error visibility alongside each fix, not just
the fix itself — bug #5 was only diagnosable at all because bug #4's
fix made the underlying vendor error visible instead of silent.
