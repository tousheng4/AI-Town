"""Agent基类定义"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AgentResult:
    """Agent执行结果"""
    success:bool
    data:Any=None
    error:str=""
    agent_name: str = ""
    execution_time: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp=datetime.now().isoformat()

class BaseAgent(ABC):
    """Agent抽象基类"""

    def __init__(self,name:str,llm:Any=None):
        self.name=name
        self.llm=llm

    @abstractmethod
    async def execute(self,context:Dict[str,Any]) -> AgentResult:
        """执行Agent任务"""
        pass

    def _create_result(self,success:bool,data:Any=None,error:str="") -> AgentResult:
        return AgentResult(
            success=success,
            data=data,
            error=error,
            agent_name=self.name
        )