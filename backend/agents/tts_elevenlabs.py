"""
ElevenLabs streaming text-to-speech adapter.

STATUS: scaffolded against the documented elevenlabs-python SDK streaming
shape (per docs/vendor_decision.md §3), NOT live-tested — this build
environment has no network access to ElevenLabs and no API key.

Implements the synchronous TTSAgent protocol from agents/base.py using the
SDK's simple `convert` + streaming iterator, which is sufficient to replace
MockTTSAgent directly without any interface changes (unlike the ASR case —
TTS here is naturally request/response: text in, audio stream out, which is
exactly what TTSAgent.synthesize already expects).

For the lowest possible time-to-first-audio in the real hot path (PRD §6
latency budget), Phase 2 should move this to the WebSocket
`/v1/text-to-speech/{voice_id}/stream-input` endpoint so partial text (as
translation tokens arrive) can start audio generation before the full
sentence is translated — this adapter uses the simpler streaming HTTP
method as a correct, lower-risk starting point.
"""

from __future__ import annotations

import os

from .base import TTSResult

# A small default voice map per target language.
#
# Real bug caught in production: this used to point every language at
# "VO7pRycLkEn8V7IWzZ0r" — a *Voice Library* voice (one pulled from
# ElevenLabs' shared community library, e.g. via their Voice Library
# browser). ElevenLabs restricts Library voices to paid-plan accounts
# specifically for API access — even though they're free to preview in
# the dashboard — and returns 402 Payment Required ("Free users cannot
# use library voices via the API") for every synthesis call. Because
# translation succeeds before this call, the failure was visible (thanks
# to the translation_error/tts_error surfacing added in session/manager.py
# and app.py) but still meant total silence: right diagnosis, wrong voice.
#
# Fixed by switching to "premade" voices — the original built-in voices
# ElevenLabs bundles with every account (including Free), NOT pulled from
# the shared Library, and accessible via the API on every plan tier. Same
# voice for every language here isn't a bug on its own (ElevenLabs' models
# handle multiple languages per voice) — see the TODO below for varying it
# per language once you've picked voices from your own account.
#
# TODO: these are still the same single voice for every language. Pick
# distinct voices per language from your own ElevenLabs account (Voice
# Library tab -> filter "My Voices"/premade only, NOT the shared
# community library) so en/hi/fr don't all sound identical.
DEFAULT_VOICE_IDS: dict[str, str] = {
    "en": "21m00Tcm4TlvDq8ikWAM",  # "Rachel" — premade, free-tier-safe
    "hi": "21m00Tcm4TlvDq8ikWAM",
    "fr": "21m00Tcm4TlvDq8ikWAM",
}

DEFAULT_MODEL = "eleven_flash_v2_5"  # lowest-latency model per vendor research


class ElevenLabsTTSAgent:
    def __init__(self, api_key: str | None = None,
                 voice_ids: dict[str, str] | None = None,
                 model_id: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self.voice_ids = voice_ids or DEFAULT_VOICE_IDS
        self.model_id = model_id
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(
                    "ELEVENLABS_API_KEY is not set. Set it in the environment "
                    "or pass api_key= explicitly."
                )
            from elevenlabs.client import ElevenLabs  # lazy import
            self._client = ElevenLabs(api_key=self.api_key)
        return self._client

    def synthesize(self, text: str, target_lang: str) -> TTSResult:
        client = self._get_client()
        voice_id = self.voice_ids.get(target_lang)
        if not voice_id or voice_id.startswith("REPLACE_WITH"):
            raise RuntimeError(
                f"No real ElevenLabs voice_id configured for target_lang="
                f"'{target_lang}'. Set one via voice_ids= at construction "
                f"time (see DEFAULT_VOICE_IDS placeholders in this file)."
            )

        try:
            audio_chunks = client.text_to_speech.convert(
                voice_id=voice_id,
                model_id=self.model_id,
                text=text,
                output_format="mp3_44100_128",
            )
            audio_bytes = b"".join(audio_chunks)
        except Exception as exc:  # noqa: BLE001 - vendor SDK error types vary
            # ElevenLabs' own error message here ("Free users cannot use
            # library voices via the API") is accurate but doesn't say
            # what to actually do about it — this is exactly the error a
            # Library-sourced voice_id produces on a Free-tier account,
            # which is what DEFAULT_VOICE_IDS above used to be. Re-raising
            # with an actionable hint appended, rather than a bare pass-
            # through, since this is the single most likely
            # misconfiguration anyone deploying this adapter will hit.
            msg = str(exc)
            if "library voices" in msg.lower() or "payment_required" in msg.lower():
                msg += (
                    " — this voice_id is from ElevenLabs' shared Voice "
                    "Library, which requires a paid plan for API access "
                    "even though it's free to preview in their dashboard. "
                    "Fix: use a 'premade' voice from your own account "
                    "instead (ElevenLabs dashboard -> Voices -> filter to "
                    "your own/premade voices, not the community Library)."
                )
            raise RuntimeError(msg) from exc

        # The convert() call doesn't return duration directly; estimating
        # from mp3 byte size at the fixed bitrate above is rough but fine
        # for latency-budget bookkeeping (PRD §6). Replace with a real
        # duration probe (e.g. mutagen) if exact timing is needed downstream.
        estimated_duration_ms = (len(audio_bytes) * 8) / 128 * 1000 / 1000

        return TTSResult(audio_bytes=audio_bytes, duration_ms=estimated_duration_ms)
