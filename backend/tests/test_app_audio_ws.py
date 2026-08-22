import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VOXBUDDY_ASR_PROVIDER", "mock")
    import app as app_module
    app_module.sessions.clear()
    return TestClient(app_module.app)


def test_audio_endpoint_accepts_connection_and_creates_session(client):
    with client.websocket_connect("/ws/some-audio-session/audio") as ws:
        # A single frame that happens to be valid UTF-8 text (this is what
        # MockStreamingASRAgent can actually handle — real PCM bytes are
        # covered by the decode-error test below).
        ws.send_bytes(b"namaste")
    import app as app_module
    assert "some-audio-session" in app_module.sessions


def test_audio_endpoint_final_turn_reaches_pipeline(client):
    from agents.mock_streaming_asr import END_OF_TURN

    with client.websocket_connect("/ws/turn-session/audio") as ws:
        # Partial results (adapter._handle_asr_result) don't reach the
        # pipeline or send anything back — only a final (END_OF_TURN) does.
        ws.send_bytes(b"namaste")
        ws.send_bytes(END_OF_TURN.encode("utf-8"))
        final_result = ws.receive_json()
        assert final_result["confidence"] is not None

    import app as app_module
    session = app_module.sessions["turn-session"]
    assert len(session.state.turn_history) == 1


def test_audio_endpoint_reports_real_pcm_incompatible_with_mock(client):
    # Real 16-bit PCM audio is not valid UTF-8 in general — this specific
    # 2-byte frame (0xFF 0xFE) is guaranteed to fail decode(), which is
    # exactly what happens if you point real microphone audio at the mock
    # provider instead of VOXBUDDY_ASR_PROVIDER=assemblyai.
    with client.websocket_connect("/ws/real-audio-session/audio") as ws:
        ws.send_bytes(bytes([0xFF, 0xFE, 0x00, 0x01]))
        result = ws.receive_json()
        assert "error" in result
        assert "assemblyai" in result["error"].lower()


def test_audio_endpoint_without_assemblyai_key_returns_clear_error(client, monkeypatch):
    monkeypatch.setenv("VOXBUDDY_ASR_PROVIDER", "assemblyai")
    monkeypatch.delenv("ASSEMBLYAI_API_KEY", raising=False)
    with client.websocket_connect("/ws/no-key-session/audio") as ws:
        result = ws.receive_json()
        assert "ASSEMBLYAI_API_KEY" in result["error"]


def test_audio_endpoint_translates_into_the_query_param_target_lang(client, monkeypatch):
    """Real bug caught in production: target_lang was hardcoded to "en" in
    this endpoint regardless of what the user actually selected as "You
    speak" during setup — a user with Hindi selected heard English spoken
    back, confirmed on a real device. Fixed by accepting target_lang as a
    query param (populated by the frontend from the logged-in user's own
    preferred_language) instead of a hardcoded default. MockTranslationAgent
    conveniently tags its output with the target_lang it was given
    (`f"[{target_lang}] {text}"`), which is what makes this directly
    assertable without a real translation vendor."""
    monkeypatch.setenv("VOXBUDDY_TRANSLATION_PROVIDER", "mock")
    monkeypatch.setenv("VOXBUDDY_TTS_PROVIDER", "mock")
    from agents.mock_streaming_asr import END_OF_TURN

    with client.websocket_connect("/ws/hindi-session/audio?target_lang=hi") as ws:
        ws.send_bytes(b"namaste")
        ws.send_bytes(END_OF_TURN.encode("utf-8"))
        result = ws.receive_json()

    assert result["translated_text"].startswith("[hi]")


def test_audio_endpoint_defaults_to_english_when_target_lang_omitted(client, monkeypatch):
    """The fallback still exists (the query param is optional) — this just
    confirms omitting it doesn't error, and defaults sanely rather than
    breaking the connection."""
    monkeypatch.setenv("VOXBUDDY_TRANSLATION_PROVIDER", "mock")
    monkeypatch.setenv("VOXBUDDY_TTS_PROVIDER", "mock")
    from agents.mock_streaming_asr import END_OF_TURN

    with client.websocket_connect("/ws/default-lang-session/audio") as ws:
        ws.send_bytes(b"namaste")
        ws.send_bytes(END_OF_TURN.encode("utf-8"))
        result = ws.receive_json()

    assert result["translated_text"].startswith("[en]")
