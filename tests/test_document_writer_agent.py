# -*- coding: utf-8 -*-
import pytest


def test_document_writer_merges_persona_and_yaml(monkeypatch):
    # Stub prompt_loader
    from configs import prompt_loader

    def fake_get_prompt_text(key: str, default: str = ""):
        if key == "document_writer":
            return "[DOC-PREAMBLE] 문서 작성 원칙"
        return default

    monkeypatch.setattr(prompt_loader, "get_prompt_text", fake_get_prompt_text, raising=True)

    from agents.document_writer_agent import DocumentWriterAgent

    # Force built-in rendering path (no external formatter) so notes are visible
    agent = DocumentWriterAgent(tools=[])
    task_data = {
        "type": "document_creation",
        "task_id": "t1",
        "document_type": "memo",
        "content": {
            "title": "테스트 메모",
            "content": "본문",
            "notes": "기존 노트"
        },
        "persona": {
            "직책": "데이터 분석가",
            "전문 분야": "분석",
            "업무 영역": "리포팅",
            "사고방식": "정확성"
        }
    }

    res = agent.process_task(task_data)
    assert res.get("status") == "success"
    doc_result = res["result"]
    # Built-in path returns nested result dict; normalize
    if isinstance(doc_result, dict) and "result" in doc_result:
        doc_result = doc_result["result"]

    # Since DocumentWriterAgent returns {'result': {...}} from _process_document_creation_task,
    # and built-in creation returns {'status': 'success', 'document': '...'}
    # We cannot directly read notes after rendering. But we can assert that the agent
    # prepended notes before rendering by checking the source 'content' impacts the document string.
    text = str(doc_result)
    assert "페르소나 지침" in text
    assert "문서 작성 지침" in text
    assert "DOC-PREAMBLE" in text or "문서 작성 원칙" in text
