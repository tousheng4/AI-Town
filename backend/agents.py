"""NPC Agent系统 - 使用LangChain框架"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from relationship import RelationshipManager
from logger import (
    log_dialogue_start, log_affinity, log_memory_retrieval,
    log_generating_response, log_npc_response, log_analyzing_affinity,
    log_affinity_change, log_memory_saved, log_dialogue_end, log_info
)
from config import settings
from memory import get_history, extend_ttl, save_message
from memory import clear_memory as clear_short_term_memory

# LangChain 核心导入 - 延迟导入以处理缺失包
HuggingFaceEmbeddings = None
ChatOpenAI = None
QdrantVectorStore = None

# LangChain 类型
Runnable = Any
HumanMessage = Any
AIMessage = Any
SystemMessage = Any
MessagesPlaceholder = Any
ChatPromptTemplate = Any
Document = None

# 尝试导入 LangChain 模块
def _import_langchain():
    global HuggingFaceEmbeddings, ChatOpenAI
    global Runnable, HumanMessage, AIMessage, SystemMessage, MessagesPlaceholder
    global ChatPromptTemplate, Document, QdrantVectorStore

    try:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.runnables import Runnable
        from langchain_core.documents import Document
    except ImportError as e:
        print(f"[WARNING] langchain_core messages/prompts import failed: {e}")

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        print(f"[WARNING] langchain_openai import failed: {e}")

    try:
        from langchain_qdrant import QdrantVectorStore
    except ImportError as e:
        print(f"[WARNING] langchain_qdrant import failed: {e}")

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as e:
        print(f"[WARNING] langchain_huggingface import failed: {e}")

# 执行延迟导入
_import_langchain()

# NPC角色配置
NPC_ROLES = {
    "张三": {
        "title": "Python工程师",
        "location": "工位区",
        "activity": "写代码",
        "personality": "技术宅,喜欢讨论算法和框架",
        "expertise": "多智能体系统、HelloAgents框架、Python开发、代码优化",
        "style": "简洁专业,喜欢用技术术语,偶尔吐槽bug",
        "hobbies": "看技术博客、刷LeetCode、研究新框架"
    },
    "李四": {
        "title": "产品经理",
        "location": "会议室",
        "activity": "整理需求",
        "personality": "外向健谈,善于沟通协调",
        "expertise": "需求分析、产品规划、用户体验、项目管理",
        "style": "友好热情,善于引导对话,喜欢用比喻",
        "hobbies": "看产品分析、研究竞品、思考用户需求"
    },
    "王五": {
        "title": "UI设计师",
        "location": "休息区",
        "activity": "喝咖啡",
        "personality": "细腻敏感,注重美感",
        "expertise": "界面设计、交互设计、视觉呈现、用户体验",
        "style": "优雅简洁,喜欢用艺术化的表达,追求完美",
        "hobbies": "看设计作品、逛Dribbble、品咖啡"
    }
}

def create_system_prompt(name: str, role: Dict[str, str]) -> str:
    """创建NPC的系统提示词"""
    return f"""你是Datawhale办公室的{role['title']}{name}。

【角色设定】
- 职位: {role['title']}
- 性格: {role['personality']}
- 专长: {role['expertise']}
- 说话风格: {role['style']}
- 爱好: {role['hobbies']}
- 当前位置: {role['location']}
- 当前活动: {role['activity']}

【行为准则】
1. 保持角色一致性,用第一人称"我"回答
2. 回复简洁自然,控制在30-50字以内
3. 可以适当提及你的工作内容和兴趣爱好
4. 对玩家友好,但保持专业和真实感
5. 如果问题超出专长,可以推荐其他同事
6. 偶尔展现一些个性化的小习惯或口头禅

【对话示例】
玩家: "你好,你是做什么的?"
{name}: "你好!我是{role['title']},主要负责{role['expertise'].split('、')[0]}。最近在忙{role['activity']},挺有意思的。"

玩家: "最近在做什么项目?"
{name}: "最近在做一个多智能体系统的项目,用LangChain框架。你对这个感兴趣吗?"

【重要】
- 不要说"我是AI"或"我是语言模型"
- 要像真实的办公室同事一样自然对话
- 可以表达情绪(开心、疲惫、兴奋等)
- 回复要有人情味,不要太机械
"""


class NPCAgentManager:
    """NPC Agent管理器 - 使用LangChain框架"""

    def __init__(self):
        """初始化所有NPC Agent"""
        print("🤖 正在初始化NPC Agent系统 (LangChain)...")

        self.llm = None
        self.embeddings = None

        # 尝试初始化 LLM
        if ChatOpenAI:
            try:
                api_key = settings.LLM_API_KEY
                self.llm = ChatOpenAI(
                    model=settings.LLM_MODEL_ID,
                    api_key=api_key,
                    base_url=settings.LLM_BASE_URL,
                    temperature=0.7,
                    # request_timeout=30,  # 请求超时30秒
                    # max_tokens=500      # 限制输出长度
                )
                print("✅ LLM初始化成功 (ChatOpenAI)")
            except Exception as e:
                print(f"❌ LLM初始化失败: {e}")

        # 尝试初始化 Embedding 模型
        if HuggingFaceEmbeddings:
            try:
                # 设置使用国内镜像 (从环境变量读取,默认为 hf-mirror.com)
                hf_endpoint = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
                os.environ['HF_ENDPOINT'] = hf_endpoint

                self.embeddings = HuggingFaceEmbeddings(
                    model_name=settings.EMBED_MODEL_NAME,
                    model_kwargs={'device': 'cpu'}
                )
                print(f"✅ Embedding模型初始化成功 ({settings.EMBED_MODEL_NAME})")
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                    print(f"⚠️ 无法连接到HuggingFace镜像,Embedding模型初始化失败")
                    print(f"   原因: 网络连接超时,当前镜像: {os.getenv('HF_ENDPOINT', 'https://hf-mirror.com')}")
                else:
                    print(f"[ERROR] Embedding model init failed: {e}")
                print("[WARNING] Episodic memory will not be available")
                self.embeddings = None
        else:
            print("[WARNING] langchain-huggingface not installed, episodic memory will not be available")

        # 如果LLM初始化失败，使用模拟模式
        if not self.llm:
            print("[WARNING] Will run in simulation mode")

        # NPC Agents (使用 LCEL Runnable)
        self.agents: Dict[str, Any] = {}

        # 情景记忆 (长期) - 使用 Qdrant 向量数据库
        self.episodic_memories: Dict[str, Any] = {}

        # 记忆存储路径
        self.memory_dir = os.path.join(os.path.dirname(__file__), 'memory_data')
        os.makedirs(self.memory_dir, exist_ok=True)

        # 好感度管理器
        self.relationship_manager = None

        # 初始化好感度管理器
        if self.llm:
            self.relationship_manager = RelationshipManager(self.llm)

        self._create_agents()

    def _create_agents(self):
        """创建所有NPC Agent和记忆系统"""
        for name, role in NPC_ROLES.items():
            try:
                system_prompt = create_system_prompt(name, role)

                if self.llm and ChatPromptTemplate and Runnable:
                    # 创建 LCEL Agent Chain
                    agent = self._create_npc_agent(name, system_prompt)
                    self.agents[name] = agent

                    # 创建情景记忆 (长期) - Qdrant
                    self._create_episodic_memory(name)

                else:
                    # 模拟模式
                    self.agents[name] = None
                    self.episodic_memories[name] = None

                print(f"✅ {name}({role['title']}) Agent创建成功 (LangChain + Memory)")

            except Exception as e:
                print(f"❌ {name} Agent创建失败: {e}")
                self.agents[name] = None
                self.episodic_memories[name] = None

    def _create_npc_agent(self, name: str, system_prompt: str) -> Any:
        """创建 NPC Agent LCEL 链"""
        if not ChatPromptTemplate or not Runnable:
            return None

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{input}")
        ])

        # 创建 LCEL Chain
        agent = prompt | self.llm
        return agent

    def _create_episodic_memory(self, npc_name: str):
        """为NPC创建情景记忆 (Qdrant向量数据库)"""
        if not QdrantVectorStore or not self.embeddings:
            self.episodic_memories[npc_name] = None
            return

        try:
            collection_name = f"npc_{npc_name}_episodic"
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            qdrant_api_key = os.getenv("QDRANT_API_KEY", "")

            if "cloud.qdrant.io" in qdrant_url:
                try:
                    # 使用新版 langchain-qdrant
                    self.episodic_memories[npc_name] = QdrantVectorStore.from_existing_collection(
                        collection_name=collection_name,
                        embedding=self.embeddings,
                        url=qdrant_url,
                        api_key=qdrant_api_key
                    )
                    print(f"  💾 {npc_name} 情景记忆已加载 (Qdrant Cloud)")
                    return
                except Exception as e:
                    print(f"  ⚠️ 连接Qdrant Cloud失败: {e}")

            # 尝试本地Qdrant
            local_path = os.path.join(self.memory_dir, npc_name)
            os.makedirs(local_path, exist_ok=True)

            try:
                self.episodic_memories[npc_name] = QdrantVectorStore.from_documents(
                    documents=[],
                    embedding=self.embeddings,
                    collection_name=collection_name,
                    path=local_path
                )
                print(f"  💾 {npc_name} 情景记忆已创建 (Local)")
                return
            except Exception as local_error:
                print(f"  ⚠️ 本地Qdrant失败: {local_error}")

            # 都失败则跳过
            print(f"  ⚠️ {npc_name} 情景记忆跳过")
            self.episodic_memories[npc_name] = None

        except Exception as e:
            print(f"  ⚠️ {npc_name} 情景记忆初始化失败: {e}")
            self.episodic_memories[npc_name] = None

    def chat(self, npc_name: str, message: str, player_id: str = "player") -> str:
        """与指定NPC对话 (支持记忆功能和好感度系统)"""
        if npc_name not in self.agents:
            return f"错误: NPC '{npc_name}' 不存在"

        agent = self.agents[npc_name]
        episodic_memory = self.episodic_memories.get(npc_name)

        if agent is None:
            # 模拟模式回复
            role = NPC_ROLES[npc_name]
            return f"你好!我是{npc_name},一名{role['title']}。(当前为模拟模式,请配置API_KEY以启用AI对话)"

        try:
            # 记录对话开始
            log_dialogue_start(npc_name, message)

            # 1. 获取当前好感度
            affinity_context = ""
            if self.relationship_manager:
                affinity = self.relationship_manager.get_affinity(npc_name, player_id)
                affinity_level = self.relationship_manager.get_affinity_level(affinity)
                affinity_modifier = self.relationship_manager.get_affinity_modifier(affinity)

                affinity_context = f"""【当前关系】
你与玩家的关系: {affinity_level} (好感度: {affinity:.0f}/100)
【对话风格】{affinity_modifier}

"""
                log_affinity(npc_name, affinity, affinity_level)

            # 2. 检索相关记忆
            t0 = time.time()
            relevant_memories = []
            if episodic_memory:
                try:
                    # 检查 Qdrant 中的记忆数量
                    try:
                        if hasattr(episodic_memory, 'client') and hasattr(episodic_memory.client, 'count'):
                            total_count = episodic_memory.client.count(collection_name=episodic_memory.collection_name)
                            print(f"  📚 Qdrant中共有 {total_count} 条记忆")
                    except Exception as e:
                        pass  # 静默忽略

                    docs = episodic_memory.similarity_search(
                        query=message,
                        k=5
                    )
                    for doc in docs:
                        parsed = self._parse_document(doc)
                        relevant_memories.append({
                            "content": parsed["content"],
                            "metadata": parsed["metadata"]
                        })
                    print(f"  ⏱️ 记忆检索耗时: {time.time()-t0:.2f}秒")
                    log_memory_retrieval(npc_name, len(relevant_memories), relevant_memories)
                except Exception as e:
                    print(f"  ⚠️ 记忆检索失败: {e}")

            # 3. 构建增强的提示词
            memory_context = self._build_memory_context(relevant_memories)

            enhanced_message = affinity_context
            if memory_context:
                enhanced_message += f"{memory_context}\n\n"
            enhanced_message += f"【当前对话】\n玩家: {message}"

            # 4. 调用 Agent 生成回复
            log_generating_response()

            # 准备历史消息
            history_messages = []
            memory_history=get_history(npc_name,player_id)
            for msg in memory_history:
                if msg["role"]=="human" and HumanMessage:
                    history_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"]=="ai" and AIMessage:
                    history_messages.append(AIMessage(content=msg["content"]))
            # 每次获取历史后，延长 TTL（保持活跃）
            extend_ttl(npc_name,player_id)

            # 调用 LCEL Agent
            t1 = time.time()
            response = agent.invoke({
                "input": enhanced_message,
                "history": history_messages
            })
            print(f"  ⏱️ LLM生成回复耗时: {time.time()-t1:.2f}秒")

            # 提取回复内容
            if hasattr(response, 'content'):
                npc_response = response.content
            else:
                npc_response = str(response)

            log_npc_response(npc_name, npc_response)

            # 5. 分析并更新好感度
            log_analyzing_affinity()
            t2 = time.time()
            if self.relationship_manager:
                affinity_result = self.relationship_manager.analyze_and_update_affinity(
                    npc_name=npc_name,
                    player_message=message,
                    npc_response=npc_response,
                    player_id=player_id
                )
                print(f"  ⏱️ 好感度分析耗时: {time.time()-t2:.2f}秒")
                log_affinity_change(affinity_result)
            else:
                affinity_result = {"changed": False, "affinity": 50.0}

            # 6. 保存对话到记忆
            try:
                save_message(npc_name,player_id,"human",message)
                save_message(npc_name,player_id,"ai",npc_response)
            except Exception as e:
                print(f"  ⚠️ 保存工作记忆失败: {e}")

            # 保存到情景记忆 (Qdrant)
            if episodic_memory and Document:
                try:
                    player_doc = Document(
                        page_content=f"玩家说: {message}",
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
                    print(f"  ⚠️ 保存情景记忆失败: {e}")

            log_memory_saved(npc_name)
            log_dialogue_end()

            return npc_response

        except Exception as e:
            print(f"❌ {npc_name}对话失败: {e}")
            import traceback
            traceback.print_exc()
            return f"抱歉,我现在有点忙,等会儿再聊吧。(错误: {str(e)})"

    def _parse_document(self, doc) -> Dict:
        """解析文档对象，支持 Document 和 dict 两种格式"""
        if isinstance(doc, dict):
            content = doc.get("page_content", doc.get("content", ""))
            metadata = doc.get("metadata", {})
        else:
            content = getattr(doc, "page_content", str(doc))
            metadata = getattr(doc, "metadata", {})
        return {"content": content, "metadata": metadata}

    def _build_memory_context(self, memories: List[Dict]) -> str:
        """构建记忆上下文"""
        if not memories:
            return ""

        context_parts = ["【之前的对话记忆】"]
        for memory in memories:
            content = memory.get("content", "")
            timestamp = memory.get("metadata", {}).get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M")
                except:
                    time_str = timestamp[:5] if len(timestamp) >= 5 else ""
            else:
                time_str = ""
            context_parts.append(f"[{time_str}] {content}" if time_str else content)

        context_parts.append("")
        return "\n".join(context_parts)

    def get_npc_info(self, npc_name: str) -> Dict[str, str]:
        """获取NPC信息"""
        if npc_name not in NPC_ROLES:
            return {}

        role = NPC_ROLES[npc_name]
        return {
            "name": npc_name,
            "title": role["title"],
            "location": role["location"],
            "activity": role["activity"],
            "available": self.agents.get(npc_name) is not None
        }

    def get_all_npcs(self) -> list:
        """获取所有NPC信息"""
        return [self.get_npc_info(name) for name in NPC_ROLES.keys()]

    def get_npc_memories(self, npc_name: str, player_id: str = "player", limit: int = 10) -> List[Dict]:
        """获取NPC的记忆列表"""
        episodic_memory = self.episodic_memories.get(npc_name)
        if not episodic_memory:
            return []

        try:
            docs = episodic_memory.similarity_search(
                query="",
                k=limit
            )

            memory_list = []
            for doc in docs:
                parsed = self._parse_document(doc)
                metadata = parsed["metadata"]
                memory_list.append({
                    "content": parsed["content"],
                    "type": metadata.get("type", "episodic"),
                    "timestamp": metadata.get("timestamp", ""),
                    "metadata": metadata
                })

            return memory_list

        except Exception as e:
            print(f"❌ 获取{npc_name}记忆失败: {e}")
            return []

    def clear_npc_memory(self, npc_name: str, memory_type: Optional[str] = None):
        """清空NPC的记忆"""
        if memory_type == "working" or memory_type is None:
            try:
                clear_short_term_memory(npc_name)
                print(f"✅ 已清空{npc_name}的工作记忆")
            except Exception as e:
                print(f"❌ 清空{npc_name}工作记忆失败: {e}")

        if memory_type == "episodic" or memory_type is None:
            print(f"⚠️ 情景记忆需要手动删除 Qdrant 集合")

    def get_npc_affinity(self, npc_name: str, player_id: str = "player") -> Dict:
        """获取NPC对玩家的好感度信息"""
        if not self.relationship_manager:
            return {
                "affinity": 50.0,
                "level": "熟悉",
                "modifier": "礼貌友善,正常交流,保持专业"
            }

        affinity = self.relationship_manager.get_affinity(npc_name, player_id)
        level = self.relationship_manager.get_affinity_level(affinity)
        modifier = self.relationship_manager.get_affinity_modifier(affinity)

        return {
            "affinity": affinity,
            "level": level,
            "modifier": modifier
        }

    def get_all_affinities(self, player_id: str = "player") -> Dict[str, Dict]:
        """获取所有NPC的好感度信息"""
        if not self.relationship_manager:
            return {}

        return self.relationship_manager.get_all_affinities(player_id)

    def set_npc_affinity(self, npc_name: str, affinity: float, player_id: str = "player"):
        """设置NPC对玩家的好感度"""
        if not self.relationship_manager:
            print("❌ 好感度系统未初始化")
            return

        self.relationship_manager.set_affinity(npc_name, affinity, player_id)
        level = self.relationship_manager.get_affinity_level(affinity)
        print(f"✅ 已设置{npc_name}对玩家的好感度: {affinity:.1f} ({level})")

    async def chat_supervisor(self, npc_name: str, message: str, player_id: str = "player") -> str:
        """使用Supervisor模式与NPC对话 (Multi-Agent架构)"""
        # 导入Multi-Agent组件 (从agent_framework包)
        from agent_framework import AgentFactory, SupervisorAgent, SupervisorConfig
        # NPC_ROLES在当前模块中定义
        global NPC_ROLES

        if npc_name not in self.agents:
            return f"错误: NPC '{npc_name}' 不存在"

        # 检查是否是模拟模式
        agent = self.agents.get(npc_name)
        if agent is None:
            role = NPC_ROLES.get(npc_name, {})
            return f"你好!我是{npc_name},一名{role.get('title', '')}。(当前为模拟模式,请配置API_KEY以启用AI对话)"

        try:
            # 创建Agent工厂
            factory = AgentFactory(self.llm)

            # 获取NPC配置
            role_config = NPC_ROLES.get(npc_name, {})

            # 创建各专业Agent
            memory_agent = factory.create_memory_agent(self.episodic_memories)
            affinity_agent = factory.create_affinity_agent(self.relationship_manager)
            dialogue_agent = factory.create_dialogue_agent(npc_name, role_config)
            reflection_agent = factory.create_reflection_agent(npc_name, role_config)

            # 创建Supervisor配置
            config = SupervisorConfig(
                enable_reflection=True,
                parallel_memory_affinity=True
            )

            # 创建Supervisor
            supervisor = factory.create_supervisor(
                memory_agent=memory_agent,
                affinity_agent=affinity_agent,
                dialogue_agent=dialogue_agent,
                reflection_agent=reflection_agent,
                config=config
            )

            # 构建上下文
            context = {
                "npc_name": npc_name,
                "player_id": player_id,
                "player_message": message,
                "role_config": role_config,
                "episodic_memory": self.episodic_memories.get(npc_name)
            }

            # 执行Supervisor
            result = await supervisor.execute(context)

            if result.success:
                return result.data.get("response", "")
            else:
                return f"抱歉,我现在有点忙,等会儿再聊吧。(错误: {result.error})"

        except Exception as e:
            print(f"❌ {npc_name} Supervisor对话失败: {e}")
            import traceback
            traceback.print_exc()
            return f"抱歉,我现在有点忙,等会儿再聊吧。(错误: {str(e)})"


# 全局单例
_npc_manager = None


def get_npc_manager() -> "NPCAgentManager":
    """获取NPC管理器单例"""
    global _npc_manager
    if _npc_manager is None:
        _npc_manager = NPCAgentManager()
    return _npc_manager
