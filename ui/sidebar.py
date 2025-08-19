# ui/sidebar.py
# -*- coding: utf-8 -*-
"""
Streamlit 사이드바 렌더러 모듈.
- 기능 버튼, 프로세스 대시보드, 푸터, (옵션) 간단 로그 표시
"""
from typing import Any, Dict, Optional

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


def render_sidebar(state: Optional[Dict[str, Any]] = None) -> None:
    if st is None:
        return

    with st.sidebar:
        # 헤더 (단일 표시)
        st.markdown('<div class="sidebar-header"><h4>💼 AI 기능</h4></div>', unsafe_allow_html=True)
        st.divider()

        # 기능 버튼 스타일
        st.markdown(
            """
            <style>
            .feature-button {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .feature-button.active {
                background-color: #e1f5fe !important;
                border: 2px solid #2196f3 !important;
                color: #1976d2 !important;
                font-weight: bold;
            }
            .feature-button:hover {
                background-color: #e9ecef;
                transform: translateY(-2px);
            }
            .feature-icon { font-size: 1.2rem; margin-right: 8px; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # 기능 버튼
        feature_col1, feature_col2 = st.columns(2)

        def toggle_feature(tab_name: str) -> None:
            st.session_state["current_process"] = None  # 탭 전환 시 대시보드 초기화
            current = st.session_state.get("active_feature")
            if current == tab_name:
                st.session_state.active_feature = None
            else:
                st.session_state.active_feature = tab_name
                if tab_name == "document":
                    st.session_state.active_document_task = None

        with feature_col1:
            if st.button("💬 챗봇", key="btn_chatbot", use_container_width=True):
                toggle_feature("home")
            if st.button("📝 프롬프트", key="btn_prompt", use_container_width=True):
                toggle_feature("prompt")
            if st.button("📄 문서", key="btn_document", use_container_width=True):
                toggle_feature("document")

        with feature_col2:
            if st.button("📧 이메일", key="btn_email", use_container_width=True):
                toggle_feature("email")
            if st.button("📊 분석", key="btn_analysis", use_container_width=True):
                toggle_feature("analysis")
            st.button("🔍 검색", key="btn_search", use_container_width=True, disabled=True)

        st.divider()

        # 프로세스 대시보드
        st.markdown("#### ⚡ 프로세스 대시보드")
        proc = st.session_state.get("current_process")
        if proc:
            progress = proc.get("progress", 0.0)
            if not isinstance(progress, (int, float)) or not (0.0 <= progress <= 1.0):
                progress = 0.0
            st.info(proc.get("desc", "진행 중 작업"))
            st.progress(progress)
        else:
            st.caption("진행 중인 작업 없음")

        st.divider()

        # (옵션) 간단 로그 표시
        logs = (state or {}).get("logs") if state else None
        if logs:
            st.subheader("🪵 로그")
            for line in logs[-100:]:
                st.text(line)

        # 고정 푸터 및 버튼 강조 스타일
        st.markdown("<div style='position: fixed; bottom: 20px; font-size: 0.8rem;'>© 2025 My AI Agent</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <style>
            button#btn_document.feature-button{background-color:#e1f5fe;border:2px solid #2196f3;color:#1976d2;font-weight:bold;}
            button#btn_chatbot.feature-button{background-color:#e1f5fe;border:2px solid #2196f3;color:#1976d2;font-weight:bold;}
            </style>
            """,
            unsafe_allow_html=True,
        )
