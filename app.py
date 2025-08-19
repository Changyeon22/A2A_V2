#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
My AI Agent - 멀티 에이전트 AI 시스템

음성 인식, 이메일 처리, 기획서 작성 등 다양한 AI 기능을 제공하는 
통합 에이전트 시스템의 메인 Streamlit 애플리케이션입니다.
"""

# CACHE_INVALIDATION_TOKEN: f8a9d2c35e17_20250708_1620
# 위 토큰은 Streamlit 캐시를 강제로 무효화하기 위한 것입니다.

import sys
import os
import base64
import streamlit as st
import speech_recognition as sr
import threading
import time
import datetime
import shutil
from ui.chat import render_chat_ui
from ui.sidebar import render_sidebar
from ui.analysis import render_analysis_ui
from ui.document import render_document_ui
from ui.email import render_email_ui
from ui.common import init_session_state, play_audio_autoplay_hidden, save_uploaded_file
from ui.voice import start_continuous_voice_recognition, stop_continuous_voice_recognition

# 프로젝트 모듈 임포트를 위한 경로 설정
current_script_dir = os.path.dirname(os.path.abspath(__file__))
if current_script_dir not in sys.path:
    sys.path.insert(0, current_script_dir)

# 하위 모듈 경로 추가
for subdir in ["tools", "ui_components", "agents"]:
    subdir_path = os.path.join(current_script_dir, subdir)
    if subdir_path not in sys.path:
        sys.path.insert(0, subdir_path)

# 설정 및 로깅 초기화
from config import config
from logging_config import setup_logging, get_logger
from configs.prompt_loader import get_prompt_text

# --- 세션 상태 초기화 ---
init_session_state()

# 로깅 설정
setup_logging(log_level=config.LOG_LEVEL, log_dir=config.LOG_DIR)
logger = get_logger(__name__)

# 필수 환경 변수 검증
try:
    config.validate_required_keys()
    logger.info("환경 변수 검증 완료")
except ValueError as e:
    logger.error(f"환경 변수 오류: {e}")
    st.error(f"환경 변수 설정 오류: {e}")
    st.stop()

import assistant_core
from ui_components.display_helpers import (
    show_message, show_spinner_ui, show_ai_response, 
    show_download_button, show_voice_controls, apply_custom_css,
    play_audio_with_feedback, show_voice_status
)
from tools.voice_tool.core import speech_to_text_from_mic_data
from tools.planning_tool.core import execute_create_new_planning_document
from tools.planning_tool.core import execute_collaboration_planning
from tools.planning_tool.core import execute_expand_notion_document
from tools.planning_tool.configs import personas, DOCUMENT_TEMPLATES
from tools.email_tool import get_daily_email_summary, get_email_details
from agents.email_agent import EmailAgent, MailAnalysisAgent
from agents.agent_protocol import AgentMessage, MessageType
from ui_components.prompt_ui import render_prompt_automation_ui, render_prompt_history
# 데이터 분석 도구 import
try:
    from tools.data_analysis import DataAnalysisTool, ChartGenerator, InsightExtractor
    DATA_ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"데이터 분석 도구 import 실패: {e}")
    DATA_ANALYSIS_AVAILABLE = False
import uuid
from tools.notion_utils import upload_to_notion
from personas.repository import PersonaRepository

# --- Streamlit 페이지 설정 ---
st.set_page_config(
    page_title="AI 기획 비서", 
    layout="wide", 
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# CSS 스타일 적용
apply_custom_css()

def process_user_text_input(text_input: str):
    if not text_input.strip():
        st.warning("내용이 없는 메시지는 처리할 수 없습니다.")
        return
        
    # 대화 기록 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # 사용자 메시지 저장 (UI 표시는 채팅 컨테이너에서 처리)
    st.session_state.messages.append({"role": "user", "content": text_input})
    
    # 상태 표시 컨테이너 생성
    status_container = st.empty()
    
    # --- 진행상황 대시보드 연동: LLM 작업 시작 ---
    st.session_state["current_process"] = {"type": "llm", "desc": "LLM 입력 분석 중...", "progress": 0.1}
    with show_spinner_ui("🤔 생각 중..."):
        # 1단계: 입력 분석
        st.session_state["current_process"]["desc"] = "LLM 입력 분석 중..."
        st.session_state["current_process"]["progress"] = 0.1
        # 2단계: 대화 이력 준비
        st.session_state["current_process"]["desc"] = "대화 이력 준비 중..."
        st.session_state["current_process"]["progress"] = 0.3
        conversation_history = []
        for msg in st.session_state.messages:
            if msg["role"] in ["user", "assistant"]:
                if "voice_text" in msg and "detailed_text" in msg:
                    conversation_history.append({"role": msg["role"], "content": msg["detailed_text"]})
                elif "content" in msg:
                    conversation_history.append({"role": msg["role"], "content": msg["content"]})
        # --- 챗봇 파일 업로드 context 전달 ---
        file_context = None
        if "chatbot_uploaded_file" in st.session_state and st.session_state["chatbot_uploaded_file"]:
            file_context = {"uploaded_file": st.session_state["chatbot_uploaded_file"]}
        # 3단계: LLM 응답 대기 (context 전달)
        st.session_state["current_process"]["desc"] = "LLM 응답 대기 중..."
        st.session_state["current_process"]["progress"] = 0.5
        # 컨텍스트 구성: 업로드 파일 + 선택된 페르소나(있을 경우)
        ctx = {}
        if file_context:
            ctx.update(file_context)
        selected_persona = st.session_state.get("selected_persona")
        if selected_persona:
            ctx["persona"] = selected_persona
        # 실제 호출
        response = assistant_core.process_command_with_llm_and_tools(text_input, conversation_history, context=ctx or None)
        # 4단계: LLM 응답 처리
        st.session_state["current_process"]["desc"] = "LLM 응답 처리 중..."
        st.session_state["current_process"]["progress"] = 0.8
        
        # 디버깅을 위해 응답 로그 출력
        # 바이너리 데이터 로깅 방지 - 응답 내용을 안전하게 출력
        safe_response = {}
        for key, value in response.items():
            if key == "audio_content" and isinstance(value, bytes):
                safe_response[key] = f"[Binary audio data of length: {len(value)} bytes]"
            else:
                safe_response[key] = value
        print(f"\n[DEBUG] LLM Response: {safe_response}\n")
        
        if response.get("status") == "success":
            # 응답 타입 확인
            if response.get("response_type") == "audio_response":
                # 음성 및 상세 텍스트 처리
                voice_text = response.get("voice_text", "")
                detailed_text = response.get("detailed_text", voice_text)
                audio_content = response.get("audio_content", None)
                
                # 디버깅 정보 출력 - 바이너리 데이터 로깅 방지 개선
                print(f"\n[DEBUG] Voice Text: {voice_text[:50] if voice_text else 'None'}...\n")
                print(f"\n[DEBUG] Detailed Text: {detailed_text[:50] if detailed_text else 'None'}...\n")
                if isinstance(audio_content, bytes):
                    print(f"\n[DEBUG] Audio Content: Binary data of length {len(audio_content)} bytes\n")
                else:
                    print(f"\n[DEBUG] Audio Content Type: {type(audio_content)}\n")
                
                # 대화 기록에 저장 (UI 표시는 채팅 컨테이너에서 처리)
                if voice_text:
                    # 오디오가 있는 경우 먼저 메시지를 추가
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "voice_text": voice_text,
                        "detailed_text": detailed_text
                    })
                    
                    # 오디오 자동 재생 (UI 없음)
                    if audio_content and isinstance(audio_content, bytes):
                        play_audio_autoplay_hidden(audio_content)
                    else:
                        st.warning("💬 텍스트 응답만 가능합니다. (오디오 생성 실패)")
                else:
                    st.error("어시스턴트 응답 생성 오류")
                    print(f"\n[DEBUG] ERROR: Empty voice_text in audio_response\n")
            
            # text_fallback 응답 타입 처리
            elif response.get("response_type") == "text_fallback" and response.get("text_content"):
                text_content = response.get("text_content")
                print(f"\n[DEBUG] Text Fallback Content: {text_content[:50]}...\n")
                
                # 대화 기록에 저장 (UI 표시는 채팅 컨테이너에서 처리)
                st.session_state.messages.append({
                    "role": "assistant",
                    "voice_text": text_content,
                    "detailed_text": text_content
                })
            
            else:
                # 일반 텍스트 응답
                message = response.get("message", "") or response.get("response", "") or response.get("text_content", "응답이 없습니다.")
                print(f"\n[DEBUG] Text Response Message: {message}\n")
                
                # 대화 기록에 저장 (UI 표시는 채팅 컨테이너에서 처리)
                st.session_state.messages.append({"role": "assistant", "content": message})
        else:
            # 오류 응답 처리
            error_msg = response.get("message", "") or response.get("response", "처리 중 알 수 없는 오류가 발생했습니다.")
            st.error(f"오류: {error_msg}")
            print(f"\n[DEBUG] ERROR Response: {error_msg}\n")
    # --- 진행상황 대시보드 연동: LLM 작업 종료 ---
    st.session_state["current_process"] = None

    # 페이지 리로드하여 새 메시지가 표시되도록 함
    # st.rerun() 호출하지 않음

 

# 스타일은 ui_components.display_helpers.apply_custom_css()에서 중앙 관리됩니다.

# --- 사이드바 UI 구성 ---
render_sidebar({})

# --- (보류) 신규 챗봇 탭 구현: 현재는 사용하지 않음 (향후 실험용으로 'chatbot_new' 키 사용) ---
if st.session_state.get("active_feature") == "chatbot_new":
    st.markdown("#### 💬 챗봇")
    # 업로드: 챗봇 문맥 파일
    up = st.file_uploader("챗봇이 참고할 파일 업로드", type=["txt","md","csv","json","xlsx","xls","pdf","docx"], help="텍스트/표 위주 파일 권장")
    if up is not None:
        try:
            saved = save_uploaded_file(up)
            st.session_state["chatbot_uploaded_file"] = {"path": saved, "name": up.name, "mime": getattr(up, "type", "")}
            st.success(f"업로드됨: {saved}")
        except Exception as e:
            st.error(f"파일 저장 실패: {e}")
    # 대화 표시
    with st.container():
        for msg in st.session_state.get("messages", []):
            if msg.get("role") == "user" and msg.get("content"):
                st.markdown(f"<div class='user-message'>{msg['content']}</div>", unsafe_allow_html=True)
            elif msg.get("role") == "assistant":
                if "voice_text" in msg or "detailed_text" in msg:
                    txt = msg.get("detailed_text") or msg.get("voice_text")
                    st.markdown(f"<div class='assistant-message'>{txt}</div>", unsafe_allow_html=True)
                elif msg.get("content"):
                    st.markdown(f"<div class='assistant-message'>{msg['content']}</div>", unsafe_allow_html=True)
    # 입력창 및 전송
    user_text = st.text_area("메시지 입력", key="chat_text_input", placeholder="메시지를 입력하세요...")
    col_s, col_b = st.columns([4,1])
    with col_b:
        if st.button("전송", type="primary"):
            process_user_text_input(user_text or "")



if st.session_state.get("active_feature") == "document":
    try:
        render_document_ui()
    except Exception as e:
        import traceback
        st.error("문서 UI 렌더링 중 오류가 발생했습니다.")
        st.exception(e)
        # 추가 디버깅 로그
        try:
            print("[Document UI Error]", e)
            print(traceback.format_exc())
        except Exception:
            pass

 

# --- 데이터 분석 탭 구현 (모듈화 UI만 사용) ---
if st.session_state.get("active_feature") == "analysis":
    try:
        render_analysis_ui()
    except Exception as e:
        st.error("데이터 분석 UI 렌더링 중 오류가 발생했습니다.")
        st.exception(e)

# --- 이메일 탭 개선: 모듈화 렌더러 사용 ---
if st.session_state.get("active_feature") == "email":
    try:
        render_email_ui()
    except Exception as e:
        st.error("이메일 UI 렌더링 중 오류가 발생했습니다.")
        st.exception(e)

# --- 프롬프트 자동화 UI ---
if st.session_state.get("active_feature") == "prompt":
    render_prompt_automation_ui()
    render_prompt_history()

# --- 메인 UI 레이아웃 (홈/디폴트: 모듈화된 레거시 챗봇 UI) ---
if st.session_state.get("active_feature") in [None, "home"]:
    # 메인 챗 UI만 렌더링 (사이드바는 상단에서 이미 한 번 렌더)
    render_chat_ui({})

# --- 오디오 자동 재생 함수 ---
def play_audio_in_browser(audio_bytes: bytes):
    """
    주어진 오디오 바이트를 브라우저에서 자동 재생합니다.
    """
    if not audio_bytes:
        return
    try:
        # (audio_html 및 st.markdown(audio_html, ...) 코드 완전 삭제)
        pass
    except Exception as e:
        st.error(f"음성 재생 중 오류 발생: {e}")

# --- 음성 인식 토글 상태 확인 및 처리 ---
if st.session_state.voice_recognition_active:
    # 토글이 켜져 있으면 음성 인식 스레드 시작
    start_continuous_voice_recognition()
else:
    # 토글이 꺼져 있으면 음성 인식 중지 시도
    if "voice_thread" in st.session_state and st.session_state.voice_thread and st.session_state.voice_thread.is_alive():
        stop_continuous_voice_recognition()

def main():
    """
    애플리케이션 메인 함수
    
    이 함수는 앱이 직접 실행될 때 호출됩니다.
    Streamlit은 이미 모든 UI 로직을 실행하므로 여기서는 
    추가적인 초기화나 설정 작업을 수행할 수 있습니다.
    """
    logger.info(f"{config.APP_NAME} v{config.APP_VERSION} 시작됨")
    
    # 캐시 무효화를 위한 타임스탬프 기록
    _cache_invalidation_time = time.time()
    
    # 브라우저에 직접 스크립트 삽입
    st.markdown("""
    <script>
    // 브라우저 캐시 강제 초기화
    if (window.localStorage) {
        // 마지막 초기화 시간 확인
        const lastReset = localStorage.getItem('streamlit_cache_reset');
        const now = Date.now();
        
        // 24시간마다 캐시 초기화 (86400000 밀리초)
        if (!lastReset || (now - parseInt(lastReset)) > 3600000) {
            console.log('Forcing cache reset...');
            localStorage.clear();
            sessionStorage.clear();
            localStorage.setItem('streamlit_cache_reset', now.toString());
            // 화면 새로고침
            setTimeout(() => { location.reload(true); }, 100);
        }
    }
    </script>
    """, unsafe_allow_html=True)
    
    # 애플리케이션 시작 시 추가 설정이나 검증 작업을 여기에 추가할 수 있습니다
    if config.is_development():
        logger.debug("개발 모드에서 실행 중")

if __name__ == "__main__":
    main()