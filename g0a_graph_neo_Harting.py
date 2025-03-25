from neo4j import GraphDatabase

def query_neo4j():
    # Neo4j连接配置
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # 查询以A02+K1.B1-X2开头的所有点
    query = """
    MATCH (n) 
    WHERE n.ftid STARTS WITH '=A02+K1.B1-X2' 
    RETURN n.ftid AS terminal_id, labels(n) AS types
    ORDER BY n.ftid
    """
    
    with driver.session() as session:
        result = session.run(query)
        terminals = [dict(record) for record in result]
    
    driver.close()
    return terminals

def main():
    print("正在查询Neo4j数据库...")
    terminals = query_neo4j()
    
    print("\n查询结果：")
    for terminal in terminals:
        print(f"{terminal['terminal_id']} - {terminal['types']}")

if __name__ == "__main__":
    main()