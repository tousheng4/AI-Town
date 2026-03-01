"""对话生成Agent"""
import time
from typing import Dict, Any

# NPC_ROLES will be passed via role_config parameter to avoid circular imports
from .base import BaseAgent, AgentResult

# LangChain 延迟导入
ChatPromptTemplate = None
MessagesPlaceholder = None
HumanMessage = None
AIMessage = None


def _import_langchain():
    global ChatPromptTemplate, MessagesPlaceholder, HumanMessage, AIMessage
    try:
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.messages import HumanMessage, AIMessage
    except ImportError:
        pass


_import_langchain()


class DialogueAgent(BaseAgent):
    """对话生成Agent"""

    def __init__(self, llm, npc_name: str, role_config: Dict = None):
        super().__init__(f"DialogueAgent_{npc_name}", llm)
        self.npc_name = npc_name
        self.role_config = role_config or {}
        self.agent = None

        if llm and ChatPromptTemplate:
            self._create_agent_chain()

    def _create_agent_chain(self):
        """创建对话链"""
        system_prompt = self._create_system_prompt()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", "{input}")
        ])

        self.agent = prompt | self.llm

    def _create_system_prompt(self) -> str:
        role = self.role_config
        return f"""你是Datawhale办公室的{role.get('title', '')}{self.npc_name}。

  【角色设定】
  - 职位: {role.get('title', '')}
  - 性格: {role.get('personality', '')}
  - 专长: {role.get('expertise', '')}
  - 说话风格: {role.get('style', '')}
  - 爱好: {role.get('hobbies', '')}

  【行为准则】
  1. 保持角色一致性,用第一人称"我"回答
  2. 回复简洁自然,控制在30-50字以内
  3. 不要说"我是AI"
  """

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """执行对话生成"""
        start_time = time.time()

        try:
            # 从上下文获取增强信息
            affinity_context = context.get("affinity_context", "")
            memory_context = context.get("memory_context", "")
            player_message = context.get("player_message", "")
            working_memory = context.get("working_memory", [])

            # 构建增强的输入
            enhanced_input = affinity_context
            if memory_context:
                enhanced_input += f"{memory_context}\n\n"
            enhanced_input += f"【当前对话】\n玩家: {player_message}"

            # 准备历史消息
            history_messages = []
            if HumanMessage and AIMessage:
                for msg in working_memory:
                    if msg.get("role") == "human":
                        history_messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "ai":
                        history_messages.append(AIMessage(content=msg.get("content", "")))

            # 调用LLM
            if self.agent:
                response = self.agent.invoke({
                    "input": enhanced_input,
                    "history": history_messages
                })
                npc_response = getattr(response, "content", str(response))
            else:
                npc_response = f"你好!我是{self.npc_name}。(模拟模式)"

            return self._create_result(
                success=True,
                data={"response": npc_response, "input": enhanced_input}
            )

        except Exception as e:
            return self._create_result(
                success=False,
                error=str(e)
            )
