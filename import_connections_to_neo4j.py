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

        # 检查节点数量
        result = session.run('MATCH (d:V_Device) RETURN count(d) AS deviceCount')
        device_count = result.single()['deviceCount']
        print(f'数据库中存在 {device_count} 个V_Device节点')

        result = session.run('MATCH (t:V_terminal) RETURN count(t) AS terminalCount')
        terminal_count = result.single()['terminalCount']
        print(f'数据库中存在 {terminal_count} 个V_Terminal节点')

        # 清空现有连接关系
        result = session.run('MATCH ()-[r:CONN]->() DELETE r')
        print('已清除所有现有连接关系')

    # 从CSV文件导入连接关系
    conn_count = 0
    fail_count = 0
    with open('output/connections_export.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            with driver.session() as session:
                cypher = '''
                    MATCH (source)
                    WHERE source.fdid = $source
                    AND (source:V_Device OR source:V_terminal)
                    MATCH (target)
                    WHERE target.fdid = $target
                    AND (target:V_Device OR target:V_terminal)
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
                        source=row['source'],
                        target=row['target'],
                        connNo=row['connNo'],
                        connType=row['connType'],
                        color=row['color'],
                        isCable=row['isCable'] == '1',
                        voltage=float(row['voltage'] or 0),
                        current=float(row['current'] or 0),
                        resistance=float(row['resistance'] or 0)
                    )
                    if not result.peek():
                        print('未能找到节点: source=' + row['source'] + ', target=' + row['target'])
                        fail_count += 1
                    else:
                        conn_count += 1
                        if conn_count % 100 == 0:
                            print(f'已创建 {conn_count} 个连接关系')
                except Exception as e:
                    print(f'创建连接失败: {e}', file=sys.stderr)
                    fail_count += 1

    print(f'总共创建了 {conn_count} 个连接关系，失败 {fail_count} 个')

    # 验证连接关系数量
    with driver.session() as session:
        result = session.run('MATCH ()-[r:CONN]->() RETURN count(r) AS connCount')
        conn_count = result.single()['connCount']
        print(f'数据库中实际存在 {conn_count} 个CONN关系')

    driver.close()
except Exception as e:
    print(f'错误: {e}', file=sys.stderr)
    sys.exit(1)
