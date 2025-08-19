# ui/chat.py
# -*- coding: utf-8 -*-
"""
Streamlit 챗 UI 렌더러 모듈.
app.py의 비대를 줄이고, 재정의 오류를 방지하기 위해 UI 로직을 함수로 분리합니다.

본 모듈은 안전한 래퍼 수준으로 제공되며, 점진적으로 app.py에서 호출하도록 통합합니다.
"""
from typing import Any, Dict, Optional

try:
    import streamlit as st
    import streamlit.components.v1 as components
except Exception:  # pragma: no cover
    st = None  # 테스트/비-UI 환경 대응
    components = None

# 공용 UI/저장 헬퍼 사용으로 중복 제거
from ui_components.display_helpers import (
    show_voice_controls,
    show_ai_response,
    show_message,
)
from ui.common import save_uploaded_file


# 중복된 업로드 저장 유틸 제거 (_save_uploaded_file -> ui.common.save_uploaded_file 사용)


def render_chat_ui(state: Optional[Dict[str, Any]] = None) -> None:
    """레거시 챗봇 UI를 렌더링합니다.

    Args:
        state: 세션 상태(dict) 혹은 외부 상태
    """
    if st is None:
        return

    # 상단 고정 툴바 제거됨

    # 스크롤 가능한 로그(하위 레이어) + 상하단 입력/툴바를 상위 레이어(fixed overlay)로 올리는 CSS
    st.markdown(
        """
        <style>
        /* Streamlit 기본 패딩 축소 + 전체를 세로 플렉스 컨테이너로 전환 */
        section.main > div.block-container {
            padding-top: 1rem; padding-bottom: 1rem;
            display: flex; flex-direction: column; min-height: 100vh;
        }

        /* 오버레이가 상위 컨테이너의 overflow/transform에 의해 잘리지 않도록 보정 */
        #root, .main, section.main, section.main > div.block-container,
        div[data-testid="stAppViewContainer"], div[data-testid="stSidebar"] {
            overflow: visible !important;
            contain: none !important;
        }

        /* 상단 툴바 컨테이너: 마커를 포함하는 블록을 고정 */
        div:has(> .top-toolbar-marker) {
            position: fixed !important;
            top: 0; left: 0; right: 0;
            z-index: 2147483646 !important;
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: saturate(1.2) blur(10px);
            -webkit-backdrop-filter: saturate(1.2) blur(10px);
            border-bottom: 1px solid rgba(0,0,0,0.08);
            box-shadow: 0 8px 20px rgba(0,0,0,0.06);
        }
        [data-theme="dark"] div:has(> .top-toolbar-marker) {
            background: rgba(20, 20, 20, 0.7);
            border-bottom-color: rgba(255,255,255,0.12);
        }

        /* 상단 툴바 내부 컨텐츠의 가로 폭 정렬 */
        div:has(> .top-toolbar-marker) > div {
            max-width: 980px; margin: 0 auto; padding: 8px 16px 10px 16px;
        }

        /* 상단 툴바 제거: 기본 상단 패딩 최소화 */
        .chat-log-wrapper {
            padding-top: 12px;
        }

        /* 대화 로그: 상단/하단 UI 사이의 전용 레이어 (부모 플렉스에서 가변 높이) */
        .chat-log-wrapper {
            flex: 1 1 auto; /* 남는 공간을 차지 */
            min-height: 0;   /* 내부 스크롤이 동작하도록 필수 */
            overflow-y: auto;
            padding-right: 6px; /* 스크롤바와 콘텐츠 간 여백 */
            padding-bottom: 0; /* 하단 여백은 스페이서가 담당 */
            margin-bottom: 0;
            position: relative;
            z-index: 1; /* 입력 오버레이보다 아래 */
            scroll-behavior: smooth;
        }
        /* 필요시 화면 높이에 맞춰 조정: 300~360px 사이에서 조절하며 핏을 맞추세요 */

        /* 하단 입력 영역: 마커 포함 컨테이너를 오버레이로 고정 */
        div:has(> .bottom-input-overlay-marker) {
            position: fixed !important;
            left: 0; right: 0; bottom: 0;
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: saturate(1.2) blur(10px);
            -webkit-backdrop-filter: saturate(1.2) blur(10px);
            border-top: 1px solid rgba(0,0,0,0.08);
            box-shadow: 0 -8px 20px rgba(0,0,0,0.06);
            z-index: 2147483647 !important;
            padding: 6px 0; /* 전체 높이 축소 */
        }
        /* 하단 입력 컨텐츠 가로 폭 정렬 */
        div:has(> .bottom-input-overlay-marker) > div {
            max-width: 980px; margin: 0 auto; padding: 0 12px; /* 좌우 패딩 축소 */
        }
        [data-theme="dark"] div:has(> .bottom-input-overlay-marker) {
            background: rgba(20, 20, 20, 0.72);
            backdrop-filter: saturate(1.2) blur(10px);
            border-top-color: rgba(255,255,255,0.12);
        }

        /* 업로더 UI는 완전히 숨기되 기능은 유지 (오프스크린 렌더링 컨테이너) */
        div:has(> .bottom-input-overlay-marker) .uploader-hidden {
            position: absolute !important;
            width: 1px !important; height: 1px !important;
            overflow: hidden !important;
            clip: rect(0 0 0 0) !important;
            clip-path: inset(50%) !important;
            white-space: nowrap !important;
            border: 0 !important; padding: 0 !important; margin: -1px !important;
            pointer-events: none !important;
        }

        /* 하단 입력 내 파일 업로드: 드롭존/설명/회색 박스 숨기고 버튼만 보이게 */
        div:has(> .bottom-input-overlay-marker) [data-testid="stFileUploaderDropzone"],
        div:has(> .bottom-input-overlay-marker) .stFileUploader, /* 일부 버전 호환 */
        div:has(> .bottom-input-overlay-marker) div[role="button"][aria-label*="Drag and drop"] {
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
            min-height: auto !important;
        }
        /* 업로더 내 설명/파일타입 안내/보조 텍스트 제거 */
        div:has(> .bottom-input-overlay-marker) [data-testid="stFileUploader"] small,
        div:has(> .bottom-input-overlay-marker) [data-testid="stFileUploader"] p,
        div:has(> .bottom-input-overlay-marker) [data-testid="stFileUploaderInstructions"],
        div:has(> .bottom-input-overlay-marker) [data-testid="stFileUploaderFileTypes"],
        div:has(> .bottom-input-overlay-marker) [data-testid="UploadedFileName"] + small,
        div:has(> .bottom-input-overlay-marker) [aria-live="polite"],
        div:has(> .bottom-input-overlay-marker) [class*="uploadFileDetails"],
        div:has(> .bottom-input-overlay-marker) .st-bb, /* 회색 보더 박스 제거 */
        div:has(> .bottom-input-overlay-marker) .st-emotion-cache-1y4p8pa { /* 회색 박스 클래스 예시 */
            display: none !important;
        }
        /* 업로드 버튼을 콤팩트하게 */
        div:has(> .bottom-input-overlay-marker) [data-testid="stFileUploader"] button,
        div:has(> .bottom-input-overlay-marker) .stFileUploader button {
            padding: 0.35rem 0.6rem !important;
        }

        /* 전체 UI 축소: 업로더/음성/버튼/입력 폰트 및 간격 컴팩트화 */
        div:has(> .bottom-input-overlay-marker) * {
            font-size: 0.92rem;
        }
        /* 업로더 자체 스케일 축소 (크롬 기반에 효과적) */
        div:has(> .bottom-input-overlay-marker) [data-testid="stFileUploader"] {
            transform: scale(0.9);
            transform-origin: left center;
            display: inline-block;
        }
        /* 음성 컨트롤 영역도 약간 축소 */
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal,
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal * {
            font-size: 0.9rem !important;
        }
        /* 전송 버튼 컴팩트 */
        div:has(> .bottom-input-overlay-marker) button[kind="secondary"]:not([aria-label]),
        div:has(> .bottom-input-overlay-marker) .stButton > button {
            padding: 0.4rem 0.6rem !important;
        }

        /* 마이크 버튼 상태 시각 피드백 */
        div:has(> .bottom-input-overlay-marker) .voice-btn-wrapper .stButton > button {
            transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
        }
        div:has(> .bottom-input-overlay-marker) .voice-btn-wrapper.active .stButton > button {
            background-color: #ffeded !important;
            border-color: #ff7a7a !important;
            color: #c12424 !important;
        }

        /* 음성 인식 UI 최소화: 텍스트 설명 제거, 체크박스 라벨 텍스트 숨김, 마이크 버튼 아이콘만 */
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal p,
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal small,
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal label p,
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal label span,
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal [data-testid="stMarkdownContainer"] {
            display: none !important;
        }
        /* 마이크 버튼 텍스트 숨기고 아이콘만 출력 */
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal button {
            font-size: 0 !important;
            padding: 0.35rem 0.6rem !important;
        }
        div:has(> .bottom-input-overlay-marker) .voice-controls-minimal button::before {
            content: '🎙️';
            font-size: 1rem;
            line-height: 1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 대화 영역: 스크롤 가능한 하위 레이어 안에 메시지 렌더링
    st.session_state.setdefault("messages", [])
    messages = st.session_state.messages
    st.markdown('<div class="chat-log-wrapper" id="chat-log">', unsafe_allow_html=True)
    if messages:
        for message in messages[-50:]:
            role = message.get("role")
            if role == "system":
                continue
            if role == "user":
                show_message("user", message.get("content", ""))
            elif role == "assistant":
                if "voice_text" in message and "detailed_text" in message:
                    vt = message.get("voice_text", "")
                    dt = message.get("detailed_text", "")
                    show_ai_response("assistant", vt, dt)
                else:
                    show_message("assistant", message.get("content", ""))
    else:
        st.info("메시지를 입력하면 대화가 시작됩니다.")
    # 입력 폼과 겹침 방지를 위한 하단 스페이서 엘리먼트
    st.markdown('<div id="chat-bottom-spacer" style="height:200px"></div></div>', unsafe_allow_html=True)

    # 대화 로그가 렌더링된 후: 상/하단 오버레이 높이에 맞춰 동적 패딩 + 최신 로그 자동 스크롤
    try:
        if components is not None:
            components.html(
                """
                <script>
                (function(){
                  const doc = window.parent && window.parent.document;
                  if (!doc) return;

                  function adjustChatLogPadding() {
                    const log = doc.getElementById('chat-log');
                    if (!log) return;

                    // 상단 툴바: 마커(.top-toolbar-marker)의 부모 컨테이너
                    const marker = doc.querySelector('.top-toolbar-marker');
                    const toolbar = marker ? marker.parentElement : null;

                    // 하단 입력 오버레이: 마커(.bottom-input-overlay-marker)의 부모 컨테이너
                    const bottomMarker = doc.querySelector('.bottom-input-overlay-marker');
                    const bottomOverlay = bottomMarker ? bottomMarker.parentElement : null;

                    const topH = toolbar ? toolbar.getBoundingClientRect().height : 0;
                    const bottomH = bottomOverlay ? bottomOverlay.getBoundingClientRect().height : 0;

                    // 상단은 padding-top으로 확보
                    log.style.paddingTop = Math.ceil(topH) + 'px';

                    // 하단은 내부 스페이서로 확보 (padding-bottom 대신 스페이서 높이 설정)
                    const spacer = doc.getElementById('chat-bottom-spacer');
                    if (spacer) {
                      const extra = 16; // 여유 간격
                      spacer.style.height = Math.max(220, Math.ceil(bottomH + extra)) + 'px';
                    }
                  }

                  function scrollToLatest(center = true) {
                    const log = doc.getElementById('chat-log');
                    if (!log) return;
                    const items = Array.from(log.children).filter(el => el.id !== 'chat-bottom-spacer');
                    const last = items[items.length - 1];
                    if (!last) return;
                    if (!center) {
                      log.scrollTop = log.scrollHeight;
                      return;
                    }
                    // 마지막 아이템을 컨테이너 중앙에 오도록 위치 계산
                    const logRect = log.getBoundingClientRect();
                    const lastRect = last.getBoundingClientRect();
                    const lastTopInLog = (lastRect.top - logRect.top) + log.scrollTop;
                    const target = Math.max(0, Math.floor(lastTopInLog - (log.clientHeight/2 - last.clientHeight/2)));
                    log.scrollTop = target;
                  }

                  // 최초 적용
                  adjustChatLogPadding();
                  scrollToLatest();
                  // 초기 레이아웃 안정화 후 한 번 더 적용
                  setTimeout(() => { adjustChatLogPadding(); scrollToLatest(); }, 50);

                  // 창 리사이즈나 줌/폰트 변경 등 레이아웃 변화 대응
                  window.addEventListener('resize', () => {
                    adjustChatLogPadding();
                    // 리사이즈 후에도 최신 위치 유지
                    scrollToLatest(true);
                  });

                  // DOM 변화(테마/위젯 갱신 등) 감지하여 동적 패딩 재적용
                  const obs = new MutationObserver(() => {
                    adjustChatLogPadding();
                    scrollToLatest(true);
                  });
                  obs.observe(doc.body, { subtree: true, childList: true, attributes: true });
                })();
                </script>
                """,
                height=0,
            )
    except Exception:
        pass

    # 입력 영역: 하단 고정 오버레이 컨테이너 내부에 음성/업로드/입력/전송 배치
    with st.container():
        st.markdown('<div class="bottom-input-overlay-marker"></div>', unsafe_allow_html=True)

        # 업로더는 기능 유지용으로 화면 밖에 숨겨 렌더링
        with st.container():
            st.markdown('<div class="uploader-hidden">', unsafe_allow_html=True)
            chatbot_uploaded_file = st.file_uploader(
                label="파일 업로드",
                type=['txt','md','csv','json','xlsx','xls','pdf','docx'],
                key='chatbot_file_uploader_bottom',
                label_visibility='collapsed',
            )
            st.markdown('</div>', unsafe_allow_html=True)
            if chatbot_uploaded_file is not None:
                try:
                    saved = save_uploaded_file(chatbot_uploaded_file)
                    st.session_state['chatbot_uploaded_file'] = {
                        "path": saved,
                        "name": getattr(chatbot_uploaded_file, 'name', ''),
                        "mime": getattr(chatbot_uploaded_file, 'type', ''),
                    }
                except Exception as e:
                    st.error(f"파일 저장 실패: {e}")

        # 1행: [음성] [메시지 입력] [전송] (업로더 UI 제거)
        cols = st.columns([1, 6, 1.2])
        with cols[0]:
            # 음성 제어: 마이크 아이콘 버튼 시각 피드백 및 토글
            st.session_state.setdefault("voice_recognition_active", False)
            is_active = bool(st.session_state.voice_recognition_active)
            mic_label = "🔴🎙️" if is_active else "🎙️"
            wrapper_class = "voice-btn-wrapper active" if is_active else "voice-btn-wrapper"
            st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
            voice_clicked = st.button(mic_label, key="voice_mic_click", help="마이크")
            st.markdown('</div>', unsafe_allow_html=True)
            if voice_clicked:
                st.session_state.voice_recognition_active = not st.session_state.voice_recognition_active
                st.rerun()
        with cols[1]:
            # 메시지 입력
            user_input = st.text_area(
                label="메시지",
                key="chat_input_text",
                height=80,
                label_visibility='collapsed',
                placeholder="메시지를 입력하세요..."
            )
        with cols[2]:
            submitted = st.button("전송", use_container_width=True)

        # 2행: 업로드 파일명/음성 상태 요약 (필요 시)
        meta_cols = st.columns([2, 6, 2])
        with meta_cols[0]:
            if st.session_state.get('chatbot_uploaded_file', {}).get('name'):
                st.caption(f"첨부: {st.session_state['chatbot_uploaded_file']['name']}")
        with meta_cols[2]:
            if st.session_state.get('voice_recognition_active'):
                st.caption("🎙️ 음성 인식 ON")

    if submitted and user_input:
        try:
            from ui.actions import handle_chat_submit
            handle_chat_submit(user_input)
            st.rerun()
        except Exception as e:
            st.error(f"메시지 전송 중 오류: {e}")
