# -*- coding: utf-8 -*-
import types
import sys
import pytest


def _install_fake_voice_tool(monkeypatch):
    # Create module tree: tools.voice_tool.core with TOOL_MAP and TOOL_SCHEMAS
    core = types.ModuleType("tools.voice_tool.core")

    def speak_text(text: str = "", detailed_text: str = "", speed: float = 1.0):
        payload = detailed_text or text
        return (f"AUDIO({payload}) speed={speed}").encode("utf-8")

    def speech_to_text_from_mic_data(audio_data: bytes):
        return {"text": "TRANSCRIBED", "len": len(audio_data)}

    core.TOOL_MAP = {
        "speak_text": speak_text,
        "speech_to_text_from_mic_data": speech_to_text_from_mic_data,
    }
    core.TOOL_SCHEMAS = []

    # Ensure package modules exist
    tools_pkg = types.ModuleType("tools")
    voice_tool_pkg = types.ModuleType("tools.voice_tool")

    monkeypatch.setitem(sys.modules, "tools", tools_pkg)
    monkeypatch.setitem(sys.modules, "tools.voice_tool", voice_tool_pkg)
    monkeypatch.setitem(sys.modules, "tools.voice_tool.core", core)


@pytest.fixture(autouse=True)
def setup_fake_tool(monkeypatch):
    _install_fake_voice_tool(monkeypatch)
    yield


def test_voice_agent_tts_alias(monkeypatch):
    from agents.voice_agent import VoiceAgent
    agent = VoiceAgent(tools=["voice_tool"])  # will use our fake tool

    from agents.agent_protocol import AgentMessage, MessageType
    msg = AgentMessage(
        type=MessageType.TASK_REQUEST.value,
        content={
            "task_id": "t1",
            "task_data": {
                "type": "tts",  # alias for text_to_speech
                "text": "hello",
                "speed": 1.2,
            },
        },
    )

    res = agent._handle_task_request(msg)
    assert res.get("status") == "success"
    result = res["result"]
    assert result["audio_data"].startswith(b"AUDIO(")


def test_voice_agent_stt_alias(monkeypatch):
    from agents.voice_agent import VoiceAgent
    agent = VoiceAgent(tools=["voice_tool"])  # will use our fake tool

    from agents.agent_protocol import AgentMessage, MessageType
    msg = AgentMessage(
        type=MessageType.TASK_REQUEST.value,
        content={
            "task_id": "t2",
            "task_data": {
                "type": "stt",  # alias for speech_to_text
                "audio_data": b"xxx",
            },
        },
    )

    res = agent._handle_task_request(msg)
    assert res.get("status") == "success"
    result = res["result"]
    assert result.get("text") == "TRANSCRIBED"
