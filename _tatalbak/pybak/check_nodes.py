from neo4j import GraphDatabase

def main():
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            # 查询节点及其属性
            query = """
            MATCH (n)
            RETURN n.Terminal AS terminal, n.Location AS location, n.name AS name
            LIMIT 10
            """
            result = session.run(query)
            if result.peek() is None:
                print("未找到任何节点。")
            else:
                for record in result:
                    print(f"节点名称: {record['name']}")
                    print(f"节点 Terminal: {record['terminal']}")
                    print(f"节点 Location: {record['location']}")
                    print("-" * 40)

if __name__ == "__main__":
    main()