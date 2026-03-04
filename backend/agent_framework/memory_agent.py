"""记忆检索Agent"""
import time
from typing import Dict, Any, List, Tuple
from datetime import datetime

from logger import log_memory_retrieval, log_info as logger_log_info
from memory import get_history
from .base import BaseAgent, AgentResult
from config import settings
from memory.garbage_collector import get_garbage_collector


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
                            # 使用 similarity_search_with_score 获取相似度分数
                            results = episodic_memory.similarity_search_with_score(
                                query=player_message,
                                k=3,
                                filter=filter_obj
                            )
                            log_info(f"[Memory] 使用filter检索到 {len(results)} 条")
                        except Exception as filter_err:
                            err_msg = str(filter_err)
                            log_info(f"[Memory] filter检索失败: {err_msg}")
                            # 如果索引不存在，回退到不过滤
                            if "Index required" in err_msg:
                                log_info("⚠️ player_id索引不存在，回退到检索所有记忆")
                                results = episodic_memory.similarity_search_with_score(
                                    query=player_message,
                                    k=3
                                )
                                log_info(f"[Memory] 无过滤检索到 {len(results)} 条")
                            else:
                                raise
                    else:
                        # 如果没有filter，回退到不过滤
                        results = episodic_memory.similarity_search_with_score(
                            query=player_message,
                            k=3
                        )
                        log_info(f"[Memory] 无filter检索到 {len(results)} 条")

                    # 根据加权分数过滤和排序 (三层记忆系统)
                    SIMILARITY_THRESHOLD = settings.MEMORY_SIMILARITY_THRESHOLD
                    gc = get_garbage_collector()
                    filtered_count = 0

                    scored_memories = []
                    for doc, similarity_score in results:
                        # 提取元数据
                        metadata = getattr(doc, "metadata", {})

                        # 提取重要度（默认为0.5）
                        importance = metadata.get("importance", 0.5)

                        # 提取时间戳
                        timestamp = metadata.get("timestamp", datetime.now().isoformat())

                        # 计算最终加权分数
                        final_score = gc.calculate_retrieval_score(
                            similarity_score=similarity_score,
                            importance=importance,
                            timestamp=timestamp
                        )

                        # 获取权重信息用于日志
                        weights = gc.get_retrieval_weights()
                        log_info(f"[Memory] 📊 记忆分数: sim={similarity_score:.3f}, imp={importance:.3f}, "
                                f"final={final_score:.3f} (α={weights['alpha']}, β={weights['beta']}, γ={weights['gamma']})")

                        # 阈值过滤
                        if final_score >= SIMILARITY_THRESHOLD:
                            content = getattr(doc, "page_content", str(doc))
                            scored_memories.append({
                                "content": content,
                                "metadata": metadata,
                                "similarity_score": similarity_score,
                                "importance_score": importance,
                                "final_score": final_score
                            })
                        else:
                            filtered_count += 1

                    # 按最终分数排序
                    scored_memories.sort(key=lambda x: x["final_score"], reverse=True)

                    # 转换为简单格式
                    relevant_memories = scored_memories

                    if filtered_count > 0:
                        log_info(f"[Memory] ⚠️ 过滤掉 {filtered_count} 条低分记忆")
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
        """构建记忆上下文

        支持两种格式：
        - 旧格式: ["记忆1", "记忆2", ...]
        - 新格式: [{"content": "...", "metadata": {}, ...}, ...]
        """
        if not memories:
            return ""

        context = ["【相关记忆】"]
        for mem in memories[:3]:
            # 支持新旧两种格式
            if isinstance(mem, dict):
                content = mem.get("content", "")
            else:
                content = str(mem)
            context.append(f"- {content}")
        return "\n".join(context)
