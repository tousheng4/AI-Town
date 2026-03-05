"""BM25 检索模块 - 基于 SQLite FTS5 + jieba

SQLite FTS5 内置 BM25 算法，无需自己实现
jieba 用于中文分词

注意：SQLite FTS5 的 jieba 支持需要特定编译版本，
如果不支持会自动回退到手动分词模式。
"""

import os
import sqlite3
import json
from typing import List, Dict, Any
from datetime import datetime

from config import settings
from logger import log_info


class BM25Retriever:
    """基于 SQLite FTS5 的 BM25 检索器"""

    def __init__(self):
        self.use_bm25 = settings.MEMORY_USE_BM25
        self.db_path = settings.MEMORY_BM25_DB_PATH
        self._ensure_db()

    def _ensure_db(self):
        """确保数据库和表存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检查 FTS5 是否支持 jieba
        supports_jieba = False
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS test_fts USING fts5(tokenize='jieba', content)
            """)
            cursor.execute("DROP TABLE IF EXISTS test_fts")
            supports_jieba = True
            log_info("[BM25] FTS5 支持 jieba")
        except:
            log_info("[BM25] FTS5 不支持 jieba，将使用手动分词")
            supports_jieba = False

        self.supports_jieba = supports_jieba

        # 创建 FTS5 虚拟表
        if supports_jieba:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    npc_name,
                    player_id,
                    content,
                    metadata,
                    timestamp,
                    tokenize='jieba'
                )
            """)
        else:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    npc_name,
                    player_id,
                    content,
                    metadata,
                    timestamp
                )
            """)

        # 创建原始文档表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                npc_name TEXT NOT NULL,
                player_id TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TEXT,
                UNIQUE(npc_name, player_id, content, timestamp)
            )
        """)

        conn.commit()
        conn.close()
        log_info(f"[BM25] 数据库初始化完成: {self.db_path}")

    def _tokenize(self, text: str) -> str:
        """分词处理"""
        if self.supports_jieba:
            # FTS5 自动分词
            return text
        else:
            # 手动分词（使用空格分隔）
            import jieba
            tokens = " ".join(jieba.cut(text))
            return tokens

    def add_documents(self, npc_name: str, player_id: str, documents: List[Any]):
        """添加文档到索引

        Args:
            npc_name: NPC名称
            player_id: 玩家ID
            documents: 文档列表
        """
        if not self.use_bm25:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for doc in documents:
            if hasattr(doc, "page_content"):
                content = doc.page_content
                metadata = json.dumps(getattr(doc, "metadata", {}))
            elif isinstance(doc, dict):
                content = doc.get("content", "")
                metadata = json.dumps(doc.get("metadata", {}))
            else:
                content = str(doc)
                metadata = "{}"

            timestamp = datetime.now().isoformat()

            try:
                # 分词后的内容
                tokenized_content = self._tokenize(content)

                # 插入 FTS 表
                cursor.execute("""
                    INSERT INTO memory_fts (npc_name, player_id, content, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (npc_name, player_id, tokenized_content, metadata, timestamp))

                # 插入原始文档表
                cursor.execute("""
                    INSERT OR REPLACE INTO memory_docs (npc_name, player_id, content, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (npc_name, player_id, content, metadata, timestamp))

            except Exception as e:
                log_info(f"[BM25] 添加文档失败: {e}")

        conn.commit()
        conn.close()
        log_info(f"[BM25] 添加 {len(documents)} 个文档到索引")

    def search(
            self,
            npc_name: str,
            player_id: str,
            query: str,
            top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """BM25 检索

        Args:
            npc_name: NPC名称
            player_id: 玩家ID
            query: 查询文本
            top_k: 返回前 k 个

        Returns:
            检索结果列表
        """
        if not self.use_bm25:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 分词查询
        tokenized_query = self._tokenize(query)

        try:
            # 使用 FTS5 的 BM25 排序
            cursor.execute("""
                SELECT d.id, d.content, d.metadata, d.timestamp,
                       bm25(memory_fts) as score
                FROM memory_fts fts
                JOIN memory_docs d ON fts.content = d.content
                                  AND fts.npc_name = d.npc_name
                                  AND fts.player_id = d.player_id
                WHERE fts.npc_name = ?
                  AND fts.player_id = ?
                  AND memory_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """, (npc_name, player_id, tokenized_query, top_k))

            results = []
            for row in cursor.fetchall():
                doc_id, content, metadata, timestamp, score = row
                try:
                    metadata = json.loads(metadata) if metadata else {}
                except:
                    metadata = {}

                results.append({
                    "id": doc_id,
                    "document": content,  # 返回原始内容
                    "metadata": metadata,
                    "timestamp": timestamp,
                    "score": abs(score)  # BM25 分数为负数，取绝对值
                })

        except Exception as e:
            log_info(f"[BM25] 检索失败: {e}")
            results = []

        conn.close()
        log_info(f"[BM25] 检索: npc={npc_name}, player={player_id}, query={query}, 结果={len(results)}")

        return results

    def delete_old_documents(self, npc_name: str, player_id: str, before_timestamp: str):
        """删除旧文档

        Args:
            npc_name: NPC名称
            player_id: 玩家ID
            before_timestamp: 删除此时间之前的文档
        """
        if not self.use_bm25:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 删除 FTS 表中的数据
        cursor.execute("""
            DELETE FROM memory_fts
            WHERE npc_name = ? AND player_id = ? AND timestamp < ?
        """, (npc_name, player_id, before_timestamp))

        # 删除原始文档表中的数据
        cursor.execute("""
            DELETE FROM memory_docs
            WHERE npc_name = ? AND player_id = ? AND timestamp < ?
        """, (npc_name, player_id, before_timestamp))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        log_info(f"[BM25] 删除 {deleted} 条旧文档")


# 全局单例
_bm25_retriever = None


def get_bm25_retriever() -> BM25Retriever:
    """获取 BM25 检索器单例"""
    global _bm25_retriever
    if _bm25_retriever is None:
        _bm25_retriever = BM25Retriever()
    return _bm25_retriever
