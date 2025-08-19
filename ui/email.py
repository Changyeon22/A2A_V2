# ui/email.py
# -*- coding: utf-8 -*-
"""
Streamlit 이메일 탭 렌더러 (메일 조회/분석/자동답장/첨부 추출).
기존 app.py의 이메일 관련 UI를 모듈화하여 유지보수성을 높입니다.
"""
from __future__ import annotations
from typing import Any, Dict, List

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore


def _lazy_imports():
    import datetime
    import uuid
    import pandas as pd  # type: ignore
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode  # type: ignore

    from tools.email_tool.core import (
        get_daily_email_summary,
        get_email_details,
        get_email_summary_on,
    )  # type: ignore
    from agents.email_agent import EmailAgent  # type: ignore
    from agents.agent_protocol import MessageType, AgentMessage  # type: ignore

    return (
        datetime,
        uuid,
        pd,
        AgGrid,
        GridOptionsBuilder,
        GridUpdateMode,
        get_daily_email_summary,
        get_email_details,
        get_email_summary_on,
        EmailAgent,
        MessageType,
        AgentMessage,
    )


def render_email_ui() -> None:
    if st is None:
        return

    (
        datetime,
        uuid,
        pd,
        AgGrid,
        GridOptionsBuilder,
        GridUpdateMode,
        get_daily_email_summary,
        get_email_details,
        get_email_summary_on,
        EmailAgent,
        MessageType,
        AgentMessage,
    ) = _lazy_imports()

    st.markdown("#### 메일 조회")
    if "selected_email_date" not in st.session_state:
        st.session_state.selected_email_date = datetime.date.today()
    selected_date = st.date_input("날짜 선택", value=st.session_state.selected_email_date, key="email_date_input")
    st.session_state.selected_email_date = selected_date

    # 메일 목록 조회
    st.session_state["current_process"] = {"type": "email", "desc": "메일 목록 조회 중...", "progress": 0.1}
    # 절대 날짜 기반 조회로 타임존/오프셋 이슈 제거
    result = get_email_summary_on(date_on=selected_date.strftime('%Y-%m-%d'), max_results=10)
    st.session_state["current_process"]["desc"] = "메일 목록 분석 중..."
    st.session_state["current_process"]["progress"] = 0.3
    if result["status"] == "success":
        real_emails = result["emails"]
    else:
        st.error(result.get("error", "메일 조회 실패"))
        real_emails = []
    st.session_state["current_process"] = None

    mail_analysis_agent = EmailAgent()

    def analyze_mail_with_agent(mail: Dict[str, Any]) -> Dict[str, str]:
        try:
            st.session_state["current_process"] = {"type": "email", "desc": "이메일 본문 분석 중...", "progress": 0.1}
            st.session_state["current_process"]["desc"] = "이메일 본문 분석 중..."
            st.session_state["current_process"]["progress"] = 0.2
            analysis_data = {
                "email_body": mail.get('body', ''),
                "email_subject": mail.get('subject', ''),
                "email_from": mail.get('from', ''),
                "email_date": mail.get('date', ''),
            }
            analysis_result = mail_analysis_agent.process_task(analysis_data)
            st.session_state["current_process"]["desc"] = "자동 답장 생성 중..."
            st.session_state["current_process"]["progress"] = 0.5
            if analysis_result.get('status') == 'success':
                return {
                    'summary': analysis_result.get('analysis', '분석 완료'),
                    'importance': analysis_result.get('importance', '일반'),
                    'action': analysis_result.get('action', '참조만 해도 됨'),
                    'reason': analysis_result.get('reason', '분석 완료'),
                }
            else:
                return {
                    'summary': f"{mail.get('body', mail.get('subject', ''))[:20]}...",
                    'importance': '일반',
                    'action': '참조만 해도 됨',
                    'reason': '분석 실패',
                }
        except Exception as e:  # pragma: no cover
            st.session_state["current_process"] = None
            return {
                'summary': f"{mail.get('body', mail.get('subject', ''))[:20]}...",
                'importance': '일반',
                'action': '참조만 해도 됨',
                'reason': f'오류: {str(e)}',
            }

    mail_rows: List[Dict[str, Any]] = []
    for m in real_emails:
        analysis = analyze_mail_with_agent(m)
        mail_rows.append({
            'id': m.get('message_id', m.get('id', '')),
            '제목': m.get('subject', ''),
            '핵심 내용': analysis['summary'],
            '중요도': analysis['importance'],
            '의사결정': analysis['action'],
            '분석 근거': analysis['reason'],
            '첨부파일': '없음',
        })

    if not mail_rows:
        st.info("해당 날짜에 받은 메일이 없습니다.")
        return

    df = pd.DataFrame(mail_rows)

    # 표에서 메일 선택 기능 구현
    st.markdown("### 📧 메일 목록")

    # id 컬럼을 숨김으로 포함하여 선택 매핑을 안정화
    table_data = df[['id', '제목', '중요도', '의사결정']].copy()
    importance_order = {'매우 중요': 1, '중요': 2, '일반': 3, '낮음': 4}
    table_data['중요도_정렬'] = table_data['중요도'].map(importance_order).fillna(99).astype(int)

    gb = GridOptionsBuilder.from_dataframe(table_data)
    gb.configure_selection('single', use_checkbox=False)
    # 행 클릭만으로 선택되도록 보장
    gb.configure_grid_options(suppressRowClickSelection=False)
    # id 컬럼을 보이도록 하여 선택 데이터에 포함되게 함 (폭은 최소화)
    gb.configure_column('id', header_name='ID', width=90, hide=False)
    gb.configure_column('제목', header_name='메일 제목', width=400)
    gb.configure_column('중요도', header_name='중요도', width=100, sortable=True)
    gb.configure_column('의사결정', header_name='의사결정', width=120)
    gb.configure_column('중요도_정렬', hide=True, sort='asc')
    grid_options = gb.build()

    grid_response = AgGrid(
        table_data,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        height=350,
        theme='streamlit',
        reload_data=False,
        key="email_list_grid",
    )

    # 1) 세션에 저장된 선택 id가 있으면 우선 매핑하여 selected_idx 결정
    selected_idx = st.session_state.get('selected_mail_index', 0) or 0
    persisted_id = st.session_state.get('selected_mail_id')
    if persisted_id:
        try:
            m = df[df['id'] == persisted_id]
            if not m.empty:
                selected_idx = int(m.index[0])
                st.session_state.selected_mail_index = selected_idx
        except Exception:
            pass
    selected_rows = grid_response.get('selected_rows', [])
    # 선택 결과를 리스트[dict]로 정규화 (버전별 반환 타입 대응)
    try:
        if hasattr(selected_rows, 'to_dict'):
            selected_rows = selected_rows.to_dict(orient='records')  # pandas DataFrame -> list[dict]
        elif isinstance(selected_rows, dict):
            selected_rows = [selected_rows]
        elif not isinstance(selected_rows, list):
            selected_rows = []
    except Exception:
        selected_rows = []
    if isinstance(selected_rows, list) and len(selected_rows) > 0 and isinstance(selected_rows[0], dict):
        selected_row = selected_rows[0]
        # id 기반으로 안정적으로 매핑
        try:
            sel_id = selected_row.get('id')
            if sel_id is not None and sel_id != "":
                match = df[df['id'] == sel_id]
                if not match.empty:
                    selected_idx = int(match.index[0])
                    # 선택이 변경되었으면 세션 상태 갱신 및 즉시 리렌더
                    if st.session_state.get('selected_mail_id') != sel_id:
                        st.session_state['selected_mail_id'] = sel_id
                        st.session_state.selected_mail_index = selected_idx
                        st.experimental_rerun()
            else:
                # 폴백: 제목으로 매핑 (동일 제목이 여러 개라면 첫 매칭)
                title = selected_row.get('제목')
                if title:
                    match = df[df['제목'] == title]
                    if not match.empty:
                        selected_idx = int(match.index[0])
                        st.session_state.selected_mail_index = selected_idx
        except Exception:
            pass
    st.session_state.selected_mail_index = selected_idx
    selected_mail = real_emails[selected_idx]

    st.markdown("---")
    st.markdown("### 📋 선택된 메일 상세")
    st.markdown(f"**제목:** {selected_mail.get('subject','')}  ")
    st.markdown(f"**발신자:** {selected_mail.get('from','')}  ")
    st.markdown(f"**날짜:** {selected_mail.get('date','')}  ")
    st.markdown(f"**첨부파일:** 없음  ")

    # message_id가 없으면 id로 폴백
    detail_key = selected_mail.get('message_id') or selected_mail.get('id', '')

    detail = get_email_details(detail_key)
    body = detail.get('body', '(본문 없음)')
    st.markdown(f"**본문:**\n{body}")

    # 하단 상세 업문: 자동 답장, 첨부파일 추출 UI
    email_tasks = [
        {"name": "자동 답장", "key": "auto_reply"},
        {"name": "첨부파일 추출", "key": "attachment_extract"},
    ]
    tab_labels = [task["name"] for task in email_tasks]
    tabs = st.tabs(tab_labels)

    email_agent = EmailAgent()

    for idx, tab in enumerate(tabs):
        with tab:
            if email_tasks[idx]["key"] == "auto_reply":
                st.markdown("#### 자동 답장")
                with st.form("email_reply_form"):
                    추가지시 = st.text_area("추가 지시사항 (선택)", placeholder="답장에 반영할 추가 요청사항", key="reply_extra")
                    submitted = st.form_submit_button("자동 답장 생성")
                if submitted:
                    subject = selected_mail.get('subject', '')
                    body = selected_mail.get('body', '')
                    sender = selected_mail.get('from', '')
                    history = '\n'.join(selected_mail.get('history', []))
                    tone = "정중하고 간결한 비즈니스 톤"
                    task_id = f"email_{uuid.uuid4().hex}"
                    agent_message = AgentMessage(
                        sender_id="ui",
                        receiver_id="email_agent",
                        message_type=MessageType.TASK_REQUEST.value,
                        content={
                            "task_id": task_id,
                            "task_data": {
                                "type": "generate_reply",
                                "email_id": selected_mail.get('message_id', ''),
                                "subject": subject,
                                "body": body,
                                "from": sender,
                                "history": history,
                                "tone": tone,
                                "extra_instruction": 추가지시,
                            },
                        },
                        id=f"msg_{uuid.uuid4().hex}",
                    )
                    reply_result = email_agent._handle_task_request(agent_message)
                    reply_draft = reply_result.get('result', {}).get('reply', '[답장 생성 실패]')
                    st.session_state['email_reply_draft'] = reply_draft
                reply_draft = st.session_state.get('email_reply_draft', '')
                reply_text = st.text_area("답장 초안 (수정 가능)", value=reply_draft, key="reply_draft_edit")
                send_clicked = st.button("답장 발송")
                if send_clicked and reply_text.strip():
                    send_task_id = f"email_{uuid.uuid4().hex}"
                    send_message = AgentMessage(
                        sender_id="ui",
                        receiver_id="email_agent",
                        message_type=MessageType.TASK_REQUEST.value,
                        content={
                            "task_id": send_task_id,
                            "task_data": {
                                "type": "send_reply",
                                "email_id": selected_mail.get('message_id', ''),
                                "reply_body": reply_text,
                            },
                        },
                        id=f"msg_{uuid.uuid4().hex}",
                    )
                    send_result = email_agent._handle_task_request(send_message)
                    if send_result.get('result', {}).get('status') == 'success':
                        st.success("답장이 성공적으로 발송되었습니다.")
                    else:
                        st.error(f"답장 발송 실패: {send_result.get('result', {}).get('error', '알 수 없는 오류')}")
            elif email_tasks[idx]["key"] == "attachment_extract":
                st.markdown("#### 첨부파일 추출")
                with st.form("email_attachment_form"):
                    첨부파일 = st.multiselect(
                        "첨부파일",
                        [a['filename'] for a in selected_mail.get('attachments', [])],
                        default=[a['filename'] for a in selected_mail.get('attachments', [])],
                        key="extract_attachments",
                    )
                    submitted = st.form_submit_button("첨부파일 저장")
                if submitted:
                    # TODO: 첨부파일 저장 로직 연동
                    st.session_state['email_attachment_result'] = {
                        'saved_files': [f"/local/path/{f}" for f in 첨부파일] if 첨부파일 else []
                    }
                if st.session_state.get('email_attachment_result'):
                    res = st.session_state['email_attachment_result']
                    st.markdown("**저장된 파일 경로**")
                    for path in res['saved_files']:
                        st.write(path)
            else:
                st.markdown(f"### {email_tasks[idx]['name']}")
                st.markdown(
                    f"<div style='margin-top:32px;'><b>{email_tasks[idx]['name']}</b> 업문 영역 (추후 구현)</div>",
                    unsafe_allow_html=True,
                )
