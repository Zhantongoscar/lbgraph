import csv
import sys
from neo4j import GraphDatabase

uri = 'bolt://192.168.35.10:7687'
username = 'neo4j'
password = '13701033228'

print(f'连接到Neo4j数据库: {uri}')
try:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    with driver.session() as session:
        result = session.run('RETURN 1 AS test')
        test_value = result.single()['test']
        print(f'连接测试成功: {test_value}')

        # 检查并打印一些节点示例
        print('\n检查节点属性示例:')
        result = session.run(
            '''
            MATCH (n) 
            WHERE n:V_Device OR n:V_terminal 
            RETURN n, labels(n) AS labels
            LIMIT 5
            '''
        )
        for record in result:
            node = record['n']
            labels = record['labels']
            print(f'\n节点类型: {labels}')
            for key, value in node.items():
                print(f'  {key}: {value}')

        # 检查并缓存节点
        result = session.run(
            '''
            MATCH (n)
            WHERE n:V_Device OR n:V_terminal
            RETURN n.FTID AS ftid, n.fdid AS fdid
            '''
        )
        nodes_by_ftid = {record['ftid']: True for record in result if record['ftid']}
        print(f'从Neo4j读取了 {len(nodes_by_ftid)} 个节点的FTID')

        # 清空现有连接关系
        result = session.run('MATCH ()-[r:CONN]->() DELETE r')
        print('已清除所有现有连接关系')

    # 从CSV文件导入连接关系
    conn_count = 0
    fail_count = 0
    missing_nodes = set()
    with open('output/connections_export.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            source = row['source']
            target = row['target']
            
            # 确保source和target有等号前缀
            if not source.startswith('='):
                source = '=' + source
            if not target.startswith('='):
                target = '=' + target
            
            if source not in nodes_by_ftid or target not in nodes_by_ftid:
                if source not in nodes_by_ftid:
                    missing_nodes.add(source)
                if target not in nodes_by_ftid:
                    missing_nodes.add(target)
                print(f'未能找到节点: source={source}, target={target}')
                fail_count += 1
                continue
            
            with driver.session() as session:
                cypher = '''
                    MATCH (source)
                    WHERE source.FTID = $source
                    MATCH (target)
                    WHERE target.FTID = $target
                    CREATE (source)-[r:CONN {
                        connNo: $connNo,
                        type: $connType,
                        color: $color,
                        isCable: $isCable,
                        voltage: $voltage,
                        current: $current,
                        resistance: $resistance
                    }]->(target)
                    RETURN r
                '''
                try:
                    result = session.run(
                        cypher,
                        source=source,
                        target=target,
                        connNo=row['connNo'],
                        connType=row['connType'],
                        color=row['color'],
                        isCable=row['isCable'] == '1',
                        voltage=float(row['voltage'] or 0),
                        current=float(row['current'] or 0),
                        resistance=float(row['resistance'] or 0)
                    )
                    if result.peek():
                        conn_count += 1
                        if conn_count % 100 == 0:
                            print(f'已创建 {conn_count} 个连接关系')
                except Exception as e:
                    print(f'创建连接失败: {e}', file=sys.stderr)
                    fail_count += 1

    print(f'总共创建了 {conn_count} 个连接关系，失败 {fail_count} 个')
    if missing_nodes:
        print('\n缺失的节点:')
        for node in sorted(missing_nodes):
            print(f'  - {node}')

    # 验证连接关系数量
    with driver.session() as session:
        result = session.run('MATCH ()-[r:CONN]->() RETURN count(r) AS connCount')
        conn_count = result.single()['connCount']
        print(f'数据库中实际存在 {conn_count} 个CONN关系')

    driver.close()
except Exception as e:
    print(f'错误: {e}', file=sys.stderr)
    sys.exit(1)
