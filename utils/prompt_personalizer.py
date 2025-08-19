# utils/prompt_personalizer.py
# -*- coding: utf-8 -*-
"""
페르소나 정보를 프롬프트 컨텍스트 문자열로 변환하는 공통 유틸.
기존 planning_tool에서 하던 문자열 합성을 여기로 모아 일관성 유지.
"""
from typing import Dict, Any, List


def build_persona_context(persona: Dict[str, Any]) -> str:
    """
    확장된 페르소나 스키마를 반영해 모델 컨텍스트 문자열을 생성.
    - 신스키마: category, role, expertise, description, skills(list), style(list), tags(list), display_name
    - 레거시: 이름, 직책, 전문 분야, 업무 영역(list), 성격, 글쓰기_특징, 톤, 스타일
    누락된 값은 건너뛰며, 리스트는 쉼표 구분으로 표기합니다.
    """
    if not persona:
        return ""

    def _as_list(val: Any) -> List[str]:
        if val is None:
            return []
        if isinstance(val, list):
            return [str(x) for x in val]
        return [str(val)]

    # 표준 키 매핑(신규/레거시 병행)
    name = persona.get("display_name") or persona.get("이름")
    category = persona.get("category")
    role = persona.get("role") or persona.get("직책")
    expertise = persona.get("expertise") or persona.get("전문 분야")
    description = persona.get("description")
    skills = _as_list(persona.get("skills"))
    style_list = _as_list(persona.get("style"))
    tags = _as_list(persona.get("tags"))
    # 레거시 확장 필드
    work_areas = _as_list(persona.get("업무 영역"))
    mindset = _as_list(persona.get("사고방식"))
    personality = persona.get("성격")
    writing = persona.get("글쓰기_특징")
    tone = persona.get("톤")
    style_legacy = persona.get("스타일")

    # 섹션 구성
    lines: List[str] = []
    # 프로필
    prof: List[str] = []
    if name:
        prof.append(f"이름: {name}")
    if category:
        prof.append(f"대분류: {category}")
    if role:
        prof.append(f"직책: {role}")
    if expertise:
        prof.append(f"전문 분야: {expertise}")
    if prof:
        lines.append("[프로필]")
        lines.extend(prof)

    # 설명
    if description:
        lines.append("[설명]")
        lines.append(str(description))

    # 업무/사고 방식
    wa_ms: List[str] = []
    if work_areas:
        wa_ms.append("업무 영역: " + ", ".join(work_areas))
    if mindset:
        wa_ms.append("사고방식: " + ", ".join(mindset))
    if wa_ms:
        lines.append("[업무/사고 방식]")
        lines.extend(wa_ms)

    # 스킬/태그
    st: List[str] = []
    if skills:
        st.append("스킬: " + ", ".join(skills))
    if tags:
        st.append("태그: " + ", ".join(tags))
    if st:
        lines.append("[스킬/태그]")
        lines.extend(st)

    # 스타일/톤/글쓰기 특징
    style_bits: List[str] = []
    if style_list:
        style_bits.append("style: " + ", ".join(style_list))
    if style_legacy:
        style_bits.append("스타일: " + str(style_legacy))
    if tone:
        style_bits.append("톤: " + str(tone))
    if writing:
        style_bits.append("글쓰기 특징: " + str(writing))
    if personality:
        style_bits.append("성격: " + str(personality))
    if style_bits:
        lines.append("[스타일]")
        lines.extend(style_bits)

    return "\n".join(lines)


def build_personalized_prompt(base_prompt: str, persona_or_ctx: Any) -> str:
    """
    페르소나 컨텍스트를 기본 프롬프트에 일관되게 병합하는 유틸.

    Args:
        base_prompt: 에이전트의 기본 프롬프트 템플릿 문자열
        persona_or_ctx: dict(persona) 또는 이미 생성된 컨텍스트 문자열

    Returns:
        페르소나 컨텍스트가 선두에 포함된 프롬프트 문자열.
        페르소나가 없으면 base_prompt를 그대로 반환.
    """
    if not persona_or_ctx:
        return base_prompt

    try:
        # dict로 들어오면 컨텍스트 생성, 문자열이면 그대로 사용
        if isinstance(persona_or_ctx, dict):
            ctx = build_persona_context(persona_or_ctx)
        else:
            ctx = str(persona_or_ctx)
        ctx = ctx.strip()
        if not ctx:
            return base_prompt
        return f"[페르소나 지침]\n{ctx}\n---\n" + base_prompt
    except Exception:
        # 컨텍스트 생성 실패 시 기본 프롬프트 반환(보수적 처리)
        return base_prompt
