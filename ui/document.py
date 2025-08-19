# ui/document.py
# -*- coding: utf-8 -*-
"""
Streamlit 문서 생성/협업/확장 탭 렌더러.
기존 app.py의 문서 관련 UI를 모듈화하여 유지보수성을 높입니다.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, List

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

# 종속 리소스는 런타임에 import (테스트 환경 안전성 고려)

def _lazy_imports():
    from tools.planning_tool.configs import personas, DOCUMENT_TEMPLATES, TEMPLATE_LABELS  # type: ignore
    from tools.planning_tool.core import (
        execute_create_new_planning_document,
        execute_collaboration_planning,
        execute_expand_notion_document,
    )  # type: ignore
    return personas, DOCUMENT_TEMPLATES, TEMPLATE_LABELS, execute_create_new_planning_document, execute_collaboration_planning, execute_expand_notion_document


def render_document_ui() -> None:
    if st is None:
        return

    personas, DOCUMENT_TEMPLATES, TEMPLATE_LABELS, execute_create_new_planning_document, execute_collaboration_planning, execute_expand_notion_document = _lazy_imports()
    
    # 페르소나 표시 라벨: 이름 (역할)
    def _persona_label(name: str) -> str:
        try:
            role = (personas.get(name) or {}).get('role')
            return f"{name} ({role})" if role else name
        except Exception:
            return str(name)
    # 템플릿 라벨: 한국어 라벨 우선, 없으면 키 그대로
    def _template_label(key: str) -> str:
        try:
            return (TEMPLATE_LABELS or {}).get(key, key)
        except Exception:
            return str(key)
    # 자동 기본값 선정을 위한 에이전트는 지연 임포트
    try:
        from agents.persona_selector_agent import PersonaSelectorAgent  # type: ignore
        _selector = PersonaSelectorAgent()
    except Exception:
        _selector = None  # 선택 실패 시에도 UI는 동작해야 함

    # --- 문서 상세 업무 선택 창 (채팅창 위에 표시) ---
    document_tasks: List[Dict[str, str]] = [
        {"name": "문서 신규 작성 자동화", "key": "new_document"},
        {"name": "다중 페르소나 협업 자동화", "key": "persona_collab"},
        {"name": "문서 확장 자동화", "key": "doc_expand"},
    ]

    tab_labels = [task["name"] for task in document_tasks]
    tabs = st.tabs(tab_labels)

    for idx, tab in enumerate(tabs):
        with tab:
            task_key = document_tasks[idx]["key"]

            if task_key == "new_document":
                # 자동 기본값: 작성자/검토자/템플릿 (폼 외부에서 session_state에 세팅)
                try:
                    if _selector:
                        task_meta = {
                            "domain": "planning",
                            "original_request": st.session_state.get("요구사항", ""),
                        }
                        pair = _selector.select_pair(task_meta) or {"writer": None, "reviewer": None}
                        if pair.get("writer") and not st.session_state.get("작성자"):
                            st.session_state["작성자"] = pair["writer"]
                        if pair.get("reviewer") and not st.session_state.get("피드백담당자"):
                            st.session_state["피드백담당자"] = pair["reviewer"]
                    # 템플릿 기본값
                    if not st.session_state.get("문서템플릿"):
                        first_tpl = next(iter(DOCUMENT_TEMPLATES.keys())) if DOCUMENT_TEMPLATES else None
                        if first_tpl:
                            st.session_state["문서템플릿"] = first_tpl
                except Exception:
                    pass
                st.markdown("#### 신규 문서 작성")
                # 1. 입력 폼
                with st.form("new_doc_form"):
                    _form_error = None
                    try:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.selectbox("작성자", list(personas.keys()), key="작성자", format_func=_persona_label)
                        with col2:
                            st.selectbox("피드백 담당자", list(personas.keys()), key="피드백담당자", format_func=_persona_label)
                        with col3:
                            st.selectbox("문서 템플릿", list(DOCUMENT_TEMPLATES.keys()), key="문서템플릿", format_func=_template_label)
                        st.text_area("요구사항 입력", placeholder="예시: 신규 유저 유입 이벤트 기획서 작성", key="요구사항")
                    except Exception as e:
                        _form_error = e
                        st.error("신규 문서 폼 렌더링 중 오류가 발생했습니다.")
                    submitted = st.form_submit_button("문서 생성")
                if '_form_error' in locals() and _form_error:
                    st.exception(_form_error)
                if submitted and not (_form_error):
                    with st.spinner("문서 생성 중..."):
                        if not isinstance(st.session_state.get("current_process"), dict):
                            st.session_state["current_process"] = {"type": "doc", "desc": "문서 초안 생성 중...", "progress": 0.1}
                        st.session_state["current_process"]["desc"] = "문서 초안 생성 중..."
                        st.session_state["current_process"]["progress"] = 0.2
                        result = execute_create_new_planning_document(
                            user_input=st.session_state["요구사항"],
                            writer_persona_name=st.session_state["작성자"],
                            reviewer_persona_name=st.session_state["피드백담당자"],
                            template_name=st.session_state["문서템플릿"],
                        )
                        if not isinstance(st.session_state.get("current_process"), dict):
                            st.session_state["current_process"] = {"type": "doc", "desc": "피드백 반영 중...", "progress": 0.5}
                        st.session_state["current_process"]["desc"] = "피드백 반영 중..."
                        st.session_state["current_process"]["progress"] = 0.5
                        st.session_state['draft'] = result.get('draft')
                        st.session_state['feedback'] = result.get('feedback')
                        st.session_state['final_doc'] = result.get('final_doc')
                        st.session_state['notion_url'] = result.get('notion_url')
                        st.session_state['message'] = result.get('message')
                        st.session_state['doc_step'] = 'feedback'
                # 2. 결과 및 추가 요구사항 입력
                if st.session_state.get('doc_step') == 'feedback' and st.session_state.get('draft'):
                    st.markdown("#### 초안")
                    st.write(st.session_state['draft'])
                    st.markdown("#### 피드백")
                    st.write(st.session_state['feedback'])
                    추가요구 = st.text_area("추가 요구사항 입력", key="추가요구")
                    if st.button("최종 문서 생성"):
                        최종요구 = st.session_state['요구사항'] + "\n" + 추가요구 if 추가요구 else st.session_state['요구사항']
                        with st.spinner("최종 문서 생성 중..."):
                            if not isinstance(st.session_state.get("current_process"), dict):
                                st.session_state["current_process"] = {"type": "doc", "desc": "최종 문서 생성 중...", "progress": 0.1}
                            st.session_state["current_process"]["desc"] = "최종 문서 생성 중..."
                            st.session_state["current_process"]["progress"] = 0.2
                            result = execute_create_new_planning_document(
                                user_input=최종요구,
                                writer_persona_name=st.session_state['작성자'],
                                reviewer_persona_name=st.session_state['피드백담당자'],
                                template_name=st.session_state['문서템플릿'],
                            )
                            if not isinstance(st.session_state.get("current_process"), dict):
                                st.session_state["current_process"] = {"type": "doc", "desc": "최종 문서 피드백 반영 중...", "progress": 0.5}
                            st.session_state["current_process"]["desc"] = "최종 문서 피드백 반영 중..."
                            st.session_state["current_process"]["progress"] = 0.5
                            st.session_state['final_doc'] = result.get('final_doc')
                            st.session_state['notion_url'] = result.get('notion_url')
                            st.session_state['message'] = result.get('message')
                            st.session_state['doc_step'] = 'final'
                if st.session_state.get('doc_step') == 'final' and st.session_state.get('final_doc'):
                    st.success("최종 문서가 생성되었습니다!")
                    st.markdown("#### 최종 문서")
                    st.write(st.session_state['final_doc'])
                    if st.session_state.get('notion_url'):
                        st.markdown(f"[Notion에서 문서 확인하기]({st.session_state['notion_url']})")
                    st.info(st.session_state.get('message', ''))

            elif task_key == "persona_collab":
                # 자동 기본값: 초안작성자/검토자/업무분배/템플릿 (폼 외부)
                try:
                    if _selector:
                        task_meta = {
                            "domain": "planning",
                            "original_request": st.session_state.get("collab_요구사항", ""),
                            "description": st.session_state.get("collab_프로젝트제목", ""),
                        }
                        pair = _selector.select_pair(task_meta) or {"writer": None, "reviewer": None}
                        if pair.get("writer") and not st.session_state.get("collab_초안작성자"):
                            st.session_state["collab_초안작성자"] = pair["writer"]
                        if pair.get("reviewer") and not st.session_state.get("collab_검토자"):
                            st.session_state["collab_검토자"] = pair["reviewer"]
                        if not st.session_state.get("collab_업무분배"):
                            names = _selector.select_collaborators(task_meta, k=3) or []
                            if names:
                                st.session_state["collab_업무분배"] = names
                    if not st.session_state.get("collab_문서템플릿"):
                        first_tpl = next(iter(DOCUMENT_TEMPLATES.keys())) if DOCUMENT_TEMPLATES else None
                        if first_tpl:
                            st.session_state["collab_문서템플릿"] = first_tpl
                except Exception:
                    pass
                st.markdown("#### 다중 페르소나 협업 자동화")
                with st.form("collab_form"):
                    _form_error = None
                    try:
                        col1, col2 = st.columns(2)
                        with col1:
                            프로젝트제목 = st.text_input("프로젝트 제목", key="collab_프로젝트제목")
                            초안작성자 = st.selectbox("초안 작성자", list(personas.keys()), key="collab_초안작성자", format_func=_persona_label)
                            검토자 = st.selectbox("검토자", list(personas.keys()), key="collab_검토자", format_func=_persona_label)
                        with col2:
                            템플릿 = st.selectbox("문서 템플릿", list(DOCUMENT_TEMPLATES.keys()), key="collab_문서템플릿", format_func=_template_label)
                            업무분배 = st.multiselect("업무 분배 페르소나(2명 이상)", list(personas.keys()), key="collab_업무분배", format_func=_persona_label)
                        요구사항 = st.text_area("요구사항 입력", placeholder="예시: 신규 프로젝트 협업 계획 작성", key="collab_요구사항")
                    except Exception as e:
                        _form_error = e
                        st.error("협업 폼 렌더링 중 오류가 발생했습니다.")
                    submitted = st.form_submit_button("협업 계획 생성")
                if '_form_error' in locals() and _form_error:
                    st.exception(_form_error)
                if submitted and not (_form_error):
                    if len(업무분배) < 2:
                        st.warning("업무 분배 페르소나는 2명 이상 선택해야 합니다.")
                    else:
                        if not isinstance(st.session_state.get("current_process"), dict):
                            st.session_state["current_process"] = {"type": "doc", "desc": "협업 계획 초안 생성 중...", "progress": 0.1}
                        with st.spinner("협업 계획 생성 중..."):
                            st.session_state["current_process"]["desc"] = "협업 계획 초안 생성 중..."
                            st.session_state["current_process"]["progress"] = 0.2
                            result = execute_collaboration_planning(
                                project_title=프로젝트제목,
                                base_document_type=템플릿,
                                user_requirements=요구사항,
                                writer_persona_name=초안작성자,
                                allocate_to_persona_names=업무분배,
                                review_by_persona_name=검토자,
                            )
                            if not isinstance(st.session_state.get("current_process"), dict):
                                st.session_state["current_process"] = {"type": "doc", "desc": "협업 계획 피드백/통합 중...", "progress": 0.7}
                            st.session_state["current_process"]["desc"] = "협업 계획 피드백/통합 중..."
                            st.session_state["current_process"]["progress"] = 0.7
                            st.session_state['collab_result'] = result
                        st.session_state["current_process"] = None

            elif task_key == "doc_expand":
                # 자동 기본값: 작성자/신규템플릿 (폼 외부)
                try:
                    if _selector:
                        task_meta = {
                            "domain": "planning",
                            "original_request": st.session_state.get("expand_추가요구", ""),
                            "description": st.session_state.get("expand_참조키워드", ""),
                        }
                        pair = _selector.select_pair(task_meta) or {"writer": None, "reviewer": None}
                        if pair.get("writer") and not st.session_state.get("expand_작성자"):
                            st.session_state["expand_작성자"] = pair["writer"]
                    if not st.session_state.get("expand_신규템플릿"):
                        first_tpl = next(iter(DOCUMENT_TEMPLATES.keys())) if DOCUMENT_TEMPLATES else None
                        if first_tpl:
                            st.session_state["expand_신규템플릿"] = first_tpl
                except Exception:
                    pass
                st.markdown("#### 문서 확장 자동화")
                with st.form("expand_form"):
                    _form_error = None
                    try:
                        col1, col2 = st.columns(2)
                        with col1:
                            참조키워드 = st.text_input("참조 문서 키워드", key="expand_참조키워드")
                            작성자 = st.selectbox("작성자", list(personas.keys()), key="expand_작성자", format_func=_persona_label)
                        with col2:
                            신규템플릿 = st.selectbox("신규 문서 템플릿", list(DOCUMENT_TEMPLATES.keys()), key="expand_신규템플릿", format_func=_template_label)
                            추가요구 = st.text_area("추가 요구사항 입력", key="expand_추가요구")
                    except Exception as e:
                        _form_error = e
                        st.error("문서 확장 폼 렌더링 중 오류가 발생했습니다.")
                    submitted = st.form_submit_button("문서 확장 생성")
                if '_form_error' in locals() and _form_error:
                    st.exception(_form_error)
                if submitted and not (_form_error):
                    if not isinstance(st.session_state.get("current_process"), dict):
                        st.session_state["current_process"] = {"type": "doc", "desc": "문서 확장 초안 생성 중...", "progress": 0.1}
                    with st.spinner("문서 확장 생성 중..."):
                        st.session_state["current_process"]["desc"] = "문서 확장 초안 생성 중..."
                        st.session_state["current_process"]["progress"] = 0.2
                        result = execute_expand_notion_document(
                            keyword=참조키워드,
                            new_doc_type=신규템플릿,
                            extra_requirements=추가요구,
                            writer_persona_name=작성자,
                        )
                        if not isinstance(st.session_state.get("current_process"), dict):
                            st.session_state["current_process"] = {"type": "doc", "desc": "문서 확장 피드백/통합 중...", "progress": 0.7}
                        st.session_state["current_process"]["desc"] = "문서 확장 피드백/통합 중..."
                        st.session_state["current_process"]["progress"] = 0.7
                        st.session_state['expand_result'] = result
                    st.session_state["current_process"] = None

            else:
                st.markdown(f"### {document_tasks[idx]['name']}")
                st.markdown(f"<div style='margin-top:32px;'><b>{document_tasks[idx]['name']}</b> 업문 영역 (추후 구현)</div>", unsafe_allow_html=True)
