from neo4j import GraphDatabase
import re

def extract_sort_key(terminal_id):
    match = re.match(r'(.+?:)(\d+)$', terminal_id)
    if match:
        return (match.group(1), int(match.group(2)))
    return (terminal_id, 0)

def determine_node_type(properties):
    """
    根据节点的属性确定其实际类型
    """
    if 'Function' in properties:
        function = properties['Function']
        # Q开头通常表示数字输出(DO)
        if function.startswith('Q'):
            return 'DO'
        # I开头通常表示数字输入(DI)
        elif function.startswith('I'):
            return 'DI'
    # 保持原有类型
    return properties.get('Type', 'Unknown')

def determine_need_type(end_type):
    """
    根据终点类型确定需要的类型
    """
    if end_type == 'DO':
        return 'DI'
    elif end_type == 'DI':
        return 'DO'
    return 'Unknown'

def update_terminal_need(driver, terminal_id, need_type):
    """
    更新终端节点的Need属性
    """
    query = """
    MATCH (n)
    WHERE n.ftid = $terminal_id
    SET n.Need = $need_type
    """
    with driver.session() as session:
        session.run(query, terminal_id=terminal_id, need_type=need_type)

def get_user_group_choice():
    """
    让用户选择要处理的组 (X20-X23)
    """
    groups = ["20", "21", "22", "23"]
    print("\n可用的组：")
    for i, group in enumerate(groups, 1):
        print(f"{i}. X{group}")
    
    while True:
        try:
            choice = input("\n请选择要处理的组编号 (1-4): ")
            index = int(choice) - 1
            if 0 <= index < len(groups):
                return groups[index]
            else:
                print("无效的选择，请输入1-4")
        except ValueError:
            print("请输入有效的数字")

def get_neo4j_driver():
    """
    获取Neo4j数据库连接
    """
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    return GraphDatabase.driver(uri, auth=(user, password))

def query_neo4j(driver, group_number):
    """
    查询Neo4j数据库并返回终端信息
    """
    # 查询特定组的所有点
    query = """
    MATCH (n)
    WHERE n.ftid STARTS WITH $prefix
    RETURN n.ftid AS terminal_id, labels(n) AS types, properties(n) AS properties
    """
    prefix = f"=A02+K1.B1-X{group_number}"
    
    # 修改路径查询，排除回头路径和更准确地处理类型
    path_query = """
    MATCH path = (start)-[:conn*1..5]->(end)
    WHERE start.ftid = $terminal_id
    AND end.ftid IS NOT NULL
    AND start <> end
    AND ALL(n IN nodes(path) WHERE single(m IN nodes(path) WHERE m = n))
    AND NONE(node IN nodes(path) WHERE node.Type = 'PE')
    RETURN path,
           length(path) AS pathLength,
           end,
           properties(end) AS end_properties,
           end.Function as end_function
    ORDER BY pathLength DESC
    LIMIT 1
    """
    
    with driver.session() as session:
        result = session.run(query, prefix=prefix)
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
    return terminals

def main():
    print("正在查询Neo4j数据库...")
    driver = None
    try:
        driver = get_neo4j_driver()
        
        # 让用户选择要处理的组
        selected_group = get_user_group_choice()
        print(f"\n选择了组: X{selected_group}")
        
        # 查询选定组的终端
        terminals = query_neo4j(driver, selected_group)
        
        print(f"\n查询结果(组X{selected_group}，按前缀和数字顺序排序)：")
        total_terminals = len(terminals)
        
        for idx, terminal in enumerate(terminals, 1):
            start_terminal = terminal['terminal_id']
            start_properties = terminal.get('properties', {})
            current_need = start_properties.get('Need', '未设置')
            print(f"\n[{idx}/{total_terminals}] {start_terminal} - {terminal['types']}")
            print(f"  当前Need属性: {current_need}")
            
            if 'longest_path' in terminal:
                path = terminal['longest_path']
                print(f"  最长非回头路径(长度:{path['path_length']}):")
                print(f"    路径: {' -> '.join(path['path'])}")
                print(f"    终点: {path['end_node']}")
                end_type = determine_node_type(path['end_properties'])
                print(f"    终点属性: Type={end_type}")
                print(f"    Function: {path['end_properties'].get('Function', '')}")
                need_type = determine_need_type(end_type)
                print(f"    起点({start_terminal})需要的属性: Need={need_type}")
                
                # 更新数据库中的Need属性
                try:
                    update_terminal_need(driver, start_terminal, need_type)
                    print(f"    √ Need属性已更新到数据库")
                except Exception as e:
                    print(f"    × Need属性更新失败: {str(e)}")
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
    finally:
        if driver:
            driver.close()

if __name__ == "__main__":
    main()