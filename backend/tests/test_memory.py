"""测试脚本：查看Qdrant中的记忆"""

import os
import sys

# 先设置 HuggingFace 镜像 (必须在导入之前设置)
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 设置控制台编码为 UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from qdrant_client import QdrantClient
from langchain_huggingface import HuggingFaceEmbeddings

# 配置 (直接使用你的配置)
QDRANT_URL = "https://6598445f-e867-4cba-a469-35209909e50e.eu-west-2-0.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.DCp-rPutjmd3r-7-dGYO70RI9csCg_Kf42-REkW93nE"

# 可选的 Embedding 模型
# EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # 英文模型（原有）
# EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # 多语言模型
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # 当前使用

# 所有 NPC 的 collection 名称
NPC_NAMES = ["张三", "李四", "王五"]


def show_collection_info(client, collection_name):
    """显示指定 collection 的信息"""
    print(f"\n{'='*60}")
    print(f"Collection: {collection_name}")
    print("=" * 60)

    try:
        collection_info = client.get_collection(collection_name=collection_name)
        print(f"   状态: {collection_info.status}")
        print(f"   向量数量: {collection_info.points_count}")
        if collection_info.points_count > 0:
            print(f"   向量维度: {collection_info.config.params.vectors}")
    except Exception as e:
        print(f"   错误: {e}")
        return

    if collection_info.points_count == 0:
        print("   (无记忆)")
        return

    # 获取所有记忆
    print("\n记忆内容:")
    print("-" * 40)

    results = client.scroll(
        collection_name=collection_name,
        limit=100,
        with_payload=True,
        with_vectors=False
    )

    for i, record in enumerate(results[0], 1):
        payload = record.payload
        content = payload.get("page_content", "")[:60]
        speaker = payload.get("metadata", {}).get("speaker", "unknown")
        timestamp = payload.get("metadata", {}).get("timestamp", "")
        msg_type = payload.get("metadata", {}).get("type", "")
        print(f"{i:2d}. [{speaker}] {content}...")
        print(f"    时间: {timestamp} | 类型: {msg_type}")


def search_memory(client, embeddings, collection_name, query, k=5):
    """测试检索指定话语的相关记忆"""
    print(f"\n{'='*60}")
    print(f"测试检索: '{query}'")
    print(f"Collection: {collection_name}")
    print("=" * 60)

    # 将查询文本转换为向量
    query_vector = embeddings.embed_query(query)
    print(f"\n查询向量维度: {len(query_vector)}")

    # 执行相似度搜索
    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=k,
        with_payload=True
    )

    if results and results.points:
        print(f"\n找到 {len(results.points)} 条相关记忆 (k={k}):")
        print("-" * 50)
        for i, result in enumerate(results.points, 1):
            payload = result.payload
            content = payload.get("page_content", "")
            speaker = payload.get("metadata", {}).get("speaker", "unknown")
            timestamp = payload.get("metadata", {}).get("timestamp", "")
            score = result.score
            print(f"{i}. 相似度: {score:.4f}")
            print(f"   [{speaker}] {content}")
            print(f"   时间: {timestamp}")
            print()
    else:
        print("未找到相关记忆")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Qdrant 记忆查看器")
    parser.add_argument("--npc", "-n", type=str, choices=NPC_NAMES, default="王五",
                        help="选择 NPC (默认: 王五)")
    parser.add_argument("--query", "-q", type=str,
                        help="测试检索指定话语")
    parser.add_argument("--k", "-k", type=int, default=5,
                        help="返回结果数量 (默认: 5)")
    parser.add_argument("--list", "-l", action="store_true",
                        help="列出所有记忆")

    args = parser.parse_args()

    print("=" * 60)
    print("Qdrant 记忆查看器")
    print("=" * 60)

    # 连接 Qdrant
    print("\n连接 Qdrant...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    collection_name = f"npc_{args.npc}_episodic"

    # 如果有查询内容，执行检索测试
    if args.query:
        # 初始化 Embedding 模型
        print("\n初始化 Embedding 模型...")
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL_NAME,
            model_kwargs={'device': 'cpu'}
        )

        search_memory(client, embeddings, collection_name, args.query, args.k)
    elif args.list:
        # 列出所有记忆
        show_collection_info(client, collection_name)
    else:
        # 默认显示所有记忆
        print("\n使用说明:")
        print("  python test_memory.py --list          查看所有记忆")
        print("  python test_memory.py -q \"咖啡\"        测试检索")
        print("  python test_memory.py -n 李四 -q \"你好\"  测试李四的记忆检索")
        print("  python test_memory.py -q \"咖啡\" -k 10  返回10条结果")
        print()
        show_collection_info(client, collection_name)

    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
