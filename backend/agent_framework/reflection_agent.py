"""反思Agent - 审查和优化NPC回复"""
import time
from typing import Dict, Any, Optional

from .base import BaseAgent, AgentResult

# LangChain 延迟导入
ChatPromptTemplate = None


def _import_langchain():
    global ChatPromptTemplate
    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        pass


_import_langchain()


class ReflectionAgent(BaseAgent):
    """反思Agent - 审查和优化NPC回复"""

    def __init__(self, llm, npc_name: str, role_config: Dict = None):
        super().__init__(f"ReflectionAgent_{npc_name}", llm)
        self.npc_name = npc_name
        self.role_config = role_config or {}
        self.chain = None

        if llm and ChatPromptTemplate:
            self._create_reflection_chain()

    def _create_reflection_chain(self):
        """创建反思链"""
        system_prompt = """你是一个对话质量审查员。你的任务是审查NPC的回复，确保其质量。

【审查标准】
1. 角色一致性 - 回复是否符合NPC的性格、职位、说话风格
2. 内容质量 - 回复是否有意义、是否回答了玩家的问题
3. 长度合适 - 回复是否简洁自然（30-50字）
4. 情感恰当 - 回复是否与当前关系等级相符

【输出格式】
请直接输出审查结果，格式如下：
- 如果回复无需修改: PASS
- 如果需要修改: REVISED: [优化后的回复]

注意：只输出审查结果，不要有其他解释。"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """【NPC信息】
- 姓名: {npc_name}
- 职位: {title}
- 性格: {personality}
- 说话风格: {style}

【当前对话】
玩家: {player_message}
NPC回复: {npc_response}

【关系】
- 好感度等级: {affinity_level}
- 对话风格: {affinity_modifier}

请审查这个回复：""")
        ])

        self.chain = prompt | self.llm

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """执行反思审查"""
        start_time = time.time()

        try:
            npc_response = context.get("npc_response", "")
            player_message = context.get("player_message", "")
            role_config = context.get("role_config", self.role_config)
            affinity_level = context.get("affinity_level", "陌生")
            affinity_modifier = context.get("affinity_modifier", "礼貌友善")

            # 如果没有LLM或chain，直接返回原回复
            if not self.chain:
                return self._create_result(
                    success=True,
                    data={
                        "original_response": npc_response,
                        "revised_response": npc_response,
                        "needs_revision": False
                    }
                )

            # 调用LLM进行审查
            response = self.chain.invoke({
                "npc_name": self.npc_name,
                "title": role_config.get("title", ""),
                "personality": role_config.get("personality", ""),
                "style": role_config.get("style", ""),
                "player_message": player_message,
                "npc_response": npc_response,
                "affinity_level": affinity_level,
                "affinity_modifier": affinity_modifier
            })

            response_text = getattr(response, "content", str(response)).strip()

            # 解析审查结果
            needs_revision = False
            revised_response = npc_response

            if response_text.startswith("REVISED:"):
                needs_revision = True
                revised_response = response_text.replace("REVISED:", "").strip()
            elif response_text != "PASS":
                # 如果不是PASS，尝试直接使用审查结果作为修改后的回复
                needs_revision = True
                revised_response = response_text

            execution_time = time.time() - start_time

            return self._create_result(
                success=True,
                data={
                    "original_response": npc_response,
                    "revised_response": revised_response,
                    "needs_revision": needs_revision,
                    "reflection": response_text
                }
            )

        except Exception as e:
            # 发生错误时返回原始回复
            return self._create_result(
                success=True,
                data={
                    "original_response": context.get("npc_response", ""),
                    "revised_response": context.get("npc_response", ""),
                    "needs_revision": False,
                    "error": str(e)
                }
            )
