"""对话上下文管理器"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class ConversationContext:
    """对话上下文"""
    # 输入
    npc_name: str
    player_id: str
    player_message: str

    # Agent执行结果
    memory_result: Optional[Dict] = None
    affinity_result: Optional[Dict] = None
    dialogue_result: Optional[Dict] = None
    reflection_result: Optional[Dict] = None

    # NPC信息
    npc_info: Dict = field(default_factory=dict)

    # 时间戳
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_context_summary(self) -> Dict:
        """获取上下文摘要"""
        return {
            "npc_name": self.npc_name,
            "player_id": self.player_id,
            "player_message": self.player_message[:50],
            "has_memory": self.memory_result is not None,
            "has_affinity": self.affinity_result is not None,
            "has_dialogue": self.dialogue_result is not None
        }


class ContextManager:
    """上下文管理器"""

    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}

    def create_context(self, npc_name: str, player_id: str, player_message: str) -> str:
        """创建新上下文，返回context_id"""
        context_id = f"{npc_name}_{player_id}_{datetime.now().timestamp()}"
        self.contexts[context_id] = ConversationContext(
            npc_name=npc_name,
            player_id=player_id,
            player_message=player_message
        )
        return context_id

    def get_context(self, context_id: str) -> Optional[ConversationContext]:
        return self.contexts.get(context_id)

    def update_context(self, context_id: str, **kwargs):
        """更新上下文"""
        if context_id in self.contexts:
            for key, value in kwargs.items():
                if hasattr(self.contexts[context_id], key):
                    setattr(self.contexts[context_id], key, value)

    def cleanup(self, max_age_seconds: int = 300):
        """清理过期上下文"""
        # 实现清理逻辑
        pass
