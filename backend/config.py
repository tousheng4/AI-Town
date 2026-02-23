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
    NPC_UPDATE_INTERVAL = 30  # NPC状态更新间隔(秒)

    # LLM配置 (从环境变量读取)
    LLM_MODEL_ID: str = os.getenv("LLM_MODEL_ID", "glm-4")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

    # Embedding 模型配置
    EMBED_MODEL_NAME: str = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")
    EMBED_MODEL_TYPE: str = os.getenv("EMBED_MODEL_TYPE", "local")

    # CORS配置
    CORS_ORIGINS = ["*"]  # 生产环境应限制具体域名

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

