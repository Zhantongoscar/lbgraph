#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
from neo4j import GraphDatabase
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def connect_mysql():
    """连接到MySQL数据库"""
    try:
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

def create_device_nodes(connection, driver):
    """从v_csv_device读取数据并创建V_device节点"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM v_csv_device")
            devices = cursor.fetchall()

            with driver.session() as session:
                for device in devices:
                    properties = {k: device[k] for k in device if device[k] is not None}
                    fdid = device['fdid']
                    # 检查节点是否已存在
                    check_query = "MATCH (d:V_device {fdid: $fdid}) RETURN d"
                    result = session.run(check_query, fdid=fdid).peek()

                    if result is None:
                        query = (
                            "CREATE (n:V_device {fdid: $fdid}) "
                            "SET n = $properties"
                        )
                        session.run(query, fdid=fdid, properties=properties)
            print(f"创建了 {len(devices)} 个V_device节点")
    except Exception as e:
        print(f"创建设备节点时出错: {e}")

def create_terminal_nodes(connection, driver):
    """从v_csv_devpoint读取数据并创建V_terminal节点"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM v_csv_devpoint")
            terminals = cursor.fetchall()

            with driver.session() as session:
                for i, terminal in enumerate(terminals):
                    properties = {k: terminal[k] for k in terminal if terminal[k] is not None}
                    ftid = terminal['ftid']
                    # 检查节点是否已存在
                    check_query = "MATCH (t:V_terminal {ftid: $ftid}) RETURN t"
                    result = session.run(check_query, ftid=ftid).peek()

                    if result is None:
                        query = (
                            "CREATE (n:V_terminal {ftid: $ftid}) "
                            "SET n = $properties"
                        )
                        session.run(query, ftid=ftid, properties=properties)

                    if (i + 1) % 100 == 0:
                        print(f"已处理 {i + 1} 个V_terminal节点")
            print(f"创建了 {len(terminals)} 个V_terminal节点")
    except Exception as e:
        print(f"创建端子节点时出错: {e}")

def create_terminal_device_relations(connection, driver):
    """创建V_terminal和V_device节点之间的belongto关系"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ftid, belongtodevice FROM v_csv_devpoint")
            terminals = cursor.fetchall()

            with driver.session() as session:
                for i, terminal in enumerate(terminals):
                    ftid = terminal['ftid']
                    fdid = terminal['belongtodevice']

                    query = (
                        "MATCH (t:V_terminal {ftid: $ftid}) "
                        "MATCH (d:V_device {fdid: $fdid}) "
                        "MERGE (t)-[r:belongto]->(d)"
                    )
                    session.run(query, ftid=ftid, fdid=fdid)

                    if (i + 1) % 100 == 0:
                        print(f"已处理 {i + 1} 个belongto关系")

            print(f"\n为 {len(terminals)} 个端子创建了belongto关系")
    except Exception as e:
        print(f"创建端子-设备关系时出错: {e}")

def create_all_connections(connection, driver):
    """从v_csv_conn读取数据并创建所有连接关系（包括外部连接和内部连接）"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM v_csv_conn")
            connections = cursor.fetchall()

            with driver.session() as session:
                processed = 0
                for conn in connections:
                    source = conn['source']
                    target = conn['target']
                    if not source or not target:
                        continue
                        
                    properties = {k: conn[k] for k in conn if conn[k] is not None}
                    connNo = properties.get('connNo')
                    if not connNo:
                        continue

                    query = """
                    MATCH (a:V_terminal {ftid: $source}), (b:V_terminal {ftid: $target})
                    MERGE (a)-[r1:conn {connNo: $connNo}]->(b)
                    MERGE (b)-[r2:conn {connNo: $connNo}]->(a)
                    SET r1 = $properties, r2 = $properties
                    """
                    session.run(query, source=source, target=target, connNo=connNo, properties=properties)
                    processed += 1
                    
                    if processed % 100 == 0:
                        print(f"已处理 {processed} 个连接")
            
            print(f"\n创建了 {processed} 个双向连接")
    except Exception as e:
        print(f"创建外部连接时出错: {e}")


def print_neo4j_queries():
    """打印有用的Neo4j查询语句"""
    print("\n=== 使用以下CQL查询在Neo4j浏览器中查看结果 ===")
    
    print("\n1. 查看设备和端子的关系:")
    print("MATCH (t:V_terminal)-[r:belongto]->(d:V_device)")
    print("RETURN t.ftid, t.name, d.fdid, d.name LIMIT 25;")
    
    print("\n2. 统计每个设备的端子数量:")
    print("MATCH (t:V_terminal)-[r:belongto]->(d:V_device)")
    print("RETURN d.name, COUNT(t) as terminal_count;")
    
    print("\n3. 查看所有连接:")
    print("MATCH (s:V_terminal)-[r:conn]->(t:V_terminal)")
    print("RETURN s.ftid, t.ftid, r.connNo, r.connType, r.connMode LIMIT 25;")
    
    print("\n4. 按连接类型查看连接:")
    print("MATCH (s:V_terminal)-[r:conn]->(t:V_terminal)")
    print("RETURN r.connType, r.connMode, count(*) as count")
    print("ORDER BY count DESC;")
    
    print("\n5. 检查重复的连接:")
    print("MATCH ()-[r:conn]->() WITH r.connNo as connNo, count(*) as cnt")
    print("WHERE cnt > 2")
    print("RETURN connNo, cnt ORDER BY cnt DESC;")

def main():
    """主函数"""
    mysql_conn = None
    neo4j_driver = None
    try:
        print("\n=== 开始创建图数据库 ===")
        
        # 建立数据库连接
        mysql_conn = connect_mysql()
        if not mysql_conn:
            return 1
            
        neo4j_driver = connect_neo4j()
        if not neo4j_driver:
            return 1

        # 1. 创建基础节点
        print("\n>>> 步骤1: 创建设备节点")
        create_device_nodes(mysql_conn, neo4j_driver)
        
        print("\n>>> 步骤2: 创建端子节点")
        create_terminal_nodes(mysql_conn, neo4j_driver)
        
        print("\n>>> 步骤3: 创建设备-端子关系")
        create_terminal_device_relations(mysql_conn, neo4j_driver)
        
        # 2. 创建连接关系
        print("\n>>> 步骤4: 创建所有连接（外部连接和内部连接）")
        create_all_connections(mysql_conn, neo4j_driver)
        
        # 3. 输出查询指南
        print_neo4j_queries()
        
        print("\n=== 所有操作完成 ===")
        return 0
        
    except Exception as e:
        print(f"程序执行错误: {e}")
        return 1
        
    finally:
        if neo4j_driver:
            neo4j_driver.close()
        if mysql_conn:
            mysql_conn.close()
            print("数据库连接已关闭")

if __name__ == "__main__":
    sys.exit(main())
