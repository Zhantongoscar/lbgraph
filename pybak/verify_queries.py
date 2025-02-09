from neo4j import GraphDatabase

def main():
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            # 查询符合条件的节点
            node_query = """
            MATCH (n) 
            WHERE NOT n.Terminal IN ['PE', 'N']
            RETURN count(DISTINCT n)
            """
            node_result = session.run(node_query)
            node_count = node_result.single()[0]
            print(f"符合条件的节点数量: {node_count}")
            
            # 查询符合条件的关系
            relationship_query = """
            MATCH (a)-[r]->(b)
            WHERE NOT a.Terminal IN ['PE', 'N'] AND NOT b.Terminal IN ['PE', 'N']
            RETURN count(DISTINCT r)
            """
            relationship_result = session.run(relationship_query)
            relationship_count = relationship_result.single()[0]
            print(f"符合条件的关系数量: {relationship_count}")

if __name__ == "__main__":
    main()