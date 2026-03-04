"""记忆重排模块 - 两阶段检索的第二阶段

使用 BGE Reranker 模型对召回的记忆进行重排，
只靠 embedding 相似度很难稳定，用 cross-encoder 重排效果更好。
CrossEncoder：一种神经网络模型，输入是 [query, document] 文本对，输出一个相关度分数
不同于 embedding（分开编码），Cross-Encoder 把 query 和 document 一起编码，能捕获更复杂的语义关系

第一阶段：Qdrant dense 召回 k=50（带 player_id 过滤）
第二阶段：用 reranker 重排，取 top-k
"""

from typing import List, Dict, Any, Optional

from config import settings
from logger import log_info


class MemoryReranker:
    """记忆重排器"""

    def __init__(self):
        self.model_name = settings.RERANKER_MODEL_NAME
        self.device = settings.RERANKER_DEVICE
        self.top_k = settings.RERANKER_TOP_K
        self.model = None
        self.tokenizer = None

    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                import os
                # 设置 HuggingFace 镜像
                if "HF_ENDPOINT" not in os.environ:
                    os.environ["HF_ENDPOINT"] = settings.HF_ENDPOINT

                from sentence_transformers import CrossEncoder
                log_info(f"[Reranker] 加载模型: {self.model_name}, 镜像={os.environ.get('HF_ENDPOINT')}")
                self.model = CrossEncoder(
                    self.model_name,
                    max_length=512,
                    device=self.device
                )
                log_info(f"[Reranker] 模型加载成功，device={self.device}")
            except ImportError:
                log_info("[Reranker] 需要安装 sentence-transformers: pip install sentence-transformers")
                raise ImportError("需要安装 sentence-transformers")
            except Exception as e:
                log_info(f"[Reranker] 模型加载失败: {e}")
                raise

    def rerank(
            self,
            query: str,
            documents: List[Any],
            top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """对文档进行重排

        Args:
            query: 查询文本
            documents: 文档列表（可以是 Document 对象或字符串）
            top_k: 返回前k个，默认为配置值

        Returns:
            重排后的文档列表，每个元素包含:
                - document: 原始文档对象
                - score: 重排分数
                - content: 文档内容
        """
        if not documents:
            return []

        k = top_k or self.top_k

        # 加载模型
        self._load_model()

        # 转换为字符串列表
        doc_texts = []
        for doc in documents:
            if hasattr(doc, "page_content"):
                doc_texts.append(doc.page_content)
            elif isinstance(doc, str):
                doc_texts.append(doc)
            elif isinstance(doc, dict):
                doc_texts.append(doc.get("content", str(doc)))
            else:
                doc_texts.append(str(doc))

        # 构建 query-document 对
        pairs = [[query, doc] for doc in doc_texts]

        try:
            # 获取重排分数
            scores = self.model.predict(pairs)

            # 构建结果列表
            results = []
            for i, (doc, score) in enumerate(zip(documents, scores)):
                results.append({
                    "document": doc,
                    "score": float(score),
                    "content": doc_texts[i]
                })

            # 按分数降序排序
            results.sort(key=lambda x: x["score"], reverse=True)

            log_info(f"[Reranker] 重排完成: 输入{len(documents)}个，输出{min(k, len(results))}个")

            return results[:k]

        except Exception as e:
            log_info(f"[Reranker] 重排失败: {e}")
            # 失败时返回原始顺序
            return [{"document": doc, "score": 0.0, "content": doc_texts[i]}
                    for i, doc in enumerate(documents[:k])]


# 全局单例
_reranker = None


def get_reranker() -> MemoryReranker:
    """获取重排器单例"""
    global _reranker
    if _reranker is None:
        _reranker = MemoryReranker()
    return _reranker
