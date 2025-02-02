from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import time
import json

# Neo4j数据库连接信息
URI = "bolt://192.168.35.10:7687"
AUTH = ("neo4j", "13701033228")

# 创建带连接池的驱动实例
driver = GraphDatabase.driver(
    URI,
    auth=AUTH,
    max_connection_pool_size=10,  # 限制最大连接数
    connection_timeout=5  # 连接超时时间
)

def execute_with_retry(query, max_retries=3, delay=1):
    retries = 0
    while retries < max_retries:
        try:
            with driver.session() as session:
                result = session.run(query)
                return result.data()  # 使用data()方法一次性获取所有结果
        except ServiceUnavailable:
            retries += 1
            if retries < max_retries:
                time.sleep(delay)
            else:
                raise

# 测试连接
try:
    results = execute_with_retry("MATCH (n) RETURN n LIMIT 25")
    # 打印所有结果,使用更好的格式化
    print(f"获取到 {len(results)} 个节点:")
    print("-" * 80)
    for i, record in enumerate(results, 1):
        node = record["n"]
        print(f"节点 {i}:")
        print(f"  功能区域: {node.get('Function', 'N/A')}")
        print(f"  设备代码: {node.get('Device', 'N/A')}")
        print(f"  节点名称: {node.get('name', 'N/A')}")
        print(f"  端子标识: {node.get('Terminal', 'N/A')}")
        print(f"  位置信息: {node.get('Location', 'N/A')}")
        print("-" * 80)
finally:
    # 关闭驱动
    driver.close()