# -*- coding: utf-8 -*-
import sys
import types
import pytest


@pytest.fixture(autouse=True)
def patch_prompt_loader_and_openai(monkeypatch):
    # Patch prompt loader: ensure research preamble is deterministic
    from configs import prompt_loader

    def fake_get_prompt_text(key: str, default: str = ""):
        if key == "research":
            return "[RESEARCH-PREAMBLE] 연구 프롬프트"
        return default

    monkeypatch.setattr(prompt_loader, "get_prompt_text", fake_get_prompt_text, raising=True)
    # Also patch the imported symbol within agents.research_agent if present
    try:
        import agents.research_agent as research_agent_module
        monkeypatch.setattr(research_agent_module, "get_prompt_text", fake_get_prompt_text, raising=False)
    except Exception:
        pass

    # Stub OpenAI client to echo prompt back
    class _Msg:
        def __init__(self, content):
            self.message = types.SimpleNamespace(content=content)

    class _Choices:
        def __init__(self, content):
            self.choices = [_Msg(content)]

    class DummyCompletions:
        def create(self, model, messages, max_tokens, temperature):
            prompt = messages[0]["content"]
            return _Choices(prompt)

    class DummyChat:
        def __init__(self):
            self.completions = DummyCompletions()

    class DummyOpenAI:
        def __init__(self, api_key=None):
            self.chat = DummyChat()

    fake_openai_mod = types.ModuleType("openai")
    fake_openai_mod.OpenAI = DummyOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai_mod)
    yield


def test_research_agent_uses_yaml_and_persona(monkeypatch):
    from agents.research_agent import ResearchAgent

    agent = ResearchAgent()

    # Stub summarize_text to expose used prompt for assertion
    class _DummySummarizer:
        def summarize_text(self, text, prompt_template):
            return {"status": "success", "summary": f"SUM({text})", "used_prompt": prompt_template}

    agent.loaded_tools["summarization_tool"] = _DummySummarizer()

    task_data = {
        "type": "research",
        "task_id": "r1",
        "content": "테스트 쿼리",
        "persona": {
            "직책": "리서처",
            "전문 분야": "기술 조사",
            "업무 영역": "리서치",
            "사고방식": "체계적",
        },
    }

    res = agent.process_task(task_data)
    assert res.get("status") == "success"
    result = res.get("result", {})
    used_prompt = result.get("used_prompt", "")
    assert "RESEARCH-PREAMBLE" in used_prompt
    assert "페르소나 지침" in used_prompt
