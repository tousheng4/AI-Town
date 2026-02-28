# 测试嵌入模型是否能正常加载
import os

# 强制指定HF镜像（避免缓存问题）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

try:
    from sentence_transformers import SentenceTransformer

    # 加载模型
    print("开始加载嵌入模型...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    # 测试文本嵌入功能
    text = "测试NPC记忆嵌入"
    embedding = model.encode(text)
    print(f"✅ 模型加载成功！文本嵌入结果长度：{len(embedding)}")
except Exception as e:
    print(f"❌ 模型加载失败，错误详情：{e}")