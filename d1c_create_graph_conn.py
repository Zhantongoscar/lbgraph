import pymysql
import csv
import sys
import os
import traceback
from neo4j import GraphDatabase
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 添加 MySQL 连接超时和字符集配置
MYSQL_CONFIG.update({
    "connect_timeout": 10,
    "charset": 'utf8mb4'
})

def log_message(message, file_handle=None):
    """打印并记录日志消息"""
    print(message, flush=True)
    if file_handle:
        file_handle.write(message + '\n')
        file_handle.flush()

def main():
    # 创建日志目录
    if not os.path.exists('logs'):
        os.makedirs('logs')

    log_file = 'logs/conn_creation.log'
    with open(log_file, 'w', encoding='utf-8') as f:
        try:
            log_message(f'连接到Neo4j数据库: {NEO4J_URI}', f)
            
            # 连接MySQL数据库
            log_message('尝试连接MySQL数据库...', f)
            log_message(f'连接参数: host={MYSQL_CONFIG["host"]}, user={MYSQL_CONFIG["user"]}, database={MYSQL_CONFIG["database"]}', f)
            try:
                mysql_conn = pymysql.connect(**MYSQL_CONFIG)
                log_message('MySQL连接成功', f)
            except pymysql.Error as e:
                log_message(f'MySQL连接错误: {str(e)}', f)
                if hasattr(e, 'errno'):
                    log_message(f'错误代码: {e.errno}', f)
                raise

            # 连接Neo4j数据库
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            
            # 测试Neo4j连接
            with driver.session() as session:
                result = session.run('RETURN 1 AS test')
                test_value = result.single()['test']
                log_message(f'Neo4j连接测试成功: {test_value}', f)

                # 统计现有节点
                result = session.run("""
                    MATCH (n) 
                    WHERE n:V_Device OR n:V_Terminal 
                    RETURN count(n) AS nodeCount
                """)
                node_count = result.single()["nodeCount"]
                log_message(f'数据库中存在 {node_count} 个节点', f)

                # 检查一些示例节点
                log_message('\n示例节点:', f)
                result = session.run("""
                    MATCH (n)
                    WHERE n:V_Device OR n:V_Terminal
                    RETURN n.FTID AS FTID, labels(n) as labels
                    LIMIT 3
                """)
                for record in result:
                    log_message(f"FTID: {record['FTID']}, 标签: {record['labels']}", f)

                # 清除现有连接关系
                result = session.run('MATCH ()-[r:CONN]->() DELETE r')
                log_message('已清除所有现有连接关系', f)

            # 导出连接数据到CSV
            cursor = mysql_conn.cursor()
            cursor.execute("""
                SELECT source, target, connNo, connType, color, isCable, 
                       voltage, current, resistance 
                FROM conn_graph 
                WHERE isInPanel=1
            """)
            
            # 确保output目录存在
            if not os.path.exists('output'):
                os.makedirs('output')

            csv_file = 'output/connections_export.csv'
            with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['source', 'target', 'connNo', 'connType', 'color', 
                           'isCable', 'voltage', 'current', 'resistance'])
                
                count = 0
                for row in cursor:
                    # 为source和target添加等号前缀
                    source = f"={row[0]}" if not row[0].startswith('=') else row[0]
                    target = f"={row[1]}" if not row[1].startswith('=') else row[1]
                    writer.writerow([source, target] + list(row[2:]))
                    count += 1
                
            log_message(f'已导出 {count} 条连接记录到CSV文件', f)

            # 创建连接关系
            conn_count = 0
            fail_count = 0
            missing_nodes = set()

            with open(csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    source = row['source']
                    target = row['target']

                    # 确保source和target有等号前缀
                    if not source.startswith('='):
                        source = f"={source}"
                    if not target.startswith('='):
                        target = f"={target}"

                    # 创建连接关系
                    with driver.session() as session:
                        cypher = """
                            MATCH (source)
                            WHERE (source:V_Device OR source:V_Terminal)
                            AND source.FTID = $source
                            MATCH (target)
                            WHERE (target:V_Device OR target:V_Terminal)
                            AND target.FTID = $target
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
                        """
                        params = {
                            'source': source,
                            'target': target,
                            'connNo': row['connNo'],
                            'connType': row['connType'],
                            'color': row['color'],
                            'isCable': row['isCable'] == '1',
                            'voltage': float(row['voltage'] or 0),
                            'current': float(row['current'] or 0),
                            'resistance': float(row['resistance'] or 0)
                        }
                        try:
                            result = session.run(cypher, params)

                            if result.peek():
                                conn_count += 1
                                if conn_count % 100 == 0:
                                    log_message(f'已创建 {conn_count} 个连接关系', f)
                            else:
                                missing_nodes.add(f"source={source}, target={target}")
                                fail_count += 1
                        except Exception as e:
                            log_message(f"创建连接失败: source={source}, target={target}, error={e}", f)
                            log_message(f"Cypher查询: {cypher}", f)
                            log_message(f"参数: {params}", f)
                            log_message(traceback.format_exc(), f)
                            fail_count += 1

            log_message(f'\n总共创建了 {conn_count} 个连接关系，失败 {fail_count} 个', f)
            if missing_nodes:
                log_message('\n未能找到的节点对:', f)
                for pair in sorted(missing_nodes):
                    log_message(f'  - {pair}', f)

            # 验证最终的连接数量
            with driver.session() as session:
                result = session.run('MATCH ()-[r:CONN]->() RETURN count(r) AS count')
                final_count = result.single()['count']
                log_message(f'\n数据库中实际存在 {final_count} 个CONN关系', f)

            # 关闭连接
            mysql_conn.close()
            driver.close()
            log_message('\n程序执行成功', f)
            return 0

        except Exception as e:
            log_message(f'错误: {str(e)}', f)
            log_message('详细错误信息:', f)
            log_message(traceback.format_exc(), f)
            return 1

if __name__ == "__main__":
    sys.exit(main())