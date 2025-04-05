from neo4j import GraphDatabase

def main():
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            # 查询具有Location和Terminal属性的节点样本
            query = """
            MATCH (n) 
            WHERE n.Location IS NOT NULL AND n.Terminal IS NOT NULL
            RETURN n 
            LIMIT 10
            """
            result = session.run(query)
            for record in result:
                print(f"节点: {record['n']}")
                print(f"属性: {record['n'].items()}")

if __name__ == "__main__":
    main()