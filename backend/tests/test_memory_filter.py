"""测试Qdrant情景记忆检索"""
import os

from dotenv import load_dotenv

load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client import models

# Qdrant 配置
QDRANT_URL = os.getenv("QDRANT_URL",
                       "https://6598445f-e867-4cba-a469-35209909e50e.eu-west-2-0.aws.cloud.qdrant.io:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY",
                           "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.DCp-rPutjmd3r-7-dGYO70RI9csCg_Kf42-REkW93nE")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# 测试不同的 player_id
test_player_ids = ["player", "Player1", "Player", "player1"]

npc_name = "王五"
collection_name = f"npc_{npc_name}_episodic"

print(f"测试集合: {collection_name}")
print("=" * 50)

# 查看集合中所有数据
print("\n1. 查看集合中所有数据 (不带过滤):")
try:
    from langchain_qdrant import QdrantVectorStore
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    qdrant = QdrantVectorStore.from_existing_collection(
        collection_name=collection_name,
        embedding=embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )

    all_docs = qdrant.similarity_search(query="你好", k=10)
    print(f"   总共 {len(all_docs)} 条记忆")
    for i, doc in enumerate(all_docs[:5]):
        player_id = doc.metadata.get("player_id", "unknown")
        content = doc.page_content[:50]
        print(f"   {i + 1}. player_id={player_id}, content={content}...")

except Exception as e:
    print(f"   错误: {e}")

# 测试用 scroll API + scroll_filter 获取数据并过滤（注意嵌套结构 metadata.player_id）
print("\n2. 使用 scroll API + scroll_filter 过滤:")
for player_id in test_player_ids:
    try:
        scroll_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.player_id",  # 注意是嵌套结构！
                    match=models.MatchValue(value=player_id)
                )
            ]
        )

        results = client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=100,
            with_vectors=False
        )

        count = len(results[0])
        print(f"   metadata.player_id='{player_id}': {count} 条")

    except Exception as e:
        err_msg = str(e)
        if "Index required" in err_msg:
            print(f"   metadata.player_id='{player_id}': 错误 - 需要创建索引")
        else:
            print(f"   player_id='{player_id}': 错误 - {e}")

# 不用过滤，直接获取所有数据
print("\n3. 直接获取所有数据（不带过滤）:")
try:
    results = client.scroll(
        collection_name=collection_name,
        limit=100,
        with_vectors=False,
        with_payload=True
    )

    print(f"   总共 {len(results[0])} 条")
    for i, point in enumerate(results[0][:3]):
        print(f"   {i + 1}. payload: {point.payload}")

except Exception as e:
    print(f"   错误: {e}")

# 查看集合信息
print("\n4. 查看集合信息:")
try:
    info = client.get_collection(collection_name=collection_name)
    print(f"   集合名称: {info.name}")
    print(f"   向量数量: {info.vectors_count}")
    print(f"   点数量: {info.points_count}")
    print(f"   索引字段: {info.payload_schema}")

except Exception as e:
    print(f"   错误: {e}")

# 5. 创建 metadata.player_id 索引
print("\n5. 创建 metadata.player_id 索引:")
try:
    client.create_payload_index(
        collection_name=collection_name,
        field_name="metadata.player_id",
        field_schema={"type": "keyword"}
    )
    print(f"   ✓ 索引创建成功!")

    # 再次测试过滤
    print("\n6. 重新测试过滤:")
    for player_id in test_player_ids:
        try:
            scroll_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.player_id",
                        match=models.MatchValue(value=player_id)
                    )
                ]
            )

            results = client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=100,
                with_vectors=False
            )

            count = len(results[0])
            print(f"   metadata.player_id='{player_id}': {count} 条")

        except Exception as e:
            print(f"   player_id='{player_id}': 错误 - {e}")

except Exception as e:
    print(f"   错误: {e}")
