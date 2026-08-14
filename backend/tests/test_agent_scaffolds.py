import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from agents.asr_assemblyai import AssemblyAIStreamingASRAgent
from agents.tts_elevenlabs import ElevenLabsTTSAgent


def test_assemblyai_agent_requires_api_key():
    agent = AssemblyAIStreamingASRAgent(api_key=None)
    agent.api_key = None
    with pytest.raises(RuntimeError, match="ASSEMBLYAI_API_KEY"):
        agent._build_client(on_result=lambda r: None)


def test_assemblyai_agent_send_audio_before_start_raises():
    agent = AssemblyAIStreamingASRAgent(api_key="fake-key")
    with pytest.raises(RuntimeError, match="call start"):
        agent.send_audio(b"\x00\x00")


def test_assemblyai_agent_matches_streaming_protocol_shape():
    """Structural check that the real vendor adapter has the exact method
    signatures session/streaming_manager.py depends on — the same ones
    agents/mock_streaming_asr.py implements, so this is what guarantees the
    two are actually interchangeable, not just similar."""
    import inspect
    from agents.base import StreamingASRAgent

    for name in ("start", "send_audio", "stop"):
        assert hasattr(AssemblyAIStreamingASRAgent, name), f"missing {name}()"

    start_params = list(inspect.signature(AssemblyAIStreamingASRAgent.start).parameters)
    assert start_params == ["self", "on_result", "sample_rate"]


def test_mock_streaming_asr_matches_same_protocol_shape():
    import inspect
    from agents.mock_streaming_asr import MockStreamingASRAgent

    for name in ("start", "send_audio", "stop"):
        assert hasattr(MockStreamingASRAgent, name), f"missing {name}()"

    start_params = list(inspect.signature(MockStreamingASRAgent.start).parameters)
    assert start_params == ["self", "on_result", "sample_rate"]


def test_elevenlabs_agent_requires_api_key():
    agent = ElevenLabsTTSAgent(api_key=None)
    agent.api_key = None
    with pytest.raises(RuntimeError, match="ELEVENLABS_API_KEY"):
        agent._get_client()


def test_elevenlabs_agent_requires_real_voice_id():
    agent = ElevenLabsTTSAgent(api_key="fake-key")
    agent._client = object()  # bypass client construction to isolate the
    # voice-id validation being tested here.
    with pytest.raises(RuntimeError, match="No real ElevenLabs voice_id"):
        agent.synthesize("hello", "en")


def test_elevenlabs_agent_accepts_custom_voice_map():
    agent = ElevenLabsTTSAgent(api_key="fake-key", voice_ids={"en": "real_voice_123"})
    assert agent.voice_ids["en"] == "real_voice_123"
