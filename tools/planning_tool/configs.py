# tools/planning_tool/configs.py

from personas.repository import PersonaRepository

# 중앙 리포지토리에서 재노출하여 단일 소스 유지
personas = PersonaRepository.get_all()

# 문서 템플릿 단일 소스: template_generator의 DEFAULT_TEMPLATES를 사용
# DEFAULT_TEMPLATES는 각 템플릿을 {section_key: format_string} 형태로 제공하므로
# UI/코어에서 사용하던 DOCUMENT_TEMPLATES 형식(섹션 목록)으로 변환합니다.
try:
    from tools.template_generator.core import DEFAULT_TEMPLATES  # type: ignore

    DOCUMENT_TEMPLATES = {
        name: list(structure.keys()) for name, structure in DEFAULT_TEMPLATES.items()
    }
    # 한국어 라벨 매핑 (UI 표시용)
    TEMPLATE_LABELS = {
        "report": "보고서",
        "article": "아티클",
        "memo": "메모",
        "research": "연구 보고서",
        "proposal": "제안서",
        "tech_doc": "기술 문서",
    }
except Exception:
    # 안전한 폴백: 기존 정적 정의 유지 (template_generator가 없거나 오류 시)
    DOCUMENT_TEMPLATES = {
        "컨셉 기획서": [
            "프로젝트 개요", "목표 및 목적", "주요 성과 지표", "주요 전략",
            "예상 일정", "예산 및 자원", "리스크 관리", "성공 요인"
        ],
        "상세 기획서": [
            "프로젝트 상세 개요", "기능 명세서", "기술적 요구사항", "일정 및 마일스톤",
            "리소스 계획", "위험 요소 분석", "품질 보증 계획", "운영 및 유지보수 계획"
        ],
        "업무 분배서": [
            "기획 Task 목록", "우선순위 및 일정", "담당자 배정", "문서 종류 및 제출 버전",
            "검토/피드백 일정", "최종 완료 기준", "진행 상태 관리 항목"
        ],
        "프로젝트 기획서": [
            "프로젝트 개요", "목표 및 목적", "주요 기능", "일정 계획",
            "리소스 분배", "예산 계획", "위험 관리", "성과 측정"
        ],
        "확장 문서": [
            "확장 개요", "기존 내용 분석", "확장 방향", "세부 내용",
            "구현 계획", "영향 분석", "검증 방법", "향후 계획"
        ]
    }

# persona_to_description 함수는 이 파일의 configs가 아닌, tools.planning_tool.core.py에서 필요하므로
# core.py에 직접 정의하거나, 필요하다면 tools/ui_helpers.py (공용)에 정의하고 임포트 할 수 있습니다.
# 여기서는 tools.planning_tool.core.py 내에서 직접 정의하는 것으로 가정합니다.