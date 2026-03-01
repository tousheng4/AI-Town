"""好感度分析Agent"""
import time
from typing import Dict, Any

from .base import BaseAgent, AgentResult


class AffinityAgent(BaseAgent):
    """好感度分析Agent"""

    def __init__(self, llm, relationship_manager=None):
        super().__init__("AffinityAgent", llm)
        self.relationship_manager = relationship_manager

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """执行好感度分析"""
        start_time = time.time()

        try:
            npc_name = context.get("npc_name")
            player_id = context.get("player_id")

            if not self.relationship_manager:
                return self._create_result(
                    success=True,
                    data={"affinity": 50.0, "level": "熟悉", "modifier": "礼貌友善"}
                )

            # 获取当前好感度
            affinity = self.relationship_manager.get_affinity(npc_name, player_id)
            level = self.relationship_manager.get_affinity_level(affinity)
            modifier = self.relationship_manager.get_affinity_modifier(affinity)

            result_data = {
                "affinity": affinity,
                "level": level,
                "modifier": modifier,
                "affinity_context": f"""【当前关系】
  你与玩家的关系: {level} (好感度: {affinity:.0f}/100)
  【对话风格】{modifier}

  """
            }

            return self._create_result(
                success=True,
                data=result_data
            )

        except Exception as e:
            return self._create_result(
                success=False,
                error=str(e)
            )

    async def update_affinity(self, npc_name: str, player_id: str,
                              player_message: str, npc_response: str) -> AgentResult:
        """更新好感度"""
        try:
            if not self.relationship_manager:
                return self._create_result(success=True, data={"changed": False})

            result = self.relationship_manager.analyze_and_update_affinity(
                npc_name=npc_name,
                player_message=player_message,
                npc_response=npc_response,
                player_id=player_id
            )

            return self._create_result(success=True, data=result)

        except Exception as e:
            return self._create_result(success=False, error=str(e))
