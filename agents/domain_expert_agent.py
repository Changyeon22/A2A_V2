from .agent_base import BaseAgent
from tools.prompt_tool.core import domain_expert_feedback
from typing import Dict, Any

class DomainExpertAgent(BaseAgent):
    """
    도메인 전문가 역할: 도메인 특화 프롬프트 피드백/보완 담당
    """
    def process_task(self, task_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        prompt = task_data.get('prompt', '')
        domain = task_data.get('domain', '일반')
        # 페르소나 컨텍스트 지원(없으면 None)
        persona = None
        try:
            persona = task_data.get('persona') or (context.get('persona') if isinstance(context, dict) else None)
        except Exception:
            persona = None
        return domain_expert_feedback(prompt, domain, persona=persona)