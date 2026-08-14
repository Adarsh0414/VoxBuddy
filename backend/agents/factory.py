"""
Agent factory — decides at runtime whether the pipeline uses the mocked
agents (default, zero-config, what Phase 1 has been running) or a real
vendor adapter, controlled by environment variables so nobody has to edit
code to flip this.

This keeps session/manager.py decoupled from any specific vendor, per the
agents/base.py Protocol design — swapping providers is a config change,
not a code change.
"""

from __future__ import annotations

import os

from .base import StreamingASRAgent, TranslationAgent, TTSAgent
from .mocks import MockTranslationAgent


def get_translation_agent() -> TranslationAgent:
    """
    Selects the translation agent based on VOXBUDDY_TRANSLATION_PROVIDER:
      - "mock" (default) — MockTranslationAgent, no network, no API key
      - "anthropic" — AnthropicTranslationAgent, requires ANTHROPIC_API_KEY
      - "gemini" — GeminiTranslationAgent, requires GEMINI_API_KEY. Same
        TranslationAgent protocol, same context-injection prompt design —
        a straight alternative, not a lesser option. Pick whichever
        vendor's pricing/quota/latency you prefer; nothing else in the
        pipeline needs to change either way.

    Only translation has a real implementation wired up so far (see
    docs/vendor_decision.md §4) — ASR and TTS stay mocked until the async
    streaming interface work described in agents/asr_assemblyai.py is done.
    """
    provider = os.environ.get("VOXBUDDY_TRANSLATION_PROVIDER", "mock").lower()

    if provider == "mock":
        return MockTranslationAgent()

    if provider == "anthropic":
        from .translation_anthropic import AnthropicTranslationAgent
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "VOXBUDDY_TRANSLATION_PROVIDER=anthropic requires "
                "ANTHROPIC_API_KEY to be set."
            )
        return AnthropicTranslationAgent(api_key=api_key)

    if provider == "gemini":
        from .translation_gemini import GeminiTranslationAgent
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "VOXBUDDY_TRANSLATION_PROVIDER=gemini requires "
                "GEMINI_API_KEY to be set."
            )
        return GeminiTranslationAgent(api_key=api_key)

    raise ValueError(
        f"Unknown VOXBUDDY_TRANSLATION_PROVIDER='{provider}'. "
        f"Valid options: 'mock', 'anthropic', 'gemini'."
    )


def get_streaming_asr_agent() -> StreamingASRAgent:
    """
    Selects the streaming ASR agent based on VOXBUDDY_ASR_PROVIDER:
      - "mock" (default) — MockStreamingASRAgent. Takes plain text tokens,
        not real audio, so it CANNOT transcribe a real microphone — it only
        proves the transport/pipeline wiring works end to end.
      - "assemblyai" — AssemblyAIStreamingASRAgent, requires
        ASSEMBLYAI_API_KEY. This is the one that turns real PCM audio from
        a microphone into text. See agents/asr_assemblyai.py's module
        docstring: scaffolded against the real SDK shape but not
        live-tested against real AssemblyAI traffic yet.

    Added alongside the new /ws/{session_id}/audio endpoint in app.py,
    which is the first caller that pushes real audio bytes through this
    agent rather than mock text tokens.
    """
    provider = os.environ.get("VOXBUDDY_ASR_PROVIDER", "mock").lower()

    if provider == "mock":
        from .mock_streaming_asr import MockStreamingASRAgent
        return MockStreamingASRAgent()

    if provider == "assemblyai":
        from .asr_assemblyai import AssemblyAIStreamingASRAgent
        api_key = os.environ.get("ASSEMBLYAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "VOXBUDDY_ASR_PROVIDER=assemblyai requires "
                "ASSEMBLYAI_API_KEY to be set."
            )
        return AssemblyAIStreamingASRAgent(api_key=api_key)

    raise ValueError(
        f"Unknown VOXBUDDY_ASR_PROVIDER='{provider}'. "
        f"Valid options: 'mock', 'assemblyai'."
    )


def get_tts_agent() -> tuple[TTSAgent, str]:
    """
    Selects the TTS agent based on VOXBUDDY_TTS_PROVIDER, and returns the
    audio format it produces alongside it — callers (session/manager.py,
    then app.py's _to_out) need the format to tell the frontend whether
    audio_b64 is actually playable audio or the mock's placeholder bytes:
      - "mock" (default) — MockTTSAgent. audio_bytes is just the input
        text UTF-8 encoded, NOT audio. Format returned: "mock-text" — the
        frontend must not try to play this through an <audio> element.
      - "elevenlabs" — ElevenLabsTTSAgent, requires ELEVENLABS_API_KEY.
        Produces real mp3 bytes. Format returned: "mp3".
    """
    provider = os.environ.get("VOXBUDDY_TTS_PROVIDER", "mock").lower()

    if provider == "mock":
        from .mocks import MockTTSAgent
        return MockTTSAgent(), "mock-text"

    if provider == "elevenlabs":
        from .tts_elevenlabs import ElevenLabsTTSAgent
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "VOXBUDDY_TTS_PROVIDER=elevenlabs requires "
                "ELEVENLABS_API_KEY to be set."
            )
        return ElevenLabsTTSAgent(api_key=api_key), "mp3"

    raise ValueError(
        f"Unknown VOXBUDDY_TTS_PROVIDER='{provider}'. "
        f"Valid options: 'mock', 'elevenlabs'."
    )
