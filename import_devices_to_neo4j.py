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

    # 清空现有设备节点
    with driver.session() as session:
        result = session.run('MATCH (d:Device) DELETE d')
        print('已清除所有现有设备节点')

    # 从CSV文件导入设备节点
    device_count = 0
    with open('output/devices_export.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            with driver.session() as session:
                session.run(
                    'CREATE (d:Device {id: $id, fdid: $fdid, function: $function, location: $location, device: $device, Type: $Type, isSim: $isSim, isPLC: $isPLC, isTerminal: $isTerminal})',
                    id=row['id'],
                    fdid=row['fdid'],
                    function=row['function'],
                    location=row['location'],
                    device=row['device'],
                    Type=row['Type'],
                    isSim=row['isSim'],
                    isPLC=row['isPLC'],
                    isTerminal=row['isTerminal']
                )
            device_count += 1
            if device_count % 100 == 0:
                print(f'已创建 {device_count} 个设备节点')

    print(f'总共创建了 {device_count} 个设备节点')
    driver.close()
except Exception as e:
    print(f'错误: {e}', file=sys.stderr)
    sys.exit(1)
