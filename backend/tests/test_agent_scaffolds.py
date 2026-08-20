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


def test_elevenlabs_agent_raises_clear_error_when_account_has_no_premade_voices():
    """When no voice_ids are configured/cached, synthesize() resolves one
    from the account's own premade voices at runtime (see
    tts_elevenlabs.py's module docstring for why hardcoding a specific ID
    is unreliable) — this checks the failure path when that account
    genuinely has none, rather than the old placeholder-string check this
    test used to cover."""
    class _EmptyVoicesResponse:
        voices = []

    class _FakeVoicesClient:
        def search(self, category=None):
            return _EmptyVoicesResponse()

    class _FakeClient:
        voices = _FakeVoicesClient()

    agent = ElevenLabsTTSAgent(api_key="fake-key")
    agent._client = _FakeClient()
    with pytest.raises(RuntimeError, match="No premade voices found"):
        agent.synthesize("hello", "en")


def test_elevenlabs_agent_resolves_and_caches_a_premade_voice():
    """The core of the fix: with no voice_ids configured, a real voice_id
    is looked up from the account's premade voices and reused (cached)
    on later calls instead of re-querying every time."""
    class _FakeVoice:
        def __init__(self, voice_id):
            self.voice_id = voice_id

    class _VoicesResponse:
        voices = [_FakeVoice("resolved_premade_voice_1"), _FakeVoice("resolved_premade_voice_2")]

    search_calls = []

    class _FakeVoicesClient:
        def search(self, category=None):
            search_calls.append(category)
            return _VoicesResponse()

    class _FakeTextToSpeechClient:
        def convert(self, voice_id, model_id, text, output_format):
            assert voice_id == "resolved_premade_voice_1"
            return [b"fake-mp3-bytes"]

    class _FakeClient:
        voices = _FakeVoicesClient()
        text_to_speech = _FakeTextToSpeechClient()

    agent = ElevenLabsTTSAgent(api_key="fake-key")
    agent._client = _FakeClient()

    result = agent.synthesize("hello", "en")
    assert result.audio_bytes == b"fake-mp3-bytes"
    assert agent.voice_ids["en"] == "resolved_premade_voice_1"
    assert search_calls == ["premade"]

    # Second call reuses the cached voice_id — no second search() call.
    agent.synthesize("hello again", "en")
    assert search_calls == ["premade"]


def test_elevenlabs_agent_self_heals_when_cached_voice_becomes_a_library_voice():
    """If a previously-working (or explicitly configured) voice_id starts
    failing with the Library-voice 402, the agent should drop it and
    resolve a fresh premade voice instead of failing the same way on
    every subsequent call — this is the self-healing retry path."""
    class _FakeVoice:
        def __init__(self, voice_id):
            self.voice_id = voice_id

    class _VoicesResponse:
        voices = [_FakeVoice("fresh_premade_voice")]

    class _FakeVoicesClient:
        def search(self, category=None):
            return _VoicesResponse()

    call_log = []

    class _FakeTextToSpeechClient:
        def convert(self, voice_id, model_id, text, output_format):
            call_log.append(voice_id)
            if voice_id == "stale_library_voice":
                raise RuntimeError(
                    "402: Free users cannot use library voices via the API."
                )
            return [b"fake-mp3-bytes"]

    class _FakeClient:
        voices = _FakeVoicesClient()
        text_to_speech = _FakeTextToSpeechClient()

    agent = ElevenLabsTTSAgent(api_key="fake-key", voice_ids={"en": "stale_library_voice"})
    agent._client = _FakeClient()

    result = agent.synthesize("hello", "en")
    assert result.audio_bytes == b"fake-mp3-bytes"
    assert call_log == ["stale_library_voice", "fresh_premade_voice"]
    assert agent.voice_ids["en"] == "fresh_premade_voice"


def test_elevenlabs_agent_accepts_custom_voice_map():
    agent = ElevenLabsTTSAgent(api_key="fake-key", voice_ids={"en": "real_voice_123"})
    assert agent.voice_ids["en"] == "real_voice_123"
