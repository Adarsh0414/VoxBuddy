"""
Mock implementations of the agent interfaces, used for the Phase 1 PoC and
for unit tests. These simulate realistic latency and confidence behavior
without calling any external vendor — swap these out for real ASR/MT/TTS
providers in Phase 2 once one is benchmarked and chosen (PRD §21).
"""

from __future__ import annotations

import hashlib
import random
import time

from .base import ASRResult, TranslationResult, TTSResult


class MockSpeakerEmbeddingAgent:
    """Deterministic pseudo-embedding derived from a speaker label, so the
    PoC simulation can reliably represent 'the same voice' across turns
    without real audio."""

    def embed(self, speaker_label: str) -> list[float]:
        h = hashlib.sha256(speaker_label.encode()).digest()
        # 8-dim pseudo-embedding from hash bytes, normalized to [-1, 1]
        return [(b / 127.5) - 1.0 for b in h[:8]]


class MockLanguageIDAgent:
    def detect(self, text: str) -> tuple[str, float]:
        # PoC heuristic: tag known sample phrases; real system uses a
        # streaming LID model on audio.
        if any(w in text.lower() for w in ["namaste", "kya", "aap"]):
            return "hi", 0.95
        if any(w in text.lower() for w in ["bonjour", "merci", "comment"]):
            return "fr", 0.95
        return "en", 0.9


class MockASRAgent:
    def transcribe(self, utterance_text: str) -> ASRResult:
        # In the PoC we pass "ground truth" text straight through with a
        # simulated confidence + latency, standing in for a real streaming
        # ASR call.
        time.sleep(0.01)
        return ASRResult(text=utterance_text, language="auto", confidence=round(random.uniform(0.85, 0.99), 2))


class MockTranslationAgent:
    def translate(self, text: str, source_lang: str, target_lang: str,
                   context: list[str]) -> TranslationResult:
        time.sleep(0.01)
        # Stand-in "translation": tag the text with the target language so
        # the pipeline's behavior is observable in the simulation output.
        return TranslationResult(text=f"[{target_lang}] {text}", confidence=round(random.uniform(0.8, 0.97), 2))


class MockTTSAgent:
    def synthesize(self, text: str, target_lang: str) -> TTSResult:
        time.sleep(0.01)
        return TTSResult(audio_bytes=text.encode(), duration_ms=len(text) * 40)
