import csv
import sys
from neo4j import GraphDatabase

# Neo4j连接信息
uri = 'bolt://192.168.35.10:7687'
username = 'neo4j'
password = '13701033228'

print(f'连接到Neo4j数据库: {uri}')
try:
    # 连接到Neo4j数据库
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    # 测试连接
    with driver.session() as session:
        result = session.run('RETURN 1 AS test')
        test_value = result.single()['test']
        print(f'连接测试成功: {test_value}')

    # 清空现有终端节点
    with driver.session() as session:
        result = session.run('MATCH (t:V_Terminal) DELETE t')
        print('已清除所有现有终端节点')

    # 从CSV文件导入终端节点
    terminal_count = 0
    with open('output/terminals_export.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            properties = {key: value for key, value in row.items()}
            cypher_query = 'CREATE (t:V_Terminal $props)'
            with driver.session() as session:
                session.run(cypher_query, props=properties)
            terminal_count += 1
            if terminal_count % 100 == 0:
                print(f'已创建 {terminal_count} 个终端节点')

    # 创建设备和终端之间的关系
    with driver.session() as session:
        # 找到匹配的Device和V_Terminal节点，创建HAS_TERMINAL关系
        session.run(
            'MATCH (d:Device), (t:V_Terminal) WHERE d.id = t.device_id CREATE (d)-[:HAS_TERMINAL]->(t)'
        )
        print('已创建设备和终端之间的关系')

    print(f'总共创建了 {terminal_count} 个终端节点')
    driver.close()
except Exception as e:
    print(f'错误: {e}', file=sys.stderr)
    sys.exit(1)
