"""Profile抽取Agent - 从对话中提取玩家长期事实"""

from typing import Dict, Any, List
from .base import BaseAgent, AgentResult
from config import settings


# Profile抽取的系统提示词
PROFILE_EXTRACTION_SYSTEM_PROMPT = """从对话中抽取玩家的长期事实。只输出有效JSON数组。

玩家说的话以"玩家: "开头，NPC说的话以"NPC: "开头。只抽取玩家的事实。

抽取类型：
- preferences: 玩家的偏好、喜欢什么
- taboos: 玩家禁忌、敏感情感
- promises: 玩家承诺、答应要做的事
- goals: 玩家的目标、计划
- relationship_tags: 描述两人关系的关键词

JSON数组格式：[{{"category": "preferences", "content": "喜欢喝咖啡", "confidence": 0.9}}]
confidence说明：0.9=非常确定，0.7=较确定，0.5=一般确定
没有事实时输出：[]
"""


class ProfileExtractionAgent(BaseAgent):
    """Profile抽取Agent - 从对话中提取长期事实"""

    def __init__(self, llm=None):
        super().__init__("ProfileExtractionAgent", llm)

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """执行Profile抽取

        Args:
            context: 包含
                - dialogue_history: 对话历史列表

        Returns:
            AgentResult:
                - success: 是否成功
                - data: {"facts": [...]}
        """
        try:
            dialogue_history = context.get("dialogue_history", [])

            if not dialogue_history:
                return self._create_result(
                    success=True,
                    data={"facts": []}
                )

            facts = await self._extract_facts(dialogue_history)
            return self._create_result(success=True, data={"facts": facts})

        except Exception as e:
            return self._create_result(
                success=False,
                error=f"Profile抽取失败: {str(e)}"
            )

    async def _extract_facts(self, dialogue_history: List[Dict]) -> List[Dict]:
        """从对话中抽取Profile事实"""

        # 转换对话格式，区分玩家和NPC
        dialogue_text = ""
        for msg in dialogue_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "human":
                dialogue_text += f"玩家: {content}\n"
            elif role == "ai":
                dialogue_text += f"NPC: {content}\n"
            else:
                dialogue_text += f"{role}: {content}\n"

        if self.llm:
            try:
                from langchain_core.prompts import ChatPromptTemplate
                from langchain_core.output_parsers import JsonOutputParser

                prompt = ChatPromptTemplate.from_messages([
                    ("system", PROFILE_EXTRACTION_SYSTEM_PROMPT),
                    ("human", "对话历史：\n{dialogue_text}")
                ])

                chain = prompt | self.llm | JsonOutputParser()
                result = chain.invoke({"dialogue_text": dialogue_text})

                # 确保返回的是列表
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict) and "facts" in result:
                    return result["facts"]
                return []

            except Exception as e:
                print(f"[ProfileExtraction] 抽取失败: {e}")

        return []
