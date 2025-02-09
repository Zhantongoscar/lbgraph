from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def cleanup_test_data():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # 删除测试虚拟层
            result = session.run("""
                MATCH (n:TestVirtualLayer)
                DETACH DELETE n
                RETURN count(n) as deleted_nodes
            """)
            record = result.single()
            print(f"删除了 {record['deleted_nodes']} 个测试节点")
            
    finally:
        driver.close()

if __name__ == "__main__":
    print("开始清理测试数据...")
    cleanup_test_data()
    print("测试数据清理完成")