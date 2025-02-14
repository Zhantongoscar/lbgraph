from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_CONFIG

def generate_truth_table():
    print("程序开始")  # 新增输出
    # 定义目标电缆端子标识
    cable_terminals = ['X20', 'X21', 'X22']
    print("开始遍历 Neo4j 数据库中包含目标电缆端子的节点:")

    # 使用 v.device CONTAINS 'X20' 类似浏览器中可获得数据的查询条件
    query = "MATCH (v:Vertex) WHERE " + " OR ".join(f"v.device CONTAINS '{terminal}'" for terminal in cable_terminals) + " RETURN v.device as device, v.name as name"
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), **NEO4J_CONFIG)
    with driver.session(database="neo4j") as session:
        result = session.run(query)
        for record in result:
            print(f"遍历到电缆端子: {record['device']} (节点名称: {record['name']})")
    driver.close()

if __name__ == '__main__':
    generate_truth_table()
