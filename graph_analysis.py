from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import time
import json

# Neo4j数据库连接信息
URI = "bolt://192.168.35.10:7687"
AUTH = ("neo4j", "13701033228")

# 创建带连接池的驱动实例
driver = GraphDatabase.driver(
    f"{URI}?apoc.import.file.enabled=true",  # 通过URI参数启用APOC
    auth=AUTH,
    max_connection_pool_size=10,  # 保留连接池配置
    connection_timeout=5  # 保留超时配置
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
    # 元数据查询
    schema_query = "CALL db.schema.visualization()"
    schema_data = execute_with_retry(schema_query)
    
    # 增强型数据查询
    analysis_queries = [
        """MATCH (n)
        RETURN labels(n) as labels, count(*) as count""",
        
        """MATCH ()-[r]->()
        RETURN type(r) as relationship_type, count(*) as count
        ORDER BY count DESC""",
        
        """MATCH (n)
        WITH n, [key in keys(n) WHERE n[key] IS NULL] as null_props
        WHERE size(null_props) > 0
        RETURN labels(n) as labels, null_props, count(*) as count"""
    ]

    # 执行分析查询
    analysis_results = []
    for query in analysis_queries:
        analysis_results.append(execute_with_retry(query))

    # 结构化输出
    def print_analysis(title, data):
        print(f"\n{'='*40}")
        print(f" {title} ")
        print(f"{'='*40}\n")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    print_analysis("图模式分析", schema_data)
    print_analysis("节点属性分布", analysis_results[0])
    print_analysis("关系类型分析", analysis_results[1])
    print_analysis("空值属性统计", analysis_results[2])
finally:
    # 关闭驱动
    driver.close()