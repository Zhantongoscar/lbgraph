from neo4j import GraphDatabase

def main():
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            # 查询节点的属性
            query = """
            MATCH (n) 
            RETURN DISTINCT keys(n) 
            LIMIT 10
            """
            result = session.run(query)
            for record in result:
                print(f"属性: {record['keys(n)']}")

if __name__ == "__main__":
    main()