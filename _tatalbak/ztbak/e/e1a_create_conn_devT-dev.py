import sys
# 设置输出编码为utf-8
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_CONFIG

def create_terminal_device_relationships():
    """创建终端点和设备之间的关系"""
    try:
        # 连接到Neo4j数据库
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print(f'连接到Neo4j数据库: {NEO4J_URI}')

        with driver.session() as session:
            # 1. 清除现有的两种关系
            result = session.run('''
                MATCH ()-[r:belongto|haveterminal]->()
                DELETE r
                RETURN count(*) as deleted_count
            ''')
            deleted_count = result.single()["deleted_count"]
            print(f'已删除 {deleted_count} 个现有关系')

            # 2. 创建新的双向关系
            result = session.run('''
                MATCH (t:V_Terminal)
                MATCH (d:V_Device)
                WHERE d.fdid = t.belongtoDevice
                CREATE (t)-[:belongto]->(d)
                CREATE (d)-[:haveterminal]->(t)
                RETURN count(*) as created_count
            ''')
            created_count = result.single()["created_count"]
            print(f'已创建 {created_count} 个新关系')

            # 3. 验证未成功匹配的终端点
            result = session.run('''
                MATCH (t:V_Terminal)
                WHERE NOT EXISTS((t)-[:belongto]->())
                RETURN t.FTID as terminal_id, 
                       t.belongtoDevice as device_id,
                       t.Function as terminal_function,
                       t.Location as terminal_location,
                       t.Device as terminal_device
                LIMIT 5
            ''')
            unmatched = list(result)
            if unmatched:
                print('\n未能匹配的终端点示例:')
                for record in unmatched:
                    print(f'终端点FTID: {record["terminal_id"]}')
                    print(f'  所属设备: {record["device_id"]}')
                    print(f'  功能: {record["terminal_function"]}')
                    print(f'  位置: {record["terminal_location"]}')
                    print(f'  设备: {record["terminal_device"]}')
                    print('---')

            # 4. 统计两种关系的总数
            result = session.run('''
                MATCH ()-[r]->() 
                WHERE type(r) IN ['belongto', 'haveterminal']
                RETURN type(r) as rel_type, count(r) as count
            ''')
            counts = list(result)
            print('\n关系统计:')
            for record in counts:
                print(f'{record["rel_type"]}: {record["count"]} 个')

        driver.close()
        print('\n关系创建过程完成')

    except Exception as e:
        print(f'错误: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    create_terminal_device_relationships()