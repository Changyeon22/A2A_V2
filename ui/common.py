# -*- coding: utf-8 -*-
"""
ui.common

Streamlit UI 공용 헬퍼와 세션 상태 초기화 유틸
"""
from __future__ import annotations
import os
import base64
import streamlit as st
from typing import Any, Dict, List, Optional

# 프로젝트 루트 경로 보정 (직접 실행과 모듈 임포트 모두 지원)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.abspath(os.path.join(_current_dir, os.pardir))
if _root_dir not in os.sys.path:
    os.sys.path.insert(0, _root_dir)

from configs.prompt_loader import get_prompt_text


def init_session_state() -> None:
    """앱 전역 세션 상태 초기화 및 시스템 프롬프트 세팅."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        default_system = (
            "You are an expert AI Planning Assistant. Your primary goal is to help users develop comprehensive and actionable "
            "plans for various projects, with a special focus on game development and IT projects.\n\n"
            "Key Responsibilities:\n"
            "- Analyze user requests to understand their planning needs.\n"
            "- Break down complex goals into manageable tasks and phases.\n"
            "- Help define project scope, objectives, deliverables, and timelines.\n"
            "- Identify potential risks and suggest mitigation strategies.\n"
            "- Utilize available tools to create, modify, or retrieve planning documents (e.g., from Notion).\n"
            "- Maintain a professional, clear, and helpful tone.\n"
            "- If a user's request is ambiguous or lacks detail, ask clarifying questions to ensure a thorough understanding before proceeding.\n"
            "- When providing plans or analysis, aim for clarity, conciseness, and actionable insights.\n"
            "- Explain your reasoning step-by-step if the query is complex or if you are about to use a tool.\n\n"
            "Constraints:\n"
            "- Only use the provided tools when necessary and appropriate for the user's request.\n"
            "- Do not make up information if it's not available through tools or your general knowledge.\n"
            "- Adhere to the structure and format requested by the user for any documents or plans.\n"
            "- All outputs should be in Korean unless explicitly requested otherwise by the user."
        )
        system_prompt_text = get_prompt_text('app_system', default_system)
        st.session_state["system_prompt"] = system_prompt_text
        st.session_state.messages.append({"role": "system", "content": system_prompt_text})
        st.session_state.messages.append({"role": "assistant", "content": "안녕하세요! AI 기획 비서입니다. 무엇을 도와드릴까요?"})

    if "text_input" not in st.session_state:
        st.session_state.text_input = ""

    if "voice_recognition_active" not in st.session_state:
        st.session_state.voice_recognition_active = False

    if "initial_greeting_played" not in st.session_state:
        st.session_state.initial_greeting_played = False

    if "active_feature" not in st.session_state:
        st.session_state.active_feature = None


def play_audio_autoplay_hidden(audio_bytes: bytes) -> None:
    """브라우저에서 숨김 자동재생 오디오 출력."""
    if not audio_bytes:
        return
    audio_base64 = base64.b64encode(audio_bytes).decode()
    audio_html = f"""
        <audio autoplay style="display:none">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)


def save_uploaded_file(uploaded_file) -> str:
    """업로드 파일을 날짜별 디렉터리에 저장 후 경로 반환."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    base_dir = os.path.join("files", today)
    os.makedirs(base_dir, exist_ok=True)
    filename = uploaded_file.name
    save_path = os.path.join(base_dir, filename)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path
