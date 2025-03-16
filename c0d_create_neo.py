#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
from neo4j import GraphDatabase
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def connect_mysql():
    """Connects to the MySQL database."""
    try:
        # 设置 autocommit=False 确保不会修改数据库
        connection = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor, autocommit=False)
        print("MySQL connection established")
        return connection
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def connect_neo4j():
    """Connects to the Neo4j database."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print("Neo4j connection established")
        return driver
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

def create_device_nodes(connection, driver):
    """Reads data from v_csv_device and creates V_device nodes in Neo4j."""
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
            print(f"Created {len(devices)} V_device nodes")
    except Exception as e:
        print(f"Error creating device nodes: {e}")

def create_terminal_nodes(connection, driver):
    """Reads data from v_csv_devpoint and creates V_terminal nodes in Neo4j."""
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
                        print(f"Processed {i + 1} V_terminal nodes")
            print(f"Created {len(terminals)} V_terminal nodes")
    except Exception as e:
        print(f"Error creating terminal nodes: {e}")

# 函数功能：relationship between V_terminal and V_device nodes
def create_terminal_device_relations(connection, driver):
    """Creates belongto relationships between V_terminal and V_device nodes."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ftid, belongtodevice FROM v_csv_devpoint")
            terminals = cursor.fetchall()

            with driver.session() as session:
                for i, terminal in enumerate(terminals):
                    ftid = terminal['ftid']
                    fdid = terminal['belongtodevice']

                    # 只创建belongto关系，不创建或修改节点
                    query = (
                        "MATCH (t:V_terminal {ftid: $ftid}) "
                        "MATCH (d:V_device {fdid: $fdid}) "
                        "MERGE (t)-[r:belongto]->(d)"
                    )
                    session.run(query, ftid=ftid, fdid=fdid)

                    if (i + 1) % 100 == 0:
                        print(f"Processed {i + 1} belongto relationships")

                print(f"\nCreated belongto relationships for {len(terminals)} terminals")
                print("\n使用以下CQL查询在Neo4j浏览器中查看结果:")
                print("// 查看所有终端及其所属设备的关系")
                print("MATCH (t:V_terminal)-[r:belongto]->(d:V_device)")
                print("RETURN t.ftid, t.name, d.fdid, d.name LIMIT 25;")
                print("\n// 统计每个设备有多少个终端")
                print("MATCH (t:V_terminal)-[r:belongto]->(d:V_device)")
                print("RETURN d.name, COUNT(t) as terminal_count;")
    except Exception as e:
        print(f"Error creating terminal-device relationships: {e}")

# 函数功能：读取v_csv_conn数据，创建external connections
def create_connections(connection, driver):
    """Reads data from v_csv_conn and creates relationships between nodes in Neo4j."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM v_csv_conn")
            connections = cursor.fetchall()

            with driver.session() as session:
                for conn in connections:
                    properties = {k: conn[k] for k in conn if conn[k] is not None}
                    source = conn['source']
                    target = conn['target']
                    connNo = properties.get('connNo')
                    if not connNo:
                        continue

                    # 使用MERGE和connNo确保连接唯一性
                    query = (
                        "MATCH (a:V_terminal {ftid: $source}), (b:V_terminal {ftid: $target}) "
                        "MERGE (a)-[r:conn {connNo: $connNo}]->(b) "
                        "SET r = $properties"
                    )
                    session.run(query, source=source, target=target, connNo=connNo, properties=properties)

                    # 创建双向关系
                    query_reverse = (
                        "MATCH (a:V_terminal {ftid: $target}), (b:V_terminal {ftid: $source}) "
                        "MERGE (a)-[r:conn {connNo: $connNo}]->(b) "
                        "SET r = $properties"
                    )
                    session.run(query_reverse, source=target, target=source, connNo=connNo, properties=properties)
            
            print(f"\nCreated {len(connections)} connections")
            print("\n使用以下CQL查询在Neo4j浏览器中查看结果:")
            print("// 查看所有连接及其connNo")
            print("MATCH (a:V_terminal)-[r:conn]->(b:V_terminal)")
            print("RETURN a.ftid, b.ftid, r.connNo, r.connType LIMIT 25;")
            print("\n// 检查是否有重复的connNo")
            print("MATCH ()-[r:conn]->() WITH r.connNo as connNo, count(*) as cnt")
            print("WHERE cnt > 2 RETURN connNo, cnt;")
    except Exception as e:
        print(f"Error creating connections: {e}")

if __name__ == "__main__":
    mysql_conn = connect_mysql()
    if mysql_conn:
        neo4j_driver = connect_neo4j()
        if neo4j_driver:
            create_device_nodes(mysql_conn, neo4j_driver)
            create_terminal_nodes(mysql_conn, neo4j_driver)
            create_terminal_device_relations(mysql_conn, neo4j_driver)
            create_connections(mysql_conn, neo4j_driver)
            neo4j_driver.close()
        mysql_conn.close()