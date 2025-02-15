from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def test_database_connection():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            # 测试1：清理数据库
            print("测试1：清理数据库")
            session.run('MATCH (n) DETACH DELETE n')
            
            # 测试2：创建测试节点
            print("\n测试2：创建带多标签的测试节点")
            result = session.run("""
                CREATE (n:Component:IntComp:Relay {
                    id: 'TEST-Q1',
                    name: '测试继电器',
                    status: 'unknown',
                    coil_voltage: '24VDC'
                }) RETURN n
            """)
            print(f"创建节点结果: {result.single()}")
            
            # 测试3：创建测试关系
            print("\n测试3：创建带属性的测试关系")
            result = session.run("""
                CREATE (source:Component:IntComp:Relay {id: 'TEST-Q2'})
                CREATE (target:Component:IntComp:PowerSupply {id: 'TEST-G1'})
                CREATE (source)-[r:CONTROLS {control_type: 'digital'}]->(target)
                RETURN r
            """)
            print(f"创建关系结果: {result.single()}")
            
            # 测试4：查询所有节点和关系
            print("\n测试4：查询所有节点和关系")
            result = session.run("""
                MATCH (n) 
                OPTIONAL MATCH (n)-[r]-() 
                RETURN 'Nodes:' as type, count(DISTINCT n) as count
                UNION
                MATCH ()-[r]->()
                RETURN 'Relationships:' as type, count(r) as count
            """)
            for record in result:
                print(f"{record['type']} {record['count']}")
                
            print("\n数据库连接和基本功能测试完成")
            
    except Exception as e:
        print(f"测试过程中出现错误: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    test_database_connection()