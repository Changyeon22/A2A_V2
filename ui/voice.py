# ui/voice.py
# -*- coding: utf-8 -*-
"""
Streamlit 음성 인식 UI 및 헬퍼 함수 모듈.
기존 app.py의 음성 관련 함수를 모듈화하여 재사용성과 유지보수성을 개선합니다.
"""
from __future__ import annotations
from typing import Optional, Dict, Any

import threading

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # type: ignore

try:
    import speech_recognition as sr  # type: ignore
except Exception:  # pragma: no cover
    sr = None  # type: ignore

# 내부 음성 인식 함수 (tools)
try:
    from tools.voice_tool.core import speech_to_text_from_mic_data  # type: ignore
except Exception:  # pragma: no cover
    def speech_to_text_from_mic_data(audio):  # type: ignore
        return {"status": "error", "text": None, "error": "voice core not available"}


essential_warning = (
    "음성 인식을 위해서는 마이크 권한과 'speech_recognition' 패키지가 필요합니다."
)


def get_voice_input_once() -> Optional[str]:
    """단일 음성 입력을 가져옵니다. (버튼 입력용)"""
    if st is None or sr is None:
        return None
    status_placeholder = st.empty()
    r = sr.Recognizer()
    with sr.Microphone() as source:
        status_placeholder.info("🎤 마이크 설정 중... (주변 소음 측정)")
        try:
            r.adjust_for_ambient_noise(source, duration=0.5)
            status_placeholder.info("🔊 듣고 있어요... 말씀해주세요.")
            audio = r.listen(source, timeout=7, phrase_time_limit=15)
        except sr.WaitTimeoutError:  # type: ignore[attr-defined]
            status_placeholder.warning("⏰ 음성 입력 시간이 초과되었습니다.")
            return None
        except Exception as e:
            status_placeholder.error(f"⚠️ 마이크 오류: {e}")
            return None

    status_placeholder.info("🤖 음성 인식 중...")
    try:
        result = speech_to_text_from_mic_data(audio)
        if result and result.get("status") == "success" and result.get("text"):
            text = result.get("text")
            status_placeholder.success(f"✅ 인식됨: {text}")
            return str(text)
        else:
            status_placeholder.error("❓ 음성 인식 실패")
            return None
    except Exception as e:
        status_placeholder.error(f"⚠️ 인식 오류: {e}")
        return None


def start_continuous_voice_recognition() -> bool:
    """음성 인식을 지속적으로 감지하는 스레드를 시작합니다."""
    if st is None:
        return False
    if "voice_thread" not in st.session_state or not st.session_state.voice_thread or not st.session_state.voice_thread.is_alive():
        st.session_state.voice_recognition_active = True
        st.session_state.voice_thread = threading.Thread(target=continuous_voice_listener, daemon=True)
        st.session_state.voice_thread.start()
        return True
    return False


def stop_continuous_voice_recognition() -> bool:
    """음성 인식 스레드를 중지합니다."""
    if st is None:
        return False
    st.session_state.voice_recognition_active = False
    return True


def continuous_voice_listener() -> None:
    """백그라운드에서 음성을 지속적으로 듣고 처리하는 함수"""
    if st is None or sr is None:
        return
    # 상태 표시
    voice_status_container = st.container()
    with voice_status_container:
        voice_status_placeholder = st.empty()
        voice_status_placeholder.markdown('<div class="voice-status-area"></div>', unsafe_allow_html=True)

    r = sr.Recognizer()
    r.pause_threshold = 1.0
    r.energy_threshold = 1000

    while st.session_state.get("voice_recognition_active", False):
        try:
            with sr.Microphone() as source:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
            result = speech_to_text_from_mic_data(audio)
            text = result.get("text") if isinstance(result, dict) else None
            if text:
                st.session_state.last_voice_text = str(text)
        except sr.WaitTimeoutError:  # no speech
            continue
        except Exception:
            continue


# Optional simple UI renderer for voice controls

def render_voice_ui() -> None:
    if st is None:
        return
    st.subheader("음성 인식")
    if sr is None:
        st.warning(essential_warning)
        return

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("한 번 녹음"):
            text = get_voice_input_once()
            if text:
                st.success(f"인식: {text}")
    with col2:
        if st.button("지속 인식 시작"):
            if start_continuous_voice_recognition():
                st.info("지속 인식을 시작했습니다.")
    with col3:
        if st.button("지속 인식 중지"):
            if stop_continuous_voice_recognition():
                st.info("지속 인식을 중지했습니다.")

    if st.session_state.get("last_voice_text"):
        st.markdown("### 최근 인식 결과")
        st.write(st.session_state.get("last_voice_text"))
