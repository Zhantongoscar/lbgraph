from neo4j import GraphDatabase
import sys
import traceback

# Neo4j连接信息
uri = "bolt://192.168.35.10:7687"
username = "neo4j"
password = "13701033228"

try:
    print(f"尝试连接到Neo4j: {uri}")
    # 连接到Neo4j数据库
    driver = GraphDatabase.driver(uri, auth=(username, password))

    print("测试连接...")
    with driver.session() as session:
        # 1. 首先测试连接
        result = session.run("RETURN 1 as test")
        print(f"连接测试成功: {result.single()['test']}")
        
        # 2. 检查是否有终端节点
        result = session.run("MATCH (t:V_Terminal) RETURN COUNT(t) as count")
        print(f"\n终端节点数量: {result.single()['count']}")
        
        # 3. 检查终端节点的属性
        result = session.run("""
            MATCH (t:V_Terminal) 
            RETURN t.id, t.belongtoDevice, t.device_id 
            LIMIT 3
        """)
        print("\n示例终端节点:")
        for record in result:
            print(f"ID: {record['t.id']}, belongtoDevice: {record['t.belongtoDevice']}, device_id: {record['t.device_id']}")
        
        # 4. 检查所有关系类型
        result = session.run("CALL db.relationshipTypes()")
        print("\n现有关系类型:")
        for record in result:
            print(f"- {record['relationshipType']}")

    driver.close()
    print("\n连接已关闭")

except Exception as e:
    print(f"错误: {str(e)}", file=sys.stderr)
    print("\n详细错误信息:", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)