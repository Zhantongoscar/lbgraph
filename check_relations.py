from neo4j import GraphDatabase
import sys

# Neo4j连接信息
uri = "bolt://192.168.35.10:7687"
username = "neo4j"
password = "13701033228"

def check_relations():
    try:
        # 连接到Neo4j数据库
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # 检查节点总数
            result = session.run("MATCH (t:V_Terminal) RETURN COUNT(t) as count")
            terminal_count = result.single()["count"]
            print(f"V_Terminal节点总数: {terminal_count}")
            
            # 检查BELONGS_TO关系
            result = session.run("""
                MATCH (t:V_Terminal)-[r:BELONGS_TO]->(d:V_Device)
                RETURN COUNT(r) as count
            """)
            belongs_count = result.single()["count"]
            print(f"BELONGS_TO关系总数: {belongs_count}")
            
            # 检查HAS_TERMINAL关系
            result = session.run("""
                MATCH (d:V_Device)-[r:HAS_TERMINAL]->(t:V_Terminal)
                RETURN COUNT(r) as count
            """)
            has_terminal_count = result.single()["count"]
            print(f"HAS_TERMINAL关系总数: {has_terminal_count}")
            
            # 输出一些示例关系
            print("\n示例关系:")
            result = session.run("""
                MATCH (t:V_Terminal)-[r:BELONGS_TO]->(d:V_Device)
                RETURN t.id, t.belongtoDevice, d.id
                LIMIT 5
            """)
            print("\nBELONGS_TO关系示例:")
            for record in result:
                print(f"终端{record['t.id']} -> 设备{record['d.id']} (belongtoDevice={record['t.belongtoDevice']})")
            
            result = session.run("""
                MATCH (d:V_Device)-[r:HAS_TERMINAL]->(t:V_Terminal)
                RETURN d.id, t.id, t.device_id
                LIMIT 5
            """)
            print("\nHAS_TERMINAL关系示例:")
            for record in result:
                print(f"设备{record['d.id']} -> 终端{record['t.id']} (device_id={record['t.device_id']})")

        driver.close()
        
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    check_relations()