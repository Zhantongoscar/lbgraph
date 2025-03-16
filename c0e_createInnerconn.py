#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
from neo4j import GraphDatabase
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def connect_mysql():
    """连接到MySQL数据库"""
    try:
        # 设置 autocommit=False 确保不会修改数据库
        connection = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor, autocommit=False)
        print("MySQL连接已建立")
        return connection
    except Exception as e:
        print(f"MySQL连接错误: {e}")
        return None

def connect_neo4j():
    """连接到Neo4j数据库"""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print("Neo4j连接已建立")
        return driver
    except Exception as e:
        print(f"Neo4j连接错误: {e}")
        return None

def create_inner_connections(connection, driver):
    """从v_csv_innerconn读取数据并在Neo4j中创建内部连接"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM v_csv_innerconn
                ORDER BY connNo
            """)
            connections = cursor.fetchall()

            with driver.session() as session:
                total_created = 0
                total_skipped = 0

                for conn in connections:
                    try:
                        # 首先验证源点和目标点是否存在
                        check_query = """
                            MATCH (s:V_terminal {ftid: $source})
                            MATCH (t:V_terminal {ftid: $target})
                            RETURN s, t
                        """
                        result = session.run(check_query, 
                                          source=conn['source'],
                                          target=conn['target']).peek()

                        if result:  # 如果两个点都存在
                            # 使用MERGE创建关系
                            props = {
                                'connNo': conn['connNo'],
                                'color': conn['color'],
                                'isCable': bool(conn['isCable']),
                                'isInPanel': bool(conn['isInPanel']),
                                'connType': conn['connType'],
                                'voltage': float(conn['voltage']) if conn['voltage'] is not None else 0.0,
                                'current': float(conn['current']) if conn['current'] is not None else 0.0,
                                'resistance': float(conn['resistance']) if conn['resistance'] is not None else 0.0
                            }

                            query = """
                                MATCH (s:V_terminal {ftid: $source}), (t:V_terminal {ftid: $target})
                                MERGE (s)-[r:conn {connNo: $connNo}]->(t)
                                SET r = $props
                            """
                            session.run(query, 
                                      source=conn['source'],
                                      target=conn['target'],
                                      connNo=conn['connNo'],
                                      props=props)

                            # 创建双向关系（如果需要）
                            session.run(query, 
                                      source=conn['target'],
                                      target=conn['source'],
                                      connNo=conn['connNo'],
                                      props=props)

                            total_created += 1
                            if total_created % 100 == 0:
                                print(f"已处理 {total_created} 个连接")
                        else:
                            print(f"跳过连接 {conn['connNo']}: 源点 ({conn['source']}) 或目标点 ({conn['target']}) 不存在")
                            total_skipped += 1

                    except Exception as e:
                        print(f"处理连接 {conn['connNo']} 时出错: {str(e)}")
                        continue

                print(f"\n处理完成:")
                print(f"成功创建连接: {total_created}")
                print(f"跳过的连接: {total_skipped}")

                print("\n使用以下CQL查询在Neo4j浏览器中查看结果:")
                print("// 查看所有内部连接")
                print("MATCH (s:V_terminal)-[r:conn]->(t:V_terminal)")
                print("WHERE r.connNo STARTS WITH 'in'")
                print("RETURN s.ftid, t.ftid, r.connNo, r.connType LIMIT 25;")
                print("\n// 检查重复的connNo")
                print("MATCH ()-[r:conn]->() WITH r.connNo as connNo, count(*) as cnt")
                print("WHERE cnt > 2 AND connNo STARTS WITH 'in'")
                print("RETURN connNo, cnt;")

    except Exception as e:
        print(f"创建内部连接时出错: {e}")
        raise

def main():
    """主函数"""
    mysql_conn = None
    neo4j_driver = None
    try:
        mysql_conn = connect_mysql()
        if mysql_conn:
            neo4j_driver = connect_neo4j()
            if neo4j_driver:
                create_inner_connections(mysql_conn, neo4j_driver)
                neo4j_driver.close()
            mysql_conn.close()
        return 0
    except Exception as e:
        print(f"程序执行错误: {e}")
        if neo4j_driver:
            neo4j_driver.close()
        if mysql_conn:
            mysql_conn.close()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())