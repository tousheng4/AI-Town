"""Profile事实库管理器

职责：
1. 存储和管理NPC-玩家之间的长期稳定事实
2. 从对话中抽取并更新事实
3. 提供Profile上下文用于增强Prompt

数据结构：
{
    "npc_name": "张三",
    "player_id": "player1",
    "facts": {
        "preferences": [
            {"content": "喜欢喝咖啡不加糖", "extracted_at": "...", "confidence": 0.9}
        ],
        "taboos": [...],
        "promises": [...],
        "goals": [...],
        "relationship_tags": [...]
    },
    "last_updated": "2026-03-03T10:00:00"
}

存储位置：profile_data/{npc_name}_{player_id}.json
"""

import json
import os
from datetime import datetime
from typing import Dict, List

from config import settings


class ProfileManager:
    """Profile事实库管理器"""

    def __init__(self):
        self.data_dir = settings.PROFILE_DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_profile_path(self, npc_name: str, player_id: str) -> str:
        """获取Profile文件路径"""
        return os.path.join(self.data_dir, f"{npc_name}_{player_id}.json")

    def _load_profile(self, npc_name: str, player_id: str) -> Dict:
        """加载Profile"""
        path = self._get_profile_path(npc_name, player_id)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ProfileManager] 加载失败: {e}")
        return self._create_empty_profile(npc_name, player_id)

    def _save_profile(self, npc_name: str, player_id: str, profile: Dict):
        """保存Profile"""
        path = self._get_profile_path(npc_name, player_id)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ProfileManager] 保存失败: {e}")

    def _create_empty_profile(self, npc_name: str, player_id: str) -> Dict:
        """创建空的Profile"""
        return {
            "npc_name": npc_name,
            "player_id": player_id,
            "facts": {
                "preferences": [],
                "taboos": [],
                "promises": [],
                "goals": [],
                "relationship_tags": []
            },
            "last_updated": datetime.now().isoformat()
        }

    def update_from_extraction(self, npc_name: str, player_id: str, extracted_facts: List[Dict]):
        """从抽取结果更新Profile

        Args:
            extracted_facts: 由MemoryConsolidationAgent抽取的事实列表
                             格式: [{"category": "preferences", "content": "...", "confidence": 0.9}, ...]
        """
        if not extracted_facts:
            return

        profile = self._load_profile(npc_name, player_id)
        facts = profile["facts"]

        for fact in extracted_facts:
            category = fact.get("category", "")
            content = fact.get("content", "")
            confidence = fact.get("confidence", 0.5)

            # 验证category
            if category not in facts:
                continue

            # 检查是否已存在（避免重复）
            existing = [f for f in facts[category] if f["content"] == content]
            if existing:
                # 更新置信度（取较高值）
                existing[0]["confidence"] = max(existing[0]["confidence"], confidence)
                existing[0]["last_accessed"] = datetime.now().isoformat()
            else:
                # 添加新事实
                facts[category].append({
                    "content": content,
                    "confidence": confidence,
                    "extracted_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat()
                })

        profile["last_updated"] = datetime.now().isoformat()
        self._save_profile(npc_name, player_id, profile)
        print(f"[ProfileManager] 已更新 {npc_name}-{player_id} 的Profile，新增 {len(extracted_facts)} 条事实")

    def get_profile_context(self, npc_name: str, player_id: str) -> str:
        """获取Profile上下文（用于增强Prompt）

        Returns:
            格式化的Profile上下文字符串
        """
        profile = self._load_profile(npc_name, player_id)
        facts = profile["facts"]

        context_parts = ["【玩家Profile】"]

        # 偏好
        if facts["preferences"]:
            prefs = [f["content"] for f in facts["preferences"]]
            context_parts.append(f"玩家偏好: {', '.join(prefs)}")

        # 禁忌
        if facts["taboos"]:
            taboos = [f["content"] for f in facts["taboos"]]
            context_parts.append(f"玩家禁忌: {', '.join(taboos)}")

        # 承诺
        if facts["promises"]:
            promises = [f["content"] for f in facts["promises"]]
            context_parts.append(f"玩家承诺: {', '.join(promises)}")

        # 目标
        if facts["goals"]:
            goals = [f["content"] for f in facts["goals"]]
            context_parts.append(f"玩家目标: {', '.join(goals)}")

        # 关系标签
        if facts["relationship_tags"]:
            tags = [f["content"] for f in facts["relationship_tags"]]
            context_parts.append(f"关系标签: {', '.join(tags)}")

        if len(context_parts) == 1:
            return ""

        context_parts.append("")
        return "\n".join(context_parts)

    def get_all_facts(self, npc_name: str, player_id: str) -> Dict:
        """获取所有事实"""
        return self._load_profile(npc_name, player_id)

    def clear_profile(self, npc_name: str, player_id: str):
        """清空Profile"""
        profile = self._create_empty_profile(npc_name, player_id)
        self._save_profile(npc_name, player_id, profile)


# 全局单例
_profile_manager = None


def get_profile_manager() -> ProfileManager:
    """获取Profile管理器单例"""
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ProfileManager()
    return _profile_manager
