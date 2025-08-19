# ui/actions.py
# -*- coding: utf-8 -*-
"""
UI 액션 디스패처 모듈.
Streamlit 이벤트에서 앱 코어 호출을 일원화합니다.
"""
from typing import Any, Dict, Optional

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


def _append_user_message(text: str) -> None:
    if st is None:
        return
    st.session_state.setdefault("messages", [])
    st.session_state.messages.append({"role": "user", "content": text})


def _append_assistant_message(text: str, voice_text: Optional[str] = None, detailed_text: Optional[str] = None) -> None:
    if st is None:
        return
    st.session_state.setdefault("messages", [])
    if voice_text is not None and detailed_text is not None:
        # 상세 텍스트를 기본 content로 저장하여 LLM 히스토리로 전달 가능하게 유지
        st.session_state.messages.append({
            "role": "assistant",
            "voice_text": voice_text,
            "detailed_text": detailed_text,
            "content": detailed_text or voice_text or text or "",
        })
    else:
        st.session_state.messages.append({"role": "assistant", "content": text})


def handle_chat_submit(user_input: str) -> None:
    """챗 입력 전송 처리: 코어 호출 및 메시지 기록.

    - 업로드된 파일이 있으면 컨텍스트에 포함.
    - assistant_core.process_command_with_llm_and_tools() 호출을 시도.
    """
    if not user_input or st is None:
        return

    _append_user_message(user_input)

    # 파일 컨텍스트 구성 (app.py 저장 규약 사용)
    file_ctx = st.session_state.get("chatbot_uploaded_file")

    try:
        import assistant_core  # 앱 코어
        # 코어에 전달할 컨텍스트 구성 및 대화 히스토리 수집
        context: Dict[str, Any] = {
            "uploaded_file": file_ctx  # {path,name,mime} 형태 또는 None
        }
        # LLM 호환 히스토리로 변환 (content가 None인 항목 제거/대체)
        raw_history = st.session_state.get("messages", [])
        conversation_history = []
        for m in raw_history:
            role = m.get("role")
            content = m.get("content") or m.get("detailed_text") or m.get("voice_text")
            if role in ("user", "assistant") and content is not None:
                conversation_history.append({"role": role, "content": str(content)})
        # 올바른 시그니처로 호출: (command_text, conversation_history, context)
        result = assistant_core.process_command_with_llm_and_tools(
            user_input,
            conversation_history,
            context=context,
        )
        # 결과 처리(간단화): content/voice_text/detailed_text 우선순위
        if isinstance(result, dict):
            if result.get("voice_text") and result.get("detailed_text"):
                _append_assistant_message("", voice_text=result["voice_text"], detailed_text=result["detailed_text"])
            else:
                text = result.get("content") or result.get("message") or str(result)
                _append_assistant_message(text)
        else:
            _append_assistant_message(str(result))
    except Exception as e:
        # 코어 호출 실패 시 에러 메시지로 대체
        err = f"코어 처리 중 오류: {e}"
        _append_assistant_message(err)
        if st is not None:
            st.error(err)
