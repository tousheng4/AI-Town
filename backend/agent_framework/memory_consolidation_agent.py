"""记忆压缩/整合Agent

职责：
1. 将最近N轮对话压缩成事件摘要（event_summary）
2. 提取关键实体（players, entities）
3. 评估重要度（importance 0-1）
4. 生成结构化的事件块用于长期存储
5. 抽取玩家Profile事实

触发时机：
- 每N轮对话后（配置 MEMORY_CONSOLIDATION_INTERVAL）
- 对话结束时
"""

from typing import Dict, Any, List
from datetime import datetime

from .base import BaseAgent, AgentResult
from config import settings
from .profile_extraction_agent import ProfileExtractionAgent


# 记忆压缩的系统提示词
CONSOLIDATION_SYSTEM_PROMPT = """将对话压缩成JSON格式的事件块。

任务：
1. 一句话概括对话内容
2. 提取参与者（players）
3. 提取涉及的话题/实体（entities）
4. 评估重要度（0-1）：
   - 0.9-1.0: 承诺、约定、冲突、表白、重要决定
   - 0.6-0.8: 讨论重要话题、深入交流
   - 0.3-0.5: 日常问候、闲聊
   - 0.0-0.2: 客套话、敷衍

必须输出有效JSON，格式：
{{"event_summary": "一句话概括", "players": ["玩家"], "entities": ["话题"], "importance": 0.5, "timestamp_range": "03-04 10:00"}}
"""


class MemoryConsolidationAgent(BaseAgent):
    """记忆压缩Agent - 将对话压缩成事件块"""

    def __init__(self, llm=None):
        super().__init__("MemoryConsolidationAgent", llm)
        self.consolidation_interval = settings.MEMORY_CONSOLIDATION_INTERVAL
        self.profile_agent = ProfileExtractionAgent(llm)

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """执行记忆压缩

        Args:
            context: 包含以下字段
                - npc_name: NPC名称
                - player_id: 玩家ID
                - dialogue_history: 对话历史列表 [{"role": "human/ai", "content": "..."}]
                - timestamp_start: 对话开始时间
                - timestamp_end: 对话结束时间

        Returns:
            AgentResult:
                - success: 是否成功
                - data: {
                    "event_block": {...},  # 事件块数据
                    "profile_facts": [...]  # 抽取的事实列表
                  }
        """
        try:
            npc_name = context.get("npc_name", "")
            player_id = context.get("player_id", "")
            dialogue_history = context.get("dialogue_history", [])
            timestamp_start = context.get("timestamp_start", "")
            timestamp_end = context.get("timestamp_end", "")

            if not dialogue_history:
                return self._create_result(
                    success=True,
                    data={"event_block": None, "profile_facts": []},
                    error="对话历史为空"
                )

            # 1. 压缩成事件块
            event_block = await self._consolidate_to_event(
                dialogue_history, timestamp_start, timestamp_end
            )

            # 2. 抽取Profile事实（使用ProfileExtractionAgent）
            profile_result = await self.profile_agent.execute({
                "dialogue_history": dialogue_history
            })
            profile_facts = profile_result.data.get("facts", []) if profile_result.success else []

            # 生成turn_id用于追溯
            turn_id = f"{npc_name}_{player_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            event_block["raw_turn_ids"] = [turn_id]

            return self._create_result(
                success=True,
                data={
                    "event_block": event_block,
                    "profile_facts": profile_facts,
                    "npc_name": npc_name,
                    "player_id": player_id
                }
            )

        except Exception as e:
            return self._create_result(
                success=False,
                error=f"记忆压缩失败: {str(e)}"
            )

    async def _consolidate_to_event(
        self,
        dialogue_history: List[Dict],
        timestamp_start: str,
        timestamp_end: str
    ) -> Dict[str, Any]:
        """将对话历史压缩成事件块"""

        # 构建对话摘要用于LLM输入
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

        # 调用LLM进行压缩
        if self.llm:
            try:
                from langchain_core.prompts import ChatPromptTemplate
                from langchain_core.output_parsers import JsonOutputParser

                prompt = ChatPromptTemplate.from_messages([
                    ("system", CONSOLIDATION_SYSTEM_PROMPT),
                    ("human", "对话历史：\n{dialogue_text}")
                ])

                chain = prompt | self.llm | JsonOutputParser()
                result = chain.invoke({"dialogue_text": dialogue_text})

                # 确保时间范围
                if "timestamp_range" not in result or not result["timestamp_range"]:
                    result["timestamp_range"] = self._format_timestamp_range(
                        timestamp_start, timestamp_end
                    )

                return result

            except Exception as e:
                print(f"[MemoryConsolidation] LLM调用失败: {e}")
                # 回退到简单压缩

        # 回退方案：简单提取
        return self._simple_consolidate(dialogue_history, timestamp_start, timestamp_end)

    def _simple_consolidate(
        self,
        dialogue_history: List[Dict],
        timestamp_start: str,
        timestamp_end: str
    ) -> Dict[str, Any]:
        """简单压缩方案（当LLM不可用时）"""

        # 简单取第一条和最后一条
        first_msg = dialogue_history[0].get("content", "")[:50]
        last_msg = dialogue_history[-1].get("content", "")[:50]

        return {
            "event_summary": f"对话: {first_msg}... 至 {last_msg}...",
            "players": [],
            "entities": [],
            "importance": 0.3,  # 默认中等偏低
            "timestamp_range": self._format_timestamp_range(timestamp_start, timestamp_end)
        }

    def _format_timestamp_range(self, start: str, end: str) -> str:
        """格式化时间范围"""
        if start and end:
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                return f"{start_dt.strftime('%m-%d %H:%M')}-{end_dt.strftime('%H:%M')}"
            except:
                pass
        return datetime.now().strftime("%m-%d %H:%M")
