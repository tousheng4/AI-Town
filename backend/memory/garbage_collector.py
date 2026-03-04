"""记忆垃圾回收器 - 遗忘机制

职责：
1. 定期清理低重要度且长期未被访问的记忆
2. 防止记忆库无限增长
3. 模拟人类遗忘曲线

清理条件：
- importance < 阈值 AND 超过N天未被访问
- 但承诺(promises)和禁忌(taboos)不会被遗忘
"""

from datetime import datetime
from typing import Dict, Optional

from config import settings
from logger import log_info


class MemoryGarbageCollector:
    """记忆垃圾回收器"""

    def __init__(self):
        self.forget_threshold = settings.MEMORY_FORGET_THRESHOLD
        self.forget_days = settings.MEMORY_FORGET_DAYS

    def should_forget(
            self,
            importance: float,
            last_accessed: str,
            is_critical: bool = False
    ) -> bool:
        """判断记忆是否应该被遗忘

        Args:
            importance: 重要度 (0-1)
            last_accessed: 最后访问时间 (ISO格式)
            is_critical: 是否是关键事实（承诺/禁忌），关键事实不会被遗忘

        Returns:
            是否应该遗忘
        """
        # 关键事实永不忘忆
        if is_critical:
            return False

        # 重要度太低，考虑遗忘
        if importance >= self.forget_threshold:
            return False

        # 检查是否长期未访问
        try:
            last_dt = datetime.fromisoformat(last_accessed)
            days_since = (datetime.now() - last_dt).days
            should = days_since > self.forget_days  # 改为 >= (>=1表示1天前及更早)
            log_info(
                f"[should_forget] importance={importance} < threshold={self.forget_threshold}, days_since={days_since}, forget_days={self.forget_days}, result={should}")
            return should
        except Exception as e:
            log_info(f"[should_forget] 时间解析失败: {e}, 默认遗忘")
            return True  # 无法解析时间，默认遗忘

    def calculate_retrieval_score(
            self,
            similarity_score: float,
            importance: float,
            timestamp: str,
            now: datetime = None
    ) -> float:
        """计算检索加权分数

        公式：score = α×sim + β×importance + γ×recency

        其中 recency = 1 / (1 + days_since × decay_rate)

        Args:
            similarity_score: 向量相似度分数 (0-1)
            importance: 重要度分数 (0-1)
            timestamp: 记忆时间戳 (ISO格式)
            now: 当前时间，默认为datetime.now()

        Returns:
            加权后的最终分数
        """
        if now is None:
            now = datetime.now()

        # 计算新近度
        try:
            mem_time = datetime.fromisoformat(timestamp)
            days_since = (now - mem_time).days
            # 新近度衰减: 1/(1 + days × decay_rate)
            recency = 1.0 / (1.0 + days_since * settings.MEMORY_RECENCY_DECAY_RATE)
        except:
            recency = 0.5  # 默认值

        # 加权计算
        final_score = (
                settings.RETRIEVAL_SIMILARITY_WEIGHT * similarity_score +
                settings.RETRIEVAL_IMPORTANCE_WEIGHT * importance +
                settings.RETRIEVAL_RECENCY_WEIGHT * recency
        )

        return final_score

    def get_retrieval_weights(self) -> Dict[str, float]:
        """获取当前检索权重配置"""
        return {
            "alpha": settings.RETRIEVAL_SIMILARITY_WEIGHT,
            "beta": settings.RETRIEVAL_IMPORTANCE_WEIGHT,
            "gamma": settings.RETRIEVAL_RECENCY_WEIGHT,
            "decay_rate": settings.MEMORY_RECENCY_DECAY_RATE
        }

    async def cleanup(
            self,
            npc_name: str,
            episodic_memory,
            player_id: Optional[str] = None
    ) -> Dict[str, int]:
        """清理应该遗忘的记忆

        Args:
            npc_name: NPC名称
            episodic_memory: Qdrant向量数据库实例
            player_id: 玩家ID（可选，不传则清理该NPC所有玩家的记忆）

        Returns:
            清理结果 {"scanned": 扫描数量, "deleted": 删除数量}
        """
        if not episodic_memory:
            log_info(f"跳过清理 {npc_name}：episodic_memory 为空")
            return {"scanned": 0, "deleted": 0}

        try:
            # 获取Qdrant客户端
            client = getattr(episodic_memory, 'client', None)
            if not client:
                log_info(f"跳过清理 {npc_name}：无法获取Qdrant客户端")
                return {"scanned": 0, "deleted": 0}

            collection_name = episodic_memory.collection_name

            # 构建基础过滤条件（可选的player_id过滤）
            should_filter = False
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue, Range

            must_conditions = []

            if player_id:
                must_conditions.append(
                    FieldCondition(
                        key="metadata.player_id",
                        match=MatchValue(value=player_id)
                    )
                )
                should_filter = True

            scroll_filter = Filter(must=must_conditions) if should_filter else None

            # 扫描所有记忆（不带importance过滤，因为需要检查所有记忆）
            scanned = 0
            deleted = 0
            points_to_delete = []

            # 使用scroll API遍历所有点
            offset = None
            while True:
                try:
                    results, offset = client.scroll(
                        collection_name=collection_name,
                        scroll_filter=scroll_filter,
                        limit=100,
                        with_vectors=False,
                        with_payload=True,
                        offset=offset
                    )
                except Exception as e:
                    log_info(f"滚动扫描出错: {e}")
                    break

                if not results:
                    break

                for point in results:
                    scanned += 1
                    payload = point.payload
                    metadata = payload.get("metadata", {})

                    importance = metadata.get("importance", 0.5)
                    timestamp = metadata.get("timestamp", "")
                    mem_type = metadata.get("type", "unknown")

                    # 调试：输出每条记忆的判断过程
                    log_info(
                        f"[GC Debug] type={mem_type}, importance={importance}, threshold={self.forget_threshold}, days={self.forget_days}")

                    # 判断是否应该遗忘（在代码中判断，不依赖过滤）
                    if self.should_forget(importance, timestamp, is_critical=False):
                        points_to_delete.append(point.id)
                        log_info(
                            f"标记遗忘: type={mem_type}, importance={importance}, timestamp={timestamp[:19] if timestamp else 'N/A'}")
                        deleted += 1

                if offset is None:
                    break

            # 批量删除
            if points_to_delete:
                try:
                    client.delete(
                        collection_name=collection_name,
                        points_selector=points_to_delete
                    )
                    log_info(f"清理完成: 扫描{scanned}条，删除{deleted}条")
                except Exception as e:
                    log_info(f"删除失败: {e}")

            return {"scanned": scanned, "deleted": deleted}

        except Exception as e:
            log_info(f"清理过程出错: {e}")
            return {"scanned": 0, "deleted": 0}


# 全局单例
_gc = None


def get_garbage_collector() -> MemoryGarbageCollector:
    """获取垃圾回收器单例"""
    global _gc
    if _gc is None:
        _gc = MemoryGarbageCollector()
    return _gc
