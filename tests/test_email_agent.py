# -*- coding: utf-8 -*-
import builtins
import types
import pytest


class DummyEmailAgent:
    """Lightweight proxy to access the real EmailAgent methods if needed.
    We import the project agent lazily to avoid heavy deps in test discovery.
    """
    def __init__(self):
        from agents.email_agent import EmailAgent
        self.agent = EmailAgent()

    def build_reply_prompt(self, subject, body, sender, history, extra, tone):
        # Access the internal method through a small harness by triggering a task.
        # We structure task_data to hit reply generation path.
        from agents.agent_protocol import AgentMessage, MessageType
        message = AgentMessage(
            type=MessageType.TASK_REQUEST.value,
            content={
                "task_id": "t1",
                "task_data": {
                    "type": "generate_reply",
                    "subject": subject,
                    "body": body,
                    "from": sender,
                    "history": history,
                    "extra_instruction": extra,
                    "tone": tone,
                }
            }
        )
        # Monkeypatch prompt loader so we can see preambles are used.
        return self.agent._handle_task_request(message)


@pytest.fixture(autouse=True)
def patch_prompt_loader_and_openai(monkeypatch):
    # Ensure prompt_loader returns sentinel strings
    from configs import prompt_loader

    def fake_get_prompt_text(key: str, default: str = ""):
        if key == "email_analysis_preamble":
            return "[ANALYSIS-PREAMBLE]"
        if key == "email_reply_preamble":
            return "[REPLY-PREAMBLE]"
        return default

    monkeypatch.setattr(prompt_loader, "get_prompt_text", fake_get_prompt_text, raising=True)
    # Also patch the imported symbol within agents.email_agent
    try:
        import agents.email_agent as email_agent_module
        monkeypatch.setattr(email_agent_module, "get_prompt_text", fake_get_prompt_text, raising=False)
    except Exception:
        # If module not imported yet, it will import after this fixture; the prompt_loader patch will still help
        pass

    # Stub OpenAI client to echo prompt back so we can assert contents
    class _Msg:
        def __init__(self, content):
            self.message = types.SimpleNamespace(content=content)

    class _Choices:
        def __init__(self, content):
            self.choices = [_Msg(content)]

    class DummyCompletions:
        def create(self, model, messages, max_tokens, temperature):
            # Echo the user prompt content to validate tone/preamble injection
            prompt = messages[0]["content"]
            return _Choices(prompt)

    class DummyChat:
        def __init__(self):
            self.completions = DummyCompletions()

    class DummyOpenAI:
        def __init__(self, api_key=None):
            self.chat = DummyChat()

    # Patch import site: when email_agent does `from openai import OpenAI`
    import sys
    import types as _types
    fake_openai_mod = _types.ModuleType("openai")
    fake_openai_mod.OpenAI = DummyOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai_mod)
    yield


def test_email_reply_includes_tone_and_preamble(monkeypatch):
    agent = DummyEmailAgent()
    res = agent.build_reply_prompt(
        subject="S",
        body="B",
        sender="alice@example.com",
        history="H",
        extra="E",
        tone="공손한",
    )
    assert res.get("status") == "success"
    result = res.get("result", {})
    text_blob = str(result)
    # The dummy model echoes the prompt, so it must include the preamble and tone
    assert "[REPLY-PREAMBLE]" in text_blob
    assert "요청 톤" in text_blob and "공손" in text_blob
