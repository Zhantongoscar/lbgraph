#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
from neo4j import GraphDatabase
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def connect_mysql():
    """连接MySQL数据库"""
    try:
        connection = pymysql.connect(
            **MYSQL_CONFIG,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("MySQL连接成功")
        return connection
    except Exception as e:
        print(f"MySQL连接错误: {e}")
        return None

def connect_neo4j():
    """连接Neo4j数据库"""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print("Neo4j连接成功")
        return driver
    except Exception as e:
        print(f"Neo4j连接错误: {e}")
        return None

def create_simpoints(mysql_conn, neo4j_driver):
    """创建模拟点节点"""
    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT * FROM v_simpoint")
            points = cursor.fetchall()

            with neo4j_driver.session() as session:
                created_count = 0
                for point in points:
                    properties = {k: v for k, v in point.items() if v is not None and k != 'id'}
                    ftid = point['ftid']

                    query = (
                        "MERGE (n:V_simpoint {ftid: $ftid}) "
                        "SET n = $properties"
                    )
                    session.run(query, ftid=ftid, properties=properties)
                    created_count += 1

                print(f"创建或更新了 {created_count} 个V_simpoint节点")

    except Exception as e:
        print(f"创建模拟点错误: {e}")

def check_node_exists(session, ftid):
    """检查节点是否存在"""
    query = """
    MATCH (n)
    WHERE n.ftid = $ftid
    RETURN n.ftid as ftid, labels(n) as labels, n.Device as Device, n.Terminal as Terminal
    """
    result = session.run(query, ftid=ftid).single()
    return result

def create_connections(mysql_conn, neo4j_driver):
    """创建模拟连接关系"""
    try:
        with mysql_conn.cursor() as cursor:
            cursor.execute("SELECT ftid, target_ftid FROM v_simpoint WHERE target_ftid IS NOT NULL AND target_ftid != ''")
            connections = cursor.fetchall()

            with neo4j_driver.session() as session:
                print("\n检查现有的sim连接:")
                check_query = """
                MATCH ()-[r:conn {connType: 'sim'}]->()
                RETURN count(r) as count
                """
                existing = session.run(check_query).single()['count']
                print(f"现有 {existing} 个sim类型的连接\n")

                created_count = 0
                for conn in connections:
                    source_ftid = conn['ftid']
                    target_ftid = conn['target_ftid']
                    
                    print(f"\n处理连接: {source_ftid} -> {target_ftid}")
                    
                    # 检查源节点和目标节点
                    source_node = check_node_exists(session, source_ftid)
                    target_node = check_node_exists(session, target_ftid)
                    
                    if source_node and target_node:
                        print(f"源节点: {source_node['ftid']} ({source_node['labels']})")
                        print(f"目标节点: {target_node['ftid']} ({target_node['labels']})")
                        
                        # 创建连接，支持V_terminal和V_simpoint节点类型
                        create_query = """
                        MATCH (source {ftid: $source_ftid})
                        MATCH (target {ftid: $target_ftid})
                        WHERE source:V_simpoint AND (target:V_terminal OR target:V_simpoint)
                        MERGE (source)-[r:conn {connType: 'sim'}]->(target)
                        RETURN r
                        """
                        result = session.run(create_query, 
                                          source_ftid=source_ftid,
                                          target_ftid=target_ftid)
                        
                        if result.single():
                            print("✓ 连接创建成功")
                            created_count += 1
                        else:
                            print("✗ 连接创建失败")
                    else:
                        print("节点检查结果:")
                        if not source_node:
                            print(f"- 源节点不存在: {source_ftid}")
                        if not target_node:
                            print(f"- 目标节点不存在: {target_ftid}")

                print(f"\n成功创建 {created_count} 个sim连接")
                
                # 验证最终结果
                final = session.run(check_query).single()['count']
                print(f"当前共有 {final} 个sim类型的连接")
                
                if final > 0:
                    print("\n连接示例:")
                    sample_query = """
                    MATCH path=(source)-[r:conn {connType: 'sim'}]->(target)
                    RETURN source.ftid as source, target.ftid as target, 
                           source.Device as sourceDevice, target.Device as targetDevice,
                           source.Terminal as sourceTerminal, target.Terminal as targetTerminal
                    LIMIT 3
                    """
                    samples = session.run(sample_query)
                    for record in samples:
                        print(f"- {record['sourceDevice']}:{record['sourceTerminal']} -> {record['targetDevice']}:{record['targetTerminal']}")

    except Exception as e:
        print(f"创建连接关系错误: {e}")
        raise e

def main():
    """主函数"""
    mysql_conn = connect_mysql()
    if not mysql_conn:
        return

    neo4j_driver = connect_neo4j()
    if not neo4j_driver:
        mysql_conn.close()
        return

    try:
        create_simpoints(mysql_conn, neo4j_driver)
        create_connections(mysql_conn, neo4j_driver)
    finally:
        neo4j_driver.close()
        mysql_conn.close()
        print("\n数据库连接已关闭")

if __name__ == "__main__":
    main()