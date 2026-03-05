"""MMR 多样性约束模块

MMR (Maximal Marginal Relevance) 公式：
MMR = λ * sim(query, doc) - (1-λ) * max(sim(doc, selected_docs))

λ 越接近 1：越看重相关性
λ 越接近 0：越看重多样性
"""

from typing import List, Dict, Any
from config import settings
from logger import log_info


class MMRScorer:
    """MMR 多样性评分器"""

    def __init__(self):
        self.use_mmr = settings.MEMORY_USE_MMR
        self.lambda_param = settings.MEMORY_MMR_LAMBDA
        self.default_k = settings.MEMORY_MMR_TOP_K  # 使用配置默认值
        self.embeddings = None

    def _load_embeddings(self):
        """加载 embedding 模型用于计算相似度"""
        if self.embeddings is None:
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
                # 使用与项目中一致的 embedding 模型
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=settings.EMBED_MODEL_NAME,
                    model_kwargs={'device': 'cpu'}  # 强制使用 CPU
                )
                log_info(f"[MMR] 加载 embedding 模型: {settings.EMBED_MODEL_NAME}")
            except Exception as e:
                log_info(f"[MMR] 加载 embedding 模型失败: {e}")
                raise

    def compute_mmr(
            self,
            query: str,
            candidates: List[Dict[str, Any]],
            k: int = None
    ) -> List[Dict[str, Any]]:
        """MMR 重排序

        Args:
            query: 查询文本
            candidates: 候选文档列表，每个元素包含 "document" 和 "score"
            k: 最终返回数量

        Returns:
            去冗余后的文档列表
        """
        # 使用配置的默认值
        if k is None:
            k = self.default_k

        log_info(f"[MMR] 收到请求: use_mmr={self.use_mmr}, candidates={len(candidates)}, k={k}, λ={self.lambda_param}")

        if not candidates or not self.use_mmr:
            log_info(f"[MMR] 跳过: use_mmr={self.use_mmr}, candidates={len(candidates)}")
            return candidates[:k] if k else candidates

        if k >= len(candidates):
            log_info(f"[MMR] k({k}) >= len(candidates)({len(candidates)}), 仍需MMR去重")
            # 继续执行MMR，虽然数量不变，但可以去重

        try:
            self._load_embeddings()
            log_info(f"[MMR] embedding模型加载成功")
        except Exception as e:
            log_info(f"[MMR] 加载embedding失败: {e}")
            return candidates[:k]

        # 提取文档内容
        docs = [c["document"] for c in candidates]
        doc_contents = []
        for doc in docs:
            if hasattr(doc, "page_content"):
                doc_contents.append(doc.page_content)
            elif isinstance(doc, dict):
                doc_contents.append(doc.get("content", str(doc)))
            else:
                doc_contents.append(str(doc))

        try:
            # 计算 query 和所有候选的 embedding
            query_embedding = self.embeddings.embed_query(query)
            doc_embeddings = self.embeddings.embed_documents(doc_contents)
        except Exception as e:
            log_info(f"[MMR] embedding 计算失败: {e}")
            return candidates[:k]

        # MMR 选代算法
        selected = []
        remaining_indices = list(range(len(candidates)))

        log_info(f"[MMR] 开始选择: λ={self.lambda_param}, 候选数={len(candidates)}")

        for step in range(k):
            if not remaining_indices:
                break

            best_idx = None
            best_mmr = float('-inf')
            best_relevance = 0
            best_novelty = 0

            for idx in remaining_indices:
                # 相关性分数（与 query 的相似度）
                relevance = self._cosine_similarity(
                    query_embedding,
                    doc_embeddings[idx]
                )

                # 新颖性分数（与已选文档的最大相似度）
                if selected:
                    similarities = [
                        self._cosine_similarity(doc_embeddings[idx], doc_embeddings[s["idx"]])
                        for s in selected
                    ]
                    novelty = max(similarities)
                else:
                    novelty = 0

                # MMR 公式
                mmr_score = (
                        self.lambda_param * relevance -
                        (1 - self.lambda_param) * novelty
                )

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx
                    best_relevance = relevance
                    best_novelty = novelty

            if best_idx is not None:
                # 获取文档内容用于日志
                doc_content = doc_contents[best_idx][:50]
                log_info(f"[MMR] 步{step+1}: 选idx={best_idx}, rel={best_relevance:.3f}, nov={best_novelty:.3f}, mmr={best_mmr:.3f}, 内容={doc_content}...")

                selected.append({
                    "idx": best_idx,
                    "document": candidates[best_idx]["document"],
                    "score": candidates[best_idx]["score"],
                    "mmr_score": best_mmr
                })
                remaining_indices.remove(best_idx)

        log_info(f"[MMR] 多样性约束: 输入{len(candidates)}个，输出{len(selected)}个")

        # 返回与原格式一致
        return [{"document": s["document"], "score": s["score"]} for s in selected]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)


_mmr_scorer = None


def get_mmr_scorer() -> MMRScorer:
    """获取 MMR 评分器单例"""
    global _mmr_scorer
    if _mmr_scorer is None:
        _mmr_scorer = MMRScorer()
    return _mmr_scorer
