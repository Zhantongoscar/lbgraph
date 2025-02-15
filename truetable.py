from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_CONFIG

def generate_truth_table():
    print("程序开始")
    # 定义目标电缆端子标识
    cable_terminals = ['X20', 'X21', 'X22']
    print("开始遍历 Neo4j 数据库中包含目标电缆端子的起始节点，并输出连接路由:")

    # 构建查询语句：从起始节点出发，沿着 conn 关系遍历所有路径，但只返回终点没有后续连接的、且路径中没有重复节点（过滤回头连接）的路径
    query = (
        "MATCH path = (v:Vertex)-[r:conn*]->(end:Vertex) "
        "WHERE " + " OR ".join(f"v.device CONTAINS '{terminal}'" for terminal in cable_terminals) +
        " AND NOT (end)-[:conn]->() "
        "AND all(n IN nodes(path) WHERE single(x IN nodes(path) WHERE x = n)) "
        "RETURN path"
    )
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), **NEO4J_CONFIG)
    with driver.session(database="neo4j") as session:
        result = session.run(query)
        for record in result:
            path = record["path"]
            # 提取整个路由中每段连接的 wire_number
            route = [rel.get("wire_number", "N/A") for rel in path.relationships]
            final_node = path.end_node
            print(f"遍历路线: {route} -> 最终节点: {final_node.get('name', '未命名')} (device: {final_node.get('device', '未知')})")
    driver.close()

if __name__ == '__main__':
    generate_truth_table()
