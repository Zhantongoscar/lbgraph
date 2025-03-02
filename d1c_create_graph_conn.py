import pymysql
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
            try:
                mysql_conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
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

                # 清除现有连接关系
                result = session.run('MATCH ()-[r:CONN]->() DELETE r')
                log_message('已清除所有现有连接关系', f)

                # 检查Neo4j中的节点数量
                result = session.run("""
                    MATCH (n:V_Terminal)
                    RETURN count(n) as count
                """)
                node_count = result.single()['count']
                log_message(f"\nNeo4j中存在 {node_count} 个V_Terminal节点", f)

                # 检查几个关键节点的存在性
                log_message("\n检查示例节点:", f)
                check_nodes = [
                    "=A01+K1.H2-Q1:D2",
                    "=A01+K1.B1-K3:14",
                    "=Q15+K1.G1-G5:ANALOG.15",
                    "=S02+K1.H2-Q1:2"
                ]
                for ftid in check_nodes:
                    result = session.run("""
                        MATCH (n:V_Terminal {FTID: $ftid})
                        RETURN n.FTID as ftid, labels(n) as labels, properties(n) as props
                    """, ftid=ftid)
                    if result.peek():
                        record = result.single()
                        log_message(f"\n找到节点: {ftid}", f)
                        log_message(f"标签: {record['labels']}", f)
                        log_message(f"属性: {record['props']}", f)
                    else:
                        log_message(f"\n未找到节点: {ftid}", f)

            # 从MySQL读取连接数据
            cursor = mysql_conn.cursor()
            
            # 获取总记录数
            cursor.execute("SELECT COUNT(*) as count FROM conn_graph")
            total_count = cursor.fetchone()['count']
            log_message(f"\n总共需要处理 {total_count} 条连接记录", f)
            
            # 分批处理所有记录
            batch_size = 1000
            processed = 0
            conn_count = 0
            fail_count = 0
            
            while processed < total_count:
                cursor.execute(f"""
                    SELECT * FROM conn_graph 
                    LIMIT {processed}, {batch_size}
                """)
                
                rows = cursor.fetchall()
                if not rows:
                    break
                
                for row in rows:
                    source = row['source']
                    target = row['target']
                    
                    # 在Neo4j中创建连接
                    with driver.session() as session:
                        # 先检查节点
                        source_result = session.run("""
                            MATCH (n:V_Terminal {FTID: $ftid})
                            RETURN n
                        """, ftid=source)
                        target_result = session.run("""
                            MATCH (n:V_Terminal {FTID: $ftid})
                            RETURN n
                        """, ftid=target)

                        source_exists = source_result.peek() is not None
                        target_exists = target_result.peek() is not None

                        if not source_exists or not target_exists:
                            fail_count += 1
                            log_message(f"\n节点缺失: source={source} ({source_exists}), target={target} ({target_exists})", f)
                            # 获取节点的详细信息
                            if not source_exists:
                                result = session.run("""
                                    MATCH (n:V_Terminal)
                                    WHERE n.FTID STARTS WITH $prefix
                                    RETURN n.FTID LIMIT 5
                                """, prefix=source.split(":")[0])
                                similar = [r['n.FTID'] for r in result]
                                if similar:
                                    log_message(f"类似的source节点: {similar}", f)
                            if not target_exists:
                                result = session.run("""
                                    MATCH (n:V_Terminal)
                                    WHERE n.FTID STARTS WITH $prefix
                                    RETURN n.FTID LIMIT 5
                                """, prefix=target.split(":")[0])
                                similar = [r['n.FTID'] for r in result]
                                if similar:
                                    log_message(f"类似的target节点: {similar}", f)
                            continue

                        # 准备连接属性
                        props = {k: v for k, v in row.items() if k not in ['source', 'target']}
                        for k in ['voltage', 'current', 'resistance']:
                            props[k] = float(props.get(k, 0))
                        props['isCable'] = bool(props.get('isCable', 0))
                        props['isInPanel'] = bool(props.get('isInPanel', 0))

                        # 创建连接
                        props_str = ', '.join(f'{k}: ${k}' for k in props.keys())
                        cypher = f"""
                            MATCH (source:V_Terminal {{FTID: $source}})
                            MATCH (target:V_Terminal {{FTID: $target}})
                            CREATE (source)-[r:CONN {{{props_str}}}]->(target)
                            RETURN r
                        """
                            
                        try:
                            result = session.run(cypher, dict(source=source, target=target, **props))
                            if result.peek():
                                conn_count += 1
                            else:
                                fail_count += 1
                                log_message(f"\n创建连接失败: {source} -> {target}", f)
                        except Exception as e:
                            fail_count += 1
                            log_message(f"\n创建连接时出错: {source} -> {target}", f)
                            log_message(f"错误信息: {e}", f)
                    
                    processed += 1
                    if processed % 100 == 0:
                        progress = (processed / total_count) * 100
                        log_message(f"\r处理进度: {processed}/{total_count} ({progress:.1f}%) - 成功: {conn_count}, 失败: {fail_count}", f)

            log_message(f'\n总共创建了 {conn_count} 个连接关系，失败 {fail_count} 个', f)

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