# agents/persona_selector_agent.py
# -*- coding: utf-8 -*-
"""
PersonaSelectorAgent: 작업 메타데이터를 바탕으로 적절한 페르소나를 선택하는 경량 에이전트.
초기 구현은 규칙 기반 점수(rank_for_task) 결과를 사용하고, 상위 1개를 반환합니다.
"""
from typing import Any, Dict, Optional, List, Tuple
import logging

from personas.repository import PersonaRepository

logger = logging.getLogger("PersonaSelectorAgent")


class PersonaSelectorAgent:
    """아주 간단한 페르소나 선택 에이전트"""

    def __init__(self, strategy: str = "rules_first") -> None:
        self.strategy = strategy

    # 내부: 계층적 후보군 산출(category -> role -> expertise)
    def _hierarchical_candidates(self, task_meta: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        """
        category, role, expertise 순서로 필터를 시도하며, 단계별로 후보를 좁힌다.
        해당 단계에서 후보가 0명이면 그 필터는 건너뛴다(완전 배제 방지).
        반환: (후보 이름 리스트, rationale dict)
        """
        meta = task_meta or {}
        cat = (meta.get("category") or "").strip()
        role = (meta.get("role") or "").strip()
        exp = (meta.get("expertise") or "").strip()

        all_data = PersonaRepository.get_all()
        names = list(all_data.keys())
        rationale: Dict[str, Any] = {"filters": []}

        # 1) category exact match
        if cat:
            cands = [n for n in names if str(all_data[n].get("category", "")).lower() == cat.lower()]
            if cands:
                names = cands
                rationale["filters"].append({"stage": "category", "value": cat, "kept": len(names)})
            else:
                rationale["filters"].append({"stage": "category", "value": cat, "kept": "all (no match)"})

        # 2) role contains/contained match
        if role:
            lc_role = role.lower()
            cands = [
                n for n in names
                if lc_role in str(all_data[n].get("role", all_data[n].get("직책", ""))).lower()
                or str(all_data[n].get("role", all_data[n].get("직책", ""))).lower() in lc_role
            ]
            if cands:
                names = cands
                rationale["filters"].append({"stage": "role", "value": role, "kept": len(names)})
            else:
                rationale["filters"].append({"stage": "role", "value": role, "kept": "unchanged (no match)"})

        # 3) expertise contains
        if exp:
            lc_exp = exp.lower()
            cands = [
                n for n in names
                if lc_exp in str(all_data[n].get("expertise", all_data[n].get("전문 분야", ""))).lower()
            ]
            if cands:
                names = cands
                rationale["filters"].append({"stage": "expertise", "value": exp, "kept": len(names)})
            else:
                rationale["filters"].append({"stage": "expertise", "value": exp, "kept": "unchanged (no match)"})

        return names, rationale

    def select(self, task_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        입력 task_meta: { 'skills': [..], 'domain': str, 'style': str, ... }
        반환: { 'name': str, 'persona': dict, 'score': float }
        선택 실패 시 None
        """
        try:
            # 계층 후보군 산출 후 랭킹
            candidates, rationale = self._hierarchical_candidates(task_meta)
            ranked = PersonaRepository.rank_for_task(task_meta=task_meta, top_k=20)
            if candidates:
                ranked = [r for r in ranked if r[0] in candidates]
            if not ranked:
                logger.info("No persona candidates matched the task meta; returning None.")
                return None
            top_score = ranked[0][2]
            top_group = [r for r in ranked if r[2] == top_score]

            # tie-break: 스킬 겹침 수가 많은 후보 우선, 그 다음 스타일 일치 여부
            skills = set((task_meta or {}).get("skills", []) or [])
            desired_style = (task_meta or {}).get("style")

            def _key(item):
                _name, _persona, _score = item
                p_skills = set((_persona or {}).get("skills", []) or [])
                overlap = len(skills & p_skills)
                style_match = 1 if desired_style and desired_style in str((_persona or {}).get("description", "")) else 0
                return (overlap, style_match)

            best = max(top_group, key=_key) if len(top_group) > 1 else ranked[0]
            name, persona, score = best
            # 간단 rationale 부가: 매칭 수준 요약
            rationale.update({
                "selected": name,
                "score": score,
                "category": persona.get("category"),
                "role": persona.get("role") or persona.get("직책"),
                "expertise": persona.get("expertise") or persona.get("전문 분야"),
            })
            logger.info(
                "Persona selected (score=%s, skills=%s, desired_style=%s): %s",
                score, list(skills), desired_style, name,
            )
            return {"name": name, "persona": persona, "score": score, "rationale": rationale}
        except Exception as e:
            logger.exception(f"Persona selection failed: {e}")
            return None

    def select_pair(self, task_meta: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        작성자/검토자 페어 자동 선정.
        - 랭킹 상위 1명을 작성자(writer), 2번째를 검토자(reviewer)로 지정(동일 인물 방지)
        - 후보가 1명뿐이면 reviewer는 None
        반환: { 'writer': Optional[str], 'reviewer': Optional[str] }
        """
        try:
            candidates, _ = self._hierarchical_candidates(task_meta)
            ranked = PersonaRepository.rank_for_task(task_meta=task_meta, top_k=20) or []
            if candidates:
                ranked = [r for r in ranked if r[0] in candidates]
            if not ranked:
                return {"writer": None, "reviewer": None}
            writer = ranked[0][0]
            reviewer = None
            for name, _persona, _score in ranked[1:]:
                if name != writer:
                    reviewer = name
                    break
            return {"writer": writer, "reviewer": reviewer}
        except Exception as e:
            logger.exception(f"Persona pair selection failed: {e}")
            return {"writer": None, "reviewer": None}

    def select_collaborators(self, task_meta: Dict[str, Any], k: int = 3) -> list[str]:
        """
        협업용 다중 페르소나 선정. 상위 k명 이름 리스트 반환.
        """
        try:
            candidates, _ = self._hierarchical_candidates(task_meta)
            ranked = PersonaRepository.rank_for_task(task_meta=task_meta, top_k=max(k * 3, 3)) or []
            if candidates:
                ranked = [r for r in ranked if r[0] in candidates]
            names = [r[0] for r in ranked]
            return names[:k]
        except Exception as e:
            logger.exception(f"Persona collaborators selection failed: {e}")
            return []
