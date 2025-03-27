from neo4j import GraphDatabase
import re

def extract_sort_key(terminal_id):
    match = re.match(r'(.+?:)(\d+)$', terminal_id)
    if match:
        return (match.group(1), int(match.group(2)))
    return (terminal_id, 0)

def query_neo4j():
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # 查询以A02+K1.B1-X2开头的所有点
    query = """
    MATCH (n) 
    WHERE n.ftid STARTS WITH '=A02+K1.B1-X2' 
    RETURN n.ftid AS terminal_id, labels(n) AS types
    """
    
    # 修改路径查询，排除回头路径
    path_query = """
    MATCH path = (start)-[:conn*1..5]->(end)
    WHERE start.ftid = $terminal_id 
    AND end.ftid IS NOT NULL
    AND start <> end
    AND ALL(n IN nodes(path) WHERE single(m IN nodes(path) WHERE m = n))
    AND NONE(node IN nodes(path) WHERE node.Type = 'PE')
    RETURN path, length(path) AS pathLength, end, properties(end) AS end_properties
    ORDER BY pathLength DESC
    LIMIT 1
    """
    
    with driver.session() as session:
        result = session.run(query)
        terminals = [dict(record) for record in result]
        
        batch_size = 100
        for i in range(0, len(terminals), batch_size):
            batch = terminals[i:i + batch_size]
            for terminal in batch:
                path_result = session.run(path_query, terminal_id=terminal['terminal_id'])
                record = path_result.single()
                if record:
                    path = record['path']
                    path_nodes = [node for node in path.nodes if node['ftid'] is not None]
                    end_node = record['end']
                    end_props = record['end_properties']
                    terminal['longest_path'] = {
                        'path': [node['ftid'] for node in path_nodes],
                        'path_length': record['pathLength'],
                        'end_node': end_node['ftid'],
                        'end_properties': end_props
                    }
    
    terminals.sort(key=lambda x: extract_sort_key(x['terminal_id']))
    driver.close()
    return terminals

def main():
    print("正在查询Neo4j数据库...")
    try:
        terminals = query_neo4j()
        
        print("\n查询结果(按前缀和数字顺序排序)：")
        total_terminals = len(terminals)
        
        for idx, terminal in enumerate(terminals, 1):
            print(f"\n[{idx}/{total_terminals}] {terminal['terminal_id']} - {terminal['types']}")
            
            if 'longest_path' in terminal:
                path = terminal['longest_path']
                print(f"  最长非回头路径(长度:{path['path_length']}):")
                print(f"    路径: {' -> '.join(path['path'])}")
                print(f"    终点: {path['end_node']}")
                print(f"    终点属性: Type={path['end_properties'].get('Type', 'Unknown')}")
            else:
                print("  未找到有效路径")
                
            if idx < total_terminals:
                try:
                    input("\n按Enter键继续查看下一个节点...")
                    print()
                except KeyboardInterrupt:
                    print("\n用户中断查询")
                    break
                    
    except Exception as e:
        print(f"查询过程中发生错误: {str(e)}")
        print("建议: 1. 减少查询范围 2. 增加Neo4j内存配置")

if __name__ == "__main__":
    main()