# ui_components/display_helpers.py

import streamlit as st
import time
import base64

# === 스타일 시트 정의 ===
def apply_custom_css():
    """
    애플리케이션 전체에 적용될 커스텀 CSS 스타일을 정의합니다.
    """
    st.markdown("""
    <style>
        /* 기본 스타일 - 앱 레이아웃에 영향을 주지 않는 요소만 포함 */
        
        /* 오디오 웨이브 애니메이션 */
        .audio-wave { display: flex; align-items: center; gap: 2px; height: 16px; margin-top: 8px; }
        .audio-wave span { display: inline-block; width: 3px; height: 8px; background-color: #3B82F6; }
        .audio-wave span:nth-child(1) { animation: wave 1s infinite ease-in-out; }
        .audio-wave span:nth-child(2) { animation: wave 1s infinite ease-in-out 0.1s; }
        .audio-wave span:nth-child(3) { animation: wave 1s infinite ease-in-out 0.2s; }
        .audio-wave span:nth-child(4) { animation: wave 1s infinite ease-in-out 0.3s; }
        @keyframes wave { 0%, 100% { transform: scaleY(0.3); } 50% { transform: scaleY(1); } }
        
        /* 상태 표시기 스타일 */
        .status-indicator { display: flex; align-items: center; font-size: 14px; }
        .status-indicator .dot { margin-left: 4px; }
        .blinking { animation: blink 1.5s infinite; }
        @keyframes blink { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
        
        /* 음성 응답 스타일 */
        .voice-response { font-size: 16px; line-height: 1.6; }
        
        /* 상세 정보 카드 스타일 */
        .detail-section { border-left: 3px solid #3B82F6; padding-left: 12px; margin-top: 12px; }

        /* === Gemini 스타일 전역 CSS (app.py에서 중앙화) === */
        /* 전체 페이지 레이아웃 */
        .block-container {
            max-width: 900px !important;
            padding-top: 1rem !important;
            padding-bottom: 0 !important;
        }

        /* 헤더 영역 스타일 */
        .main-header {
            text-align: center;
            padding: 5px 0;
            margin-bottom: 10px;
            border-bottom: 1px solid #eee;
        }

        /* 채팅 컨테이너 - 투명 배경, 높이 확장 */
        .chat-container {
            max-width: 900px;
            margin: 0 auto;
            height: auto !important;
            padding: 10px;
            margin-bottom: 10px;
            background-color: transparent;
        }

        /* 입력 컨테이너 - 투명 배경 */
        .input-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 5px 0;
            background-color: transparent;
        }

        /* 메시지 스타일링 */
        .user-message, .assistant-message {
            margin-bottom: 15px;
            padding: 12px 18px;
            border-radius: 18px;
            max-width: 80%;
            line-height: 1.5;
        }

        .user-message {
            background-color: #e1f5fe;
            margin-left: auto;
            margin-right: 0;
            color: #0277bd;
        }

        .assistant-message {
            background-color: #f1f1f1;
            margin-left: 0;
            margin-right: auto;
            color: #424242;
        }

        /* 메시지 입력 영역 스타일 */
        .stTextArea textarea {
            resize: none;
            padding: 12px;
            font-size: 16px;
            border-radius: 24px;
            border: 1px solid #ddd;
            height: 70px !important;
            box-shadow: none;
        }

        /* Streamlit 기본 요소 조정 */
        .stApp header { display: none; }
        .stApp footer { display: none; }

        /* 스크롤바 제거 - 전역적으로 적용 */
        ::-webkit-scrollbar { display: none !important; width: 0 !important; height: 0 !important; }
        body, .main, .stApp, section[data-testid="stSidebar"] {
            scrollbar-width: none !important;
            -ms-overflow-style: none !important;
        }

        /* 추가 Gemini 스타일 요소 */
        .chat-wrapper { display: flex; flex-direction: column; height: 100%; }

        /* 사이드바 조정 - 원래 상태로 롤백 */
        section[data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #eee; }

        /* 불필요한 여백 제거 */
        div.stButton > button { margin-top: 0; }

        /* 모든 컨테이너 투명화 */
        div.css-1kyxreq.e115fcil2, div.css-1y4p8pa.e1g8pov61, 
        div.block-container > div, div[data-testid="stVerticalBlock"] > div,
        div.stTextArea, div.stTextInput {
            border: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
        }

        /* 컨테이너 내부 패딩 조정 */
        div.block-container { padding: 0 !important; }

        /* 전체 컨텐츠 영역 마진 축소 */
        div[data-testid="stAppViewContainer"] > div { margin: 0 !important; }

        /* 기타 Streamlit 요소 투명화 */
        .css-ffhzg2, .css-10trblm, .css-zt5igj, .css-16idsys, 
        .css-90vs21, .css-1p8k8ky { background-color: transparent !important; }

        /* 모든 카드형 UI 요소 투명화 */
        div[data-testid="stDecoration"], div[data-testid="stToolbar"],
        div[data-testid="stCaptionContainer"], div.stMarkdown,
        div.stForm {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* 버튼 스타일 개선 */
        button[kind="primaryFormSubmit"] { border-radius: 20px !important; }

        /* 텍스트 영역 마진 제거 */
        div.stMarkdown { margin: 0 !important; padding: 0 !important; }

        /* 입력 버튼 위치 조정 */
        button[data-testid="baseButton-secondary"] { margin-top: 8px !important; }

        /* 음성 상태 표시 영역 */
        .voice-status-area {
            padding: 5px 10px;
            margin-bottom: 10px;
            border-radius: 8px;
            background-color: rgba(240, 242, 246, 0.4);
        }

        /* 오디오 플레이어 스타일 */
        audio { display: block !important; width: 100% !important; margin: 10px 0 !important; }

        /* 스트림릿 오디오 플레이어 컨테이너 스타일 수정 */
        div[data-testid="stAudio"] { margin: 10px 0 !important; background-color: transparent !important; }

        /* 스트림릿 오디오 요소의 부모 컨테이너 스타일 수정 */
        div.element-container div { background-color: transparent !important; }

        /* 마진 제거 및 최소 여백 적용 */
        .element-container, .stAudio, .stAlert { margin: 0 !important; padding: 0 !important; }
    </style>
    """, unsafe_allow_html=True)

def show_message(role: str, message: str):
    """
    Streamlit 채팅 인터페이스에 메시지를 표시합니다.
    Args:
        role (str): 'user' 또는 'assistant'.
        message (str): 표시할 메시지 내용.
    """
    with st.chat_message(role):
        st.markdown(message)

def show_ai_response(role: str, voice_text: str, detailed_text: str = None):
    """
    현대적인 AI 챗봇 UI 스타일로 응답을 표시합니다.
    
    Args:
        role (str): 메시지 역할 ('assistant')
        voice_text (str): 음성으로 전달되는 간결한 텍스트
        detailed_text (str): UI에 표시될 상세한 텍스트 (선택적)
    """
    with st.chat_message(role):
        # 1. 주요 답변 (음성으로도 전달되는 내용)
        st.markdown(f'<div class="voice-response">{voice_text}</div>', unsafe_allow_html=True)
        
        # 2. 상세 정보가 있고 음성 답변과 다른 경우에만 추가 정보 표시
        if detailed_text and detailed_text != voice_text:
            with st.expander("📑 상세 정보 및 추가 자료", expanded=False):
                st.markdown(detailed_text)

def show_spinner_ui(text: str):
    """
    Streamlit UI에 스피너(로딩 애니메이션)를 표시합니다.
    Args:
        text (str): 스피너와 함께 표시할 메시지.
    Returns:
        streamlit.spinner: with 문과 함께 사용될 스피너 객체.
    """
    return st.spinner(text)

def show_voice_status(status: str = "idle", message: str = ""):
    """
    음성 인식 상태를 표시하는 HTML을 생성합니다.
    
    Args:
        status (str): 상태 코드 ('idle', 'listening', 'processing', 'error')
        message (str): 표시할 메시지
    
    Returns:
        str: HTML 문자열 (unsafe_allow_html=True와 함께 사용해야 함)
    """
    status_color = {
        "idle": "#6c757d", # 회색
        "listening": "#28a745", # 초록색
        "processing": "#007bff", # 파란색
        "error": "#dc3545" # 빨간색
    }.get(status, "#6c757d")
    
    icon = {
        "idle": "🔇",
        "listening": "🎤",
        "processing": "⏳",
        "error": "⚠️"
    }.get(status, "🔇")
    
    dots_html = "" if status != "listening" else "<span class='dot blinking'>.</span><span class='dot blinking'>.</span><span class='dot blinking'>.</span>"
    
    html = f"""
    <div class="status-indicator" style="color: {status_color}">
        {icon} {message} {dots_html}
    </div>
    """
    
    return html

def play_audio_with_feedback(audio_bytes: bytes, container=None):
    """
    오디오를 재생하고 시각적 피드백을 표시합니다.
    
    Args:
        audio_bytes (bytes): 재생할 오디오 바이트
        container: 상태를 표시할 Streamlit 컨테이너 (선택적)
    """
    if not audio_bytes:
        return
        
    # 컨테이너가 없으면 새로 생성
    display_container = container if container else st.empty()
    
    try:
        # 음성 재생 상태 표시
        display_container.markdown("""
            <div style="text-align: right; margin-top: 4px; margin-bottom: 8px;">
                <div class="audio-wave">
                    <span></span><span></span><span></span><span></span>
                    <small style="margin-left: 6px; color: #3B82F6;">음성 재생 중</small>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 오디오 태그 생성 및 재생 - controls 속성을 표시하여 사용자가 제어할 수 있게 함
        audio_base64 = base64.b64encode(audio_bytes).decode()
        audio_html = f"""
            <audio autoplay controls style="display: block !important; width: 100%; margin-top: 10px;">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
                브라우저가 오디오 재생을 지원하지 않습니다.
            </audio>
        """
        st.audio(audio_bytes, format="audio/mp3")
        
        # 상태 표시를 유지 (재생이 끝나도 컨트롤은 그대로 유지)
    except Exception as e:
        st.error(f"음성 재생 중 오류: {e}")
        display_container.empty()

def show_download_button(content: str, filename: str, mime_type: str = "text/plain", label: str = "다운로드"):
    """
    다운로드 버튼을 표시합니다.
    
    Args:
        content (str): 다운로드할 내용
        filename (str): 다운로드 파일명
        mime_type (str): MIME 타입 (기본값: "text/plain")
        label (str): 버튼 라벨 (기본값: "다운로드")
    """
    if isinstance(content, str):
        content_bytes = content.encode('utf-8')
    else:
        content_bytes = content
    
    b64_content = base64.b64encode(content_bytes).decode()
    
    st.download_button(
        label=label,
        data=content_bytes,
        file_name=filename,
        mime=mime_type,
        key=f"download_{filename}_{hash(content)}"
    )


def show_voice_controls():
    """
    음성 인식 제어 UI를 표시합니다.
    
    Returns:
        tuple: (음성_활성화_상태, 음성_입력_버튼_클릭_여부)
    """
    col1, col2 = st.columns([1, 3])
    
    with col1:
        voice_enabled = st.checkbox(
            "🎤 음성 인식", 
            key="voice_enabled",
            help="음성 인식 기능을 활성화합니다"
        )
    
    with col2:
        if voice_enabled:
            voice_input_clicked = st.button(
                "🎙️ 음성 입력 시작",
                key="voice_input_button",
                help="마이크로 음성을 입력합니다"
            )
        else:
            voice_input_clicked = False
            st.write("음성 인식이 비활성화되어 있습니다.")
    
    return voice_enabled, voice_input_clicked

# 이전 버전과의 호환성을 위한 함수
def show_dual_response(role: str, voice_text: str, detailed_text: str):
    """
    레거시 함수 - 이전 버전과의 호환성을 위해 유지합니다.
    향후 show_ai_response 함수로 대체될 예정입니다.
    """
    return show_ai_response(role, voice_text, detailed_text)