# -*- coding: utf-8 -*-
import json
import pytest

from personas.repository import PersonaRepository as R
from agents.persona_selector_agent import PersonaSelectorAgent as A


def setup_module():
    # 캐시 리프레시 보장
    R.refresh()


def test_rank_category_priority():
    meta = {
        "category": "pm",
        "role": "프로덕트 매니저",
        "expertise": "전환율",
        "skills": ["AARRR", "실험 설계", "전환율"],
        "style": "concise",
        "original_request": "온보딩 전환율 A/B 테스트 개선"
    }
    ranked = R.rank_for_task(meta, top_k=5)
    assert isinstance(ranked, list)
    if ranked:
        # 최상위는 pm 카테고리여야 한다 (우선 가중치 강화)
        top = ranked[0]
        assert top[1].get("category") == "pm"


def test_selector_with_hierarchy_and_rationale():
    agent = A()
    meta = {
        "category": "디자이너",
        "role": "프로덕트 디자이너",
        "expertise": "UX",
        "skills": ["Wireframe", "User Flow"],
        "style": "polite",
        "description": "온보딩 UX 시나리오"
    }
    res = agent.select(meta)
    # 선택이 되면 rationale 포함
    if res is not None:
        assert "rationale" in res
        rat = res["rationale"]
        assert isinstance(rat, dict)
        # 최소한 필터 단계 요약이 있어야 함
        assert "filters" in rat


def test_collaborators_at_least_returns_list():
    agent = A()
    names = agent.select_collaborators({"category": "개발자", "skills": ["LLM", "RAG"]}, k=2)
    assert isinstance(names, list)
    assert len(names) <= 2
