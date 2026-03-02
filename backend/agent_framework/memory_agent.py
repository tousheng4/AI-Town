"""记忆检索Agent"""
import time
from typing import Dict, Any

from logger import log_memory_retrieval, log_info as logger_log_info
from memory import get_history
from .base import BaseAgent, AgentResult


def log_info(msg: str):
    logger_log_info(msg)


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

            log_info(f"[Memory] player_id={player_id}, npc={npc_name}")

            # 1. 获取工作记忆 (短期)
            working_memory = get_history(npc_name, player_id)

            # 2. 获取情景记忆 (长期) - 如果可用
            episodic_memory = self.episodic_memories.get(npc_name)
            relevant_memories = []

            if episodic_memory:
                try:
                    log_info(f"[Memory] 开始检索情景记忆，collection={getattr(episodic_memory, 'collection_name', 'unknown')}")

                    # 按 player_id 过滤，只检索当前玩家的记忆
                    filter_obj = None
                    try:
                        from qdrant_client import QdrantClient
                        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

                        # 构建过滤条件（注意：数据存储在 metadata.player_id）
                        filter_obj = Filter(
                            must=[FieldCondition(key="metadata.player_id", match=MatchValue(value=player_id))]
                        )
                        log_info(f"[Memory] 使用filter过滤 metadata.player_id={player_id}")
                    except ImportError as imp_err:
                        log_info(f"[Memory] 导入过滤模块失败: {imp_err}")

                    if filter_obj:
                        try:
                            docs = episodic_memory.similarity_search(
                                query=player_message,
                                k=3,
                                filter=filter_obj
                            )
                            log_info(f"[Memory] 使用filter检索到 {len(docs)} 条")
                        except Exception as filter_err:
                            err_msg = str(filter_err)
                            log_info(f"[Memory] filter检索失败: {err_msg}")
                            # 如果索引不存在，回退到不过滤
                            if "Index required" in err_msg:
                                log_info("⚠️ player_id索引不存在，回退到检索所有记忆")
                                docs = episodic_memory.similarity_search(
                                    query=player_message,
                                    k=3
                                )
                                log_info(f"[Memory] 无过滤检索到 {len(docs)} 条")
                            else:
                                raise
                    else:
                        # 如果没有filter，回退到不过滤
                        docs = episodic_memory.similarity_search(
                            query=player_message,
                            k=3
                        )
                        log_info(f"[Memory] 无filter检索到 {len(docs)} 条")

                    for doc in docs:
                        content = getattr(doc, "page_content", str(doc))
                        relevant_memories.append(content)
                except Exception as e:
                    log_info(f"⚠️ 情景记忆检索失败: {e}")

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
