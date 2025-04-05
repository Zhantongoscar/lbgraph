from neo4j import GraphDatabase

def main():
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            # 查询所有关系及其起始节点和结束节点的属性
            query = """
            MATCH (a)-[r]->(b)
            RETURN a.Terminal AS start_terminal, a.Location AS start_location, 
                   b.Terminal AS end_terminal, b.Location AS end_location, 
                   type(r) AS relationship_type
            LIMIT 10
            """
            result = session.run(query)
            if result.peek() is None:
                print("未找到任何关系。")
            else:
                for record in result:
                    print(f"关系类型: {record['relationship_type']}")
                    print(f"起始节点 Terminal: {record['start_terminal']}")
                    print(f"起始节点 Location: {record['start_location']}")
                    print(f"结束节点 Terminal: {record['end_terminal']}")
                    print(f"结束节点 Location: {record['end_location']}")
                    print("-" * 40)

if __name__ == "__main__":
    main()