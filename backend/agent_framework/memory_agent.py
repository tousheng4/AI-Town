"""记忆检索Agent"""
import time
from typing import Dict, Any

from memory import get_history
from .base import BaseAgent, AgentResult


class MemoryAgent(BaseAgent):
    """记忆检索Agent"""

    def __init__(self, llm=None, episodic_memories: Dict = None):
        super().__init__("MemoryAgent", llm)
        self.episodic_memories = episodic_memories or {}

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """执行记忆检索"""
        start_time = time.time()

        try:
            npc_name = context.get("npc_name")
            player_id = context.get("player_id")
            player_message = context.get("player_message", "")

            # 1. 获取工作记忆 (短期)
            working_memory = get_history(npc_name, player_id)

            # 2. 获取情景记忆 (长期) - 如果可用
            episodic_memory = self.episodic_memories.get(npc_name)
            relevant_memories = []

            if episodic_memory:
                try:
                    docs = episodic_memory.similarity_search(
                        query=player_message,
                        k=3
                    )
                    for doc in docs:
                        content = getattr(doc, "page_content", str(doc))
                        relevant_memories.append(content)
                except Exception as e:
                    print(f"  ⚠️ 情景记忆检索失败: {e}")

            # 构建记忆上下文
            memory_context = self._build_memory_context(relevant_memories)

            result_data = {
                "working_memory": working_memory,
                "episodic_memories": relevant_memories,
                "memory_context": memory_context
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

    def _build_memory_context(self, memories: list) -> str:
        if not memories:
            return ""
        context = ["【相关记忆】"]
        for mem in memories[:3]:
            context.append(f"- {mem}")
        return "\n".join(context)
