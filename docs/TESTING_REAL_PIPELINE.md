# Testing the real listen → translate → speak pipeline

This is the exact checklist for turning the demo into the real thing on
your own machine. It can't be done inside the build sandbox — that
environment has no microphone, no browser GUI, and no vendor API keys.
Everything below only needs your machine (which has a mic, a browser, and
can reach the internet).

## 1. Get three API keys

| Piece | Vendor | Where to get it | Cost |
|---|---|---|---|
| Listening (speech-to-text) | AssemblyAI | assemblyai.com → dashboard → API key | Free tier available |
| Translation | Anthropic | console.anthropic.com → API keys | Pay-as-you-go |
| Speaking | ElevenLabs | elevenlabs.io → profile → API key | Free tier available |

## 2. Get real ElevenLabs voice IDs (a key alone isn't enough)

`agents/tts_elevenlabs.py` ships with placeholder voice IDs. In your
ElevenLabs dashboard, open **Voice Library**, pick a voice, and copy its
Voice ID (looks like `21m00Tcm4TlvDq8ikWAM`). Replace the values in
`DEFAULT_VOICE_IDS` at the top of that file for at least `"en"`.

## 3. Fill in `.env`

```
cd backend
cp .env.example .env
# then edit .env and paste in your three keys + real voice ID
```

## 4. Run it for real

```
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://localhost:8000/app` in a real browser (Chrome/Edge — mic
capture needs a secure context; `localhost` counts as one).

## 5. Test the actual loop

1. Log in (OTP prints to the terminal unless you also set up Brevo).
2. On Home, check **"Use real microphone instead of demo script"**.
3. Tap **Start Conversation** and allow the mic permission prompt.
4. Speak a sentence.
5. Watch the status line — it should show the translated text, then you
   should **hear it spoken back**.

## About "speaking in earbuds" specifically

No special earbud code is needed for this part. The browser plays audio
through whatever your phone/computer's **current default audio output**
is — if your Bluetooth earbuds are already connected at the OS level
(same as any other app), the translated speech comes out of them
automatically. The "Connect earbuds" screen in Setup is a UI flow, not a
requirement for audio routing.

The one thing genuinely *not* possible here is a native "scan and pair"
experience initiated by the app itself — a web app can't drive OS
Bluetooth pairing. That needs the native Capacitor build
(`mobile/`, see `docs/MOBILE_BUILD.md`), not just real API keys.

## If something doesn't work

- **No transcription happens**: check the browser console and the
  `uvicorn` terminal for errors; confirm `VOXBUDDY_ASR_PROVIDER=assemblyai`
  is actually set (a typo silently falls back to `mock`... actually it
  raises `ValueError` — check the terminal).
- **Translation works but no audio plays**: check `tts_error` in the
  browser's network/WS inspector — most likely a bad or placeholder voice
  ID.
- **Nothing happens at all**: open browser dev tools → Console, and paste
  me the first real error. I can't see your screen, so an exact error
  message is the fastest way for me to actually fix it versus guessing.
