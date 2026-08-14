"""
AssemblyAI streaming ASR + inline diarization adapter.

STATUS: scaffolded against the real assemblyai-python-sdk v3 streaming
shape (per docs/vendor_decision.md §1), NOT live-tested — this build
environment has no network access to AssemblyAI and no API key. Treat this
as a correct starting point for Phase 2, not a finished integration.

This implements the StreamingASRAgent protocol from agents/base.py — the
same interface agents/mock_streaming_asr.py implements, which is what lets
the whole streaming pipeline (session/streaming_manager.py) be built and
tested without live AssemblyAI access. Swapping the mock for this adapter
at integration time should require no changes anywhere downstream.
"""

from __future__ import annotations

import os
from typing import Callable

from .base import ASRResult, StreamingASRResult


class AssemblyAIStreamingASRAgent:
    """
    Real-time ASR + diarization over AssemblyAI's v3 streaming WebSocket.

    Usage (matches the StreamingASRAgent protocol exactly):

        agent = AssemblyAIStreamingASRAgent()
        agent.start(on_result=my_handler, sample_rate=16000)
        agent.send_audio(pcm_bytes)   # called repeatedly as audio arrives
        ...
        agent.stop()

    `on_result` is called with a StreamingASRResult for every turn event
    (partial and final) — session/streaming_manager.py only acts on final
    (`is_final=True`) results, matching the utterance-level granularity the
    rest of the pipeline (Translation, TTS) already expects.
    """

    def __init__(self, api_key: str | None = None, speech_model: str = "universal-3-5-pro"):
        self.api_key = api_key or os.environ.get("ASSEMBLYAI_API_KEY")
        self.speech_model = speech_model
        self._client = None
        self._streaming_params_cls = None

    def _build_client(self, on_result: Callable[[StreamingASRResult], None]):
        if not self.api_key:
            raise RuntimeError(
                "ASSEMBLYAI_API_KEY is not set. Set it in the environment "
                "or pass api_key= explicitly."
            )
        # Imported lazily so the mocked PoC path never needs this SDK
        # installed.
        from assemblyai.streaming.v3 import (
            StreamingClient,
            StreamingClientOptions,
            StreamingParameters,
            StreamingEvents,
            TurnEvent,
            StreamingError,
        )

        client = StreamingClient(StreamingClientOptions(api_key=self.api_key))

        def _on_turn(_client, event: TurnEvent):
            if not event.transcript:
                return
            result = StreamingASRResult(
                text=event.transcript,
                is_final=bool(event.end_of_turn),
                confidence=getattr(event, "confidence", 0.9),
                # NOTE: speaker label extraction depends on the exact field
                # name in the SDK version pinned at integration time —
                # verify against current docs, this is the one part of this
                # adapter most likely to have drifted by the time it's wired
                # up for real.
                speaker_label=getattr(event, "speaker", None),
                language=getattr(event, "language", None),
            )
            on_result(result)

        def _on_error(_client, error: StreamingError):
            raise RuntimeError(f"AssemblyAI streaming error: {error}")

        client.on(StreamingEvents.Turn, _on_turn)
        client.on(StreamingEvents.Error, _on_error)
        self._streaming_params_cls = StreamingParameters
        return client

    def start(self, on_result: Callable[[StreamingASRResult], None],
               sample_rate: int = 16000) -> None:
        self._client = self._build_client(on_result)
        self._client.connect(self._streaming_params_cls(
            sample_rate=sample_rate,
            speech_model=self.speech_model,
        ))

    def send_audio(self, pcm_chunk: bytes) -> None:
        if self._client is None:
            raise RuntimeError("call start() before send_audio()")
        self._client.stream(pcm_chunk)

    def stop(self) -> None:
        if self._client is not None:
            self._client.disconnect()
            self._client = None

    # -- separate batch mode, NOT part of the StreamingASRAgent protocol --
    # Provided only so this file has something runnable today against
    # short pre-recorded clips via AssemblyAI's batch endpoint, for offline
    # accuracy testing (e.g. the ASR/diarization bake-off in
    # docs/vendor_decision.md §5) — not suitable for the live conversation
    # hot path.
    def transcribe_batch(self, audio_url_or_path: str) -> ASRResult:
        if not self.api_key:
            raise RuntimeError("ASSEMBLYAI_API_KEY is not set.")
        import assemblyai as aai

        aai.settings.api_key = self.api_key
        config = aai.TranscriptionConfig(speaker_labels=True, language_detection=True)
        transcript = aai.Transcriber().transcribe(audio_url_or_path, config=config)
        return ASRResult(
            text=transcript.text or "",
            language=getattr(transcript, "language_code", "auto"),
            confidence=getattr(transcript, "confidence", 0.0) or 0.0,
        )
