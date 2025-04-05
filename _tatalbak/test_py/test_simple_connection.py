from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def test_simple_connection():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            # 简单的连接测试查询
            result = session.run("RETURN 1 as n")
            value = result.single()[0]
            print(f"连接测试成功! 测试查询结果: {value}")
            
            # 获取数据库版本
            result = session.run("CALL dbms.components() YIELD name, versions, edition RETURN *")
            record = result.single()
            print(f"Neo4j 版本信息:")
            print(f"名称: {record['name']}")
            print(f"版本: {record['versions']}")
            print(f"版本类型: {record['edition']}")
            
    except Exception as e:
        print(f"连接测试失败: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    print("开始测试数据库连接...")
    test_simple_connection()