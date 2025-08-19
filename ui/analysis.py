# ui/analysis.py
# -*- coding: utf-8 -*-
"""
Streamlit 데이터 분석 탭 렌더러.
app.py의 분석 UI를 모듈화하여 유지보수성과 테스트 용이성을 높입니다.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
import os
from datetime import datetime

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


def _save_uploaded_file(uploaded_file) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    base_dir = os.path.join("files", today)
    os.makedirs(base_dir, exist_ok=True)
    filename = uploaded_file.name
    save_path = os.path.join(base_dir, filename)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path


def _try_import_tools() -> Tuple[bool, Any, Any, Any]:
    try:
        from tools.data_analysis import DataAnalysisTool, ChartGenerator, InsightExtractor  # type: ignore
        return True, DataAnalysisTool, ChartGenerator, InsightExtractor
    except Exception as e:  # pragma: no cover
        return False, None, None, None


def render_analysis_ui(state: Optional[Dict[str, Any]] = None) -> None:
    if st is None:
        return

    st.header("📊 데이터 분석")

    available, DataAnalysisTool, ChartGenerator, InsightExtractor = _try_import_tools()
    if not available:
        st.error("데이터 분석 도구를 불러올 수 없습니다. 필요한 의존성이 설치되어 있는지 확인해주세요.")
        return

    # 파일 업로드
    st.markdown("#### 파일 업로드")
    uploaded_file = st.file_uploader("분석할 파일을 업로드하세요 (CSV/Excel/PDF 등)", type=["csv", "xlsx", "xls", "pdf", "txt", "json"], key="analysis_uploader")

    if uploaded_file:
        save_path = _save_uploaded_file(uploaded_file)
        st.session_state['uploaded_file_path'] = save_path
        st.info(f"업로드 파일이 저장되었습니다: {save_path}")

        # 옵션
        col1, col2, col3 = st.columns(3)
        with col1:
            prefer_tables = st.checkbox("표 우선 추출", value=True)
        with col2:
            max_rows = st.number_input("미리보기 행 수", value=10, min_value=1, max_value=200, step=1)
        with col3:
            run_btn = st.button("분석 실행", use_container_width=True)

        if run_btn:
            st.subheader("분석 결과")
            tool = DataAnalysisTool(prefer_tables=prefer_tables)
            error_occurred = False
            try:
                result = tool.process_file(save_path)
            except Exception as e:  # pragma: no cover
                error_occurred = True
                st.error(f"파일 처리 중 오류: {e}")
                result = {"success": False, "error": str(e)}

            if not error_occurred:
                if result.get("success"):
                    tables = result.get("tables", [])
                    text_preview = result.get("text_preview") or result.get("text")

                    tab_titles = ["표 미리보기", "텍스트 미리보기", "시각화"]
                    tabs = st.tabs(tab_titles)

                    with tabs[0]:
                        if tables:
                            st.write("표가 감지되었습니다.")
                            # 여러 표가 있을 수 있으니 선택
                            options = [f"Table {i+1} ({len(tbl)} rows)" for i, tbl in enumerate(tables)]
                            idx = st.selectbox("표 선택", list(range(len(options))), format_func=lambda i: options[i])
                            import pandas as pd
                            df = pd.DataFrame(tables[idx])
                            st.dataframe(df.head(max_rows), use_container_width=True)
                        else:
                            st.info("표를 감지하지 못했습니다.")

                    with tabs[1]:
                        if text_preview:
                            st.text_area("텍스트", value=str(text_preview)[:5000], height=200)
                        else:
                            st.info("텍스트 미리보기가 없습니다.")

                    with tabs[2]:
                        try:
                            if tables:
                                import pandas as pd
                                df = pd.DataFrame(tables[0])
                                st.line_chart(df.select_dtypes(include=['number']).head(max_rows))
                            else:
                                st.info("시각화할 표 데이터가 없습니다.")
                        except Exception as e:  # pragma: no cover
                            st.warning(f"시각화 생성 실패: {e}")
                else:
                    st.error(result.get("error", "파일 처리 중 오류가 발생했습니다."))
