"""短期记忆管理 - 基于 Redis"""
import json
from typing import List, Dict
from .redis_client import get_redis_client
from config import settings

KEY_PREFIX = "npc:short_term_memory:"
MAX_HISTORY = 10  # 最多保存10条对话


def get_memory_key(npc_name: str, player_id: str) -> str:
    """获取 NPC + 玩家 的短期记忆 Key"""
    return f"{KEY_PREFIX}{npc_name}:{player_id}"


def save_message(npc_name: str, player_id: str, role: str, content: str):
    """
    保存对话消息到短期记忆

    Args:
        npc_name: NPC名称
        player_id: 玩家ID
        role: 'human' 或 'ai'
        content: 消息内容
    """
    client = get_redis_client()
    key = get_memory_key(npc_name, player_id)

    # 获取现有记忆
    memory_data = client.get(key)
    if memory_data:
        messages = json.loads(memory_data)
    else:
        messages = []

    # 添加新消息（去掉首尾换行符和多余空白）
    content = content.strip()
    messages.append({
        "role": role,
        "content": content
    })

    # 限制历史长度（保留最新的 MAX_HISTORY 条）
    if len(messages) > MAX_HISTORY:
        messages = messages[-MAX_HISTORY:]

    # 保存回去，设置过期时间（ensure_ascii=False 保持中文显示）
    client.set(key, json.dumps(messages, ensure_ascii=False), ex=settings.MEMORY_TTL)


def get_history(npc_name: str, player_id: str) -> List[Dict[str, str]]:
    """
    获取 NPC 的对话历史

    Args:
        npc_name: NPC名称
        player_id: 玩家ID

    Returns:
        [{"role": "human", "content": "..."}, {"role": "ai", "content": "..."}, ...]
    """
    client = get_redis_client()
    key = get_memory_key(npc_name, player_id)

    memory_data = client.get(key)
    if memory_data:
        return json.loads(memory_data)
    return []


def clear_memory(npc_name: str, player_id: str):
    """清空 NPC 的短期记忆"""
    client = get_redis_client()
    key = get_memory_key(npc_name, player_id)
    client.delete(key)


def extend_ttl(npc_name: str, player_id: str):
    """延长短期记忆的 TTL（每次对话时调用）"""
    client = get_redis_client()
    key = get_memory_key(npc_name, player_id)
    client.expire(key, settings.MEMORY_TTL)
