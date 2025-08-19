from .agent_base import BaseAgent
from tools.prompt_tool.core import generate_high_quality_prompt
from typing import Dict, Any

class PromptEngineerAgent(BaseAgent):
    """
    프롬프트 엔지니어 역할: 고퀄리티 프롬프트 초안 생성 담당
    """
    def process_task(self, task_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        user_input = task_data.get('user_input', '')
        options = task_data.get('options', {})
        mode = task_data.get('mode', 'basic')
        # 페르소나 컨텍스트 전달(없으면 None)
        persona = None
        try:
            persona = task_data.get('persona') or (context.get('persona') if isinstance(context, dict) else None)
        except Exception:
            persona = None
        return generate_high_quality_prompt(user_input, options, mode=mode, persona=persona)