"""Agent模块 - Multi-Agent框架"""
from typing import Dict, Any, Optional

# 子模块
from .base import BaseAgent, AgentResult
from .context import ContextManager, ConversationContext
from .memory_agent import MemoryAgent
from .affinity_agent import AffinityAgent
from .dialogue_agent import DialogueAgent
from .reflection_agent import ReflectionAgent
from .supervisor import SupervisorAgent, SupervisorConfig


class AgentFactory:
    """Agent工厂类 - 创建和管理Agent实例"""

    def __init__(self, llm, config: Dict[str, Any] = None):
        self.llm = llm
        self.config = config or {}
        self._agents: Dict[str, Any] = {}

    def create_memory_agent(self, episodic_memories: Dict = None) -> MemoryAgent:
        """创建记忆检索Agent"""
        return MemoryAgent(
            llm=self.llm,
            episodic_memories=episodic_memories or {}
        )

    def create_affinity_agent(self, relationship_manager=None) -> AffinityAgent:
        """创建好感度分析Agent"""
        return AffinityAgent(
            llm=self.llm,
            relationship_manager=relationship_manager
        )

    def create_dialogue_agent(self, npc_name: str, role_config: Dict = None) -> DialogueAgent:
        """创建对话生成Agent"""
        return DialogueAgent(
            llm=self.llm,
            npc_name=npc_name,
            role_config=role_config
        )

    def create_reflection_agent(self, npc_name: str, role_config: Dict = None) -> ReflectionAgent:
        """创建反思Agent"""
        return ReflectionAgent(
            llm=self.llm,
            npc_name=npc_name,
            role_config=role_config
        )

    def create_supervisor(
        self,
        memory_agent: MemoryAgent,
        affinity_agent: AffinityAgent,
        dialogue_agent: DialogueAgent,
        reflection_agent: Optional[ReflectionAgent] = None,
        config: SupervisorConfig = None
    ) -> SupervisorAgent:
        """创建Supervisor调度器"""
        return SupervisorAgent(
            llm=self.llm,
            memory_agent=memory_agent,
            affinity_agent=affinity_agent,
            dialogue_agent=dialogue_agent,
            reflection_agent=reflection_agent,
            config=config
        )


__all__ = [
    "BaseAgent",
    "AgentResult",
    "AgentFactory",
    "ContextManager",
    "ConversationContext",
    "MemoryAgent",
    "AffinityAgent",
    "DialogueAgent",
    "ReflectionAgent",
    "SupervisorAgent",
    "SupervisorConfig",
]
