"""数据模型定义"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    """单个NPC对话请求"""
    npc_name: str = Field(..., description="NPC名称")
    message: str = Field(..., description="玩家消息")
    player_id: str = Field(default="player", description="玩家ID")

    class Config:
        json_schema_extra = {
            "example": {
                "npc_name": "张三",
                "message": "你好,你在做什么?",
                "player_id": "player"
            }
        }

class ChatResponse(BaseModel):
    """单个NPC对话响应"""
    npc_name: str = Field(..., description="NPC名称")
    npc_title: str = Field(..., description="NPC职位")
    message: str = Field(..., description="NPC回复")
    success: bool = Field(default=True, description="是否成功")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "npc_name": "张三",
                "npc_title": "Python工程师",
                "message": "你好!我正在写代码,调试一个多智能体系统的bug。",
                "success": True
            }
        }

class NPCInfo(BaseModel):
    """NPC信息"""
    name: str = Field(..., description="NPC名称")
    title: str = Field(..., description="NPC职位")
    location: str = Field(..., description="NPC位置")
    activity: str = Field(..., description="当前活动")
    available: bool = Field(default=True, description="是否可对话")

class NPCStatusResponse(BaseModel):
    """NPC状态响应"""
    dialogues: Dict[str, str] = Field(..., description="NPC当前对话内容")
    last_update: Optional[datetime] = Field(None, description="上次更新时间")
    next_update_in: int = Field(..., description="下次更新倒计时(秒)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dialogues": {
                    "张三": "终于把这个bug修复了,测试通过!",
                    "李四": "下周的产品评审会需要准备一下资料。",
                    "王五": "这个界面的配色方案还需要优化一下。"
                },
                "last_update": "2024-01-15T10:30:00",
                "next_update_in": 25
            }
        }

class NPCListResponse(BaseModel):
    """NPC列表响应"""
    npcs: List[NPCInfo] = Field(..., description="NPC列表")
    total: int = Field(..., description="NPC总数")


# ============== 三层记忆系统数据模型 ==============

class EpisodicMemoryBlock(BaseModel):
    """情景记忆块 - 事件压缩后的结构化记忆

    这是三层记忆系统中"Episodic"层的核心数据结构。
    相比逐句存储，事件块能更好地表达对话中的完整事件。

    字段说明：
    - event_summary: 一句话概括发生了什么（压缩后的核心信息）
    - participants: 参与对话的人（玩家和NPC）
    - entities: 涉及的实体（话题、人名、地点、物品等）
    - importance: 重要度 0-1（由LLM打分，影响检索排序）
    - timestamp_range: 事件时间范围
    - raw_turn_ids: 原始对话ID列表（用于追溯）
    """
    event_summary: str = Field(..., description="事件摘要，一句话概括")
    participants: List[str] = Field(default_factory=list, description="参与者列表")
    entities: List[str] = Field(default_factory=list, description="涉及实体（话题/人物/地点）")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要度 0-1")
    timestamp_range: str = Field(default="", description="时间范围")
    raw_turn_ids: List[str] = Field(default_factory=list, description="原始对话ID")


class ProfileFact(BaseModel):
    """Profile事实库 - 稳定事实信息

    这是三层记忆系统中"Semantic/Profile"层的核心数据结构。
    存储从对话中抽取的长期稳定信息。

    字段说明：
    - category: 事实类别（preferences/taboos/promises/goals/relationship_tags）
    - content: 事实内容
    - source_turn_id: 来源对话ID
    - extracted_at: 抽取时间
    - confidence: 置信度 0-1
    """
    category: str = Field(..., description="事实类别: preferences/taboos/promises/goals/relationship_tags")
    content: str = Field(..., description="事实内容")
    source_turn_id: str = Field(default="", description="来源对话ID")
    extracted_at: str = Field(default_factory=lambda: datetime.now().isoformat(), description="抽取时间")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度 0-1")


class MemoryRetrievalResult(BaseModel):
    """记忆检索结果 - 加权评分

    用于返回检索结果，包含各维度的评分。
    最终分数 = α×相似度 + β×重要度 + γ×新近度
    """
    content: str = Field(..., description="记忆内容")
    metadata: Dict = Field(default_factory=dict, description="元数据")
    similarity_score: float = Field(default=0.0, description="向量相似度分数")
    importance_score: float = Field(default=0.0, description="重要度分数")
    recency_score: float = Field(default=0.0, description="新近度分数")
    final_score: float = Field(default=0.0, description="最终加权分数")

