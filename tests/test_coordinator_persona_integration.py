# -*- coding: utf-8 -*-
import types
import pytest


def test_coordinator_attaches_persona(monkeypatch):
    # Monkeypatch PersonaSelectorAgent used inside coordinator to return a deterministic persona
    import agents.coordinator_agent as coord_mod

    class DummySelector:
        def __init__(self, strategy="rules_first"):  # signature compatibility
            pass
        def select(self, task_meta):
            return {
                "name": "테스트 페르소나",
                "score": 0.99,
                "persona": {
                    "직책": "애널리스트",
                    "전문 분야": "연구",
                    "업무 영역": "분석",
                    "사고방식": "체계적"
                }
            }

    monkeypatch.setattr(coord_mod, "PersonaSelectorAgent", DummySelector, raising=True)

    from agents.coordinator_agent import CoordinatorAgent
    agent = CoordinatorAgent()

    task_data = {
        "type": "user_request",
        "task_id": "u1",
        "content": "AI 음성 기술 동향을 조사하고 요약해줘",
    }

    res = agent.process_task(task_data)
    assert res.get("status") == "subtasks_created"
    subtasks = res.get("subtasks", [])
    assert len(subtasks) >= 1
    # All generated subtasks should include persona metadata
    assert all("persona" in st and "persona_name" in st for st in subtasks)
