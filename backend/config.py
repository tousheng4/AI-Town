"""配置文件"""

import os
from typing import Optional


class Settings:
    """应用配置"""

    # API配置
    API_TITLE = "赛博小镇 API"
    API_VERSION = "1.0.0"
    API_HOST = "0.0.0.0"
    API_PORT = 8000

    # NPC配置
    NPC_UPDATE_INTERVAL = 480  # NPC状态更新间隔(秒)

    # LLM配置 (从环境变量读取)
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "glm-4")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

    # Embedding 模型配置
    EMBED_MODEL_NAME: str = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")
    EMBED_MODEL_TYPE: str = os.getenv("EMBED_MODEL_TYPE", "local")

    # CORS配置
    CORS_ORIGINS = ["*"]  # 生产环境应限制具体域名

    # Redis 配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    # 短期记忆过期时间（秒），默认2小时
    MEMORY_TTL: int = int(os.getenv("MEMORY_TTL", "7200"))

    # 情景记忆配置
    # 相似度阈值 (0-1)，只保留高于此分数的记忆，低于此值的将被过滤
    MEMORY_SIMILARITY_THRESHOLD: float = float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.5"))

    # ============== 三层记忆系统配置 ==============

    # 记忆压缩配置
    # 每N轮对话触发一次记忆压缩（生成事件块）
    MEMORY_CONSOLIDATION_INTERVAL: int = int(os.getenv("MEMORY_CONSOLIDATION_INTERVAL", "3"))

    # 检索权重配置 (α + β + γ = 1.0)
    # 最终分数 = α×相似度 + β×重要度 + γ×新近度
    RETRIEVAL_SIMILARITY_WEIGHT: float = float(os.getenv("RETRIEVAL_SIMILARITY_WEIGHT", "0.4"))
    RETRIEVAL_IMPORTANCE_WEIGHT: float = float(os.getenv("RETRIEVAL_IMPORTANCE_WEIGHT", "0.3"))
    RETRIEVAL_RECENCY_WEIGHT: float = float(os.getenv("RETRIEVAL_RECENCY_WEIGHT", "0.3"))

    # 新近度衰减配置
    # recency = 1 / (1 + days_since * decay_rate)
    MEMORY_RECENCY_DECAY_RATE: float = float(os.getenv("MEMORY_RECENCY_DECAY_RATE", "0.1"))

    # 遗忘配置
    # importance < 此值且长期未访问的记忆考虑遗忘
    MEMORY_FORGET_THRESHOLD: float = float(os.getenv("MEMORY_FORGET_THRESHOLD", "0.2"))
    # 超过此天数未访问且importance低的记忆将被遗忘
    MEMORY_FORGET_DAYS: int = int(os.getenv("MEMORY_FORGET_DAYS", "30"))

    # Profile事实库配置
    # 存储路径
    PROFILE_DATA_DIR: str = os.path.join(os.path.dirname(__file__), 'profile_data')

    @classmethod
    def validate(cls):
        """验证配置"""
        if not cls.LLM_API_KEY:
            print("⚠️  警告: 未设置LLM_API_KEY环境变量")
            print("   请在.env文件中配置LLM_API_KEY")
            print("   示例: LLM_API_KEY=\"your-api-key\"")
            return False

        print(f"✅ LLM配置:")
        print(f"   模型: {cls.LLM_MODEL_ID}")
        print(f"   服务地址: {cls.LLM_BASE_URL}")
        print(f"   Embedding模型: {cls.EMBED_MODEL_NAME}")
        return True


settings = Settings()
