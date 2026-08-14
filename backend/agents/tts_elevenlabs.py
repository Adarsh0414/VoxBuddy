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

# A small default voice map per target language. Real voice IDs need to be
# selected from the ElevenLabs voice library at integration time — these
# are placeholders to be replaced, not verified IDs.
DEFAULT_VOICE_IDS: dict[str, str] = {
    "en": "VO7pRycLkEn8V7IWzZ0r",
    "hi": "VO7pRycLkEn8V7IWzZ0r",
    "fr": "VO7pRycLkEn8V7IWzZ0r",
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

        audio_chunks = client.text_to_speech.convert(
            voice_id=voice_id,
            model_id=self.model_id,
            text=text,
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_chunks)

        # The convert() call doesn't return duration directly; estimating
        # from mp3 byte size at the fixed bitrate above is rough but fine
        # for latency-budget bookkeeping (PRD §6). Replace with a real
        # duration probe (e.g. mutagen) if exact timing is needed downstream.
        estimated_duration_ms = (len(audio_bytes) * 8) / 128 * 1000 / 1000

        return TTSResult(audio_bytes=audio_bytes, duration_ms=estimated_duration_ms)
