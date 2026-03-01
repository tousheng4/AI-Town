"""Supervisor调度器 - 协调多Agent工作"""
import time
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .base import BaseAgent, AgentResult
from .memory_agent import MemoryAgent
from .affinity_agent import AffinityAgent
from .dialogue_agent import DialogueAgent
from .reflection_agent import ReflectionAgent

# Logger
def log_info(msg: str):
    print(f"[Supervisor] {msg}")


@dataclass
class SupervisorConfig:
    """Supervisor配置"""
    enable_reflection: bool = True  # 是否启用反思Agent
    parallel_memory_affinity: bool = True  # 是否并行获取记忆和好感度
    max_retries: int = 1


class SupervisorAgent(BaseAgent):
    """Supervisor Agent - 任务规划和调度中心"""

    def __init__(
        self,
        llm,
        memory_agent: MemoryAgent,
        affinity_agent: AffinityAgent,
        dialogue_agent: DialogueAgent,
        reflection_agent: Optional[ReflectionAgent] = None,
        config: SupervisorConfig = None
    ):
        super().__init__("Supervisor", llm)
        self.memory_agent = memory_agent
        self.affinity_agent = affinity_agent
        self.dialogue_agent = dialogue_agent
        self.reflection_agent = reflection_agent
        self.config = config or SupervisorConfig()

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """执行Supervisor任务 - 协调多Agent工作"""
        start_time = time.time()
        log_info("开始处理对话请求")

        try:
            # 提取上下文
            npc_name = context.get("npc_name")
            player_id = context.get("player_id", "player")
            player_message = context.get("player_message", "")
            role_config = context.get("role_config", {})

            # ========== 步骤1: 并行获取记忆和好感度 ==========
            log_info("步骤1: 获取记忆和好感度")
            memory_result, affinity_result = await self._get_memory_and_affinity(
                context, npc_name, player_id, player_message
            )

            if not memory_result.success:
                log_info(f"⚠️ 记忆检索失败: {memory_result.error}")
            if not affinity_result.success:
                log_info(f"⚠️ 好感度获取失败: {affinity_result.error}")

            memory_data = memory_result.data if memory_result.success else {}
            affinity_data = affinity_result.data if affinity_result.success else {}

            # 合并上下文
            context.update({
                "working_memory": memory_data.get("working_memory", []),
                "memory_context": memory_data.get("memory_context", ""),
                "episodic_memories": memory_data.get("episodic_memories", []),
                "affinity": affinity_data.get("affinity", 50.0),
                "level": affinity_data.get("level", "陌生"),
                "modifier": affinity_data.get("modifier", "礼貌友善"),
                "affinity_context": affinity_data.get("affinity_context", "")
            })

            # ========== 步骤2: 生成NPC回复 ==========
            log_info("步骤2: 生成NPC回复")
            dialogue_result = await self.dialogue_agent.execute(context)

            if not dialogue_result.success:
                log_info(f"❌ 对话生成失败: {dialogue_result.error}")
                return self._create_result(
                    success=False,
                    error=f"对话生成失败: {dialogue_result.error}"
                )

            dialogue_data = dialogue_result.data
            npc_response = dialogue_data.get("response", "")

            # ========== 步骤3: 反思优化 (可选) ==========
            if self.config.enable_reflection and self.reflection_agent:
                log_info("步骤3: 反思优化")
                reflection_context = {
                    "npc_response": npc_response,
                    "player_message": player_message,
                    "role_config": role_config,
                    "affinity_level": affinity_data.get("level", "陌生"),
                    "affinity_modifier": affinity_data.get("modifier", "礼貌友善")
                }
                reflection_result = await self.reflection_agent.execute(reflection_context)

                if reflection_result.success and reflection_result.data.get("needs_revision"):
                    npc_response = reflection_result.data.get("revised_response", npc_response)
                    log_info(f"  ✓ 回复已优化")

            # ========== 步骤4: 更新好感度 ==========
            log_info("步骤4: 更新好感度")
            update_context = {
                "npc_name": npc_name,
                "player_id": player_id,
                "player_message": player_message,
                "npc_response": npc_response
            }
            affinity_update_result = await self.affinity_agent.update_affinity(
                npc_name=npc_name,
                player_id=player_id,
                player_message=player_message,
                npc_response=npc_response
            )

            if affinity_update_result.success:
                log_info(f"  ✓ 好感度已更新")

            # ========== 步骤5: 保存记忆 ==========
            log_info("步骤5: 保存记忆")
            await self._save_memory(
                npc_name=npc_name,
                player_id=player_id,
                player_message=player_message,
                npc_response=npc_response,
                episodic_memory=context.get("episodic_memory")
            )

            execution_time = time.time() - start_time
            log_info(f"✓ 处理完成，耗时: {execution_time:.2f}秒")

            return self._create_result(
                success=True,
                data={
                    "response": npc_response,
                    "affinity": affinity_data.get("affinity", 50.0),
                    "affinity_changed": affinity_update_result.data.get("changed", False) if affinity_update_result.success else False,
                    "execution_time": execution_time,
                    "agents_used": {
                        "memory": memory_result.success,
                        "affinity": affinity_result.success,
                        "dialogue": dialogue_result.success,
                        "reflection": self.config.enable_reflection and self.reflection_agent is not None
                    }
                }
            )

        except Exception as e:
            log_info(f"❌ Supervisor执行失败: {e}")
            import traceback
            traceback.print_exc()
            return self._create_result(
                success=False,
                error=str(e)
            )

    async def _get_memory_and_affinity(
        self,
        context: Dict[str, Any],
        npc_name: str,
        player_id: str,
        player_message: str
    ) -> tuple:
        """并行或串行获取记忆和好感度"""
        memory_context = {
            "npc_name": npc_name,
            "player_id": player_id,
            "player_message": player_message,
            "episodic_memories": context.get("episodic_memories", {})
        }
        affinity_context = {
            "npc_name": npc_name,
            "player_id": player_id
        }

        if self.config.parallel_memory_affinity:
            # 并行执行
            results = await asyncio.gather(
                self.memory_agent.execute(memory_context),
                self.affinity_agent.execute(affinity_context),
                return_exceptions=True
            )

            memory_result = results[0] if not isinstance(results[0], Exception) else AgentResult(success=False, error=str(results[0]))
            affinity_result = results[1] if not isinstance(results[1], Exception) else AgentResult(success=False, error=str(results[1]))
        else:
            # 串行执行
            memory_result = await self.memory_agent.execute(memory_context)
            affinity_result = await self.affinity_agent.execute(affinity_context)

        return memory_result, affinity_result

    async def _save_memory(
        self,
        npc_name: str,
        player_id: str,
        player_message: str,
        npc_response: str,
        episodic_memory: Any
    ):
        """保存对话到记忆"""
        try:
            from memory import save_message, extend_ttl
            from datetime import datetime

            # 保存工作记忆
            save_message(npc_name, player_id, "human", player_message)
            save_message(npc_name, player_id, "ai", npc_response)
            extend_ttl(npc_name, player_id)

            # 保存情景记忆
            if episodic_memory:
                try:
                    Document = None
                    try:
                        from langchain_core.documents import Document
                    except ImportError:
                        pass

                    if Document:
                        player_doc = Document(
                            page_content=f"玩家说: {player_message}",
                            metadata={
                                "speaker": "player",
                                "player_id": player_id,
                                "timestamp": datetime.now().isoformat(),
                                "type": "player_message"
                            }
                        )
                        npc_doc = Document(
                            page_content=f"{npc_name}说: {npc_response}",
                            metadata={
                                "speaker": npc_name,
                                "player_id": player_id,
                                "timestamp": datetime.now().isoformat(),
                                "type": "npc_response"
                            }
                        )
                        episodic_memory.add_documents([player_doc, npc_doc])
                except Exception as e:
                    log_info(f"⚠️ 保存情景记忆失败: {e}")

        except Exception as e:
            log_info(f"⚠️ 保存记忆失败: {e}")
