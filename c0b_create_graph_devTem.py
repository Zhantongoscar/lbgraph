# -*- coding: utf-8 -*-
import sys
import traceback
import logging
from neo4j import GraphDatabase
import pymysql
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import os

def eprint(*args, **kwargs):
    """打印到stderr"""
    print(*args, file=sys.stderr, **kwargs)
    sys.stderr.flush()

class GraphDeviceCreator:
    def __init__(self):
        try:
            eprint("\n=== 初始化数据库连接 ===")
            # 连接MySQL数据库
            self.mysql_conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            eprint(f"MySQL数据库连接成功：{MYSQL_CONFIG['host']}")
            
            # 连接Neo4j数据库
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            eprint(f"Neo4j数据库连接成功：{NEO4J_URI}")
            
            # 测试连接
            self._test_connections()
            eprint("数据库连接测试成功")
            
        except Exception as e:
            eprint(f"初始化失败: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            raise

    def _test_connections(self):
        """测试数据库连接"""
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            if not cursor.fetchone():
                raise Exception("MySQL连接测试失败")
            eprint("MySQL连接测试成功")
                
        with self.driver.session() as session:
            result = session.run("RETURN 1 AS test")
            if result.single()["test"] != 1:
                raise Exception("Neo4j连接测试失败")
            eprint("Neo4j连接测试成功")

    def create_device_nodes(self):
        """1. 保存设备点到neo4j"""
        try:
            eprint("\n=== 开始创建设备节点 ===")
            
            # 1. 从MySQL查询设备数据
            with self.mysql_conn.cursor() as cursor:
                sql = """
                SELECT DISTINCT 
                    COALESCE(s_device, t_device) as device,
                    COALESCE(s_location, t_location) as location,
                    COALESCE(s_function, t_function) as function,
                    COALESCE(s_ftid, t_ftid) as ftid,
                    'Device' as Type,
                    IF(s_device LIKE '%sim%' OR t_device LIKE '%sim%', 'true', 'false') as isSim,
                    IF(s_device LIKE '%plc%' OR t_device LIKE '%plc%', 'true', 'false') as isPLC,
                    'false' as isTerminal
                FROM v_csv_raw 
                WHERE s_device IS NOT NULL OR t_device IS NOT NULL
                """
                cursor.execute(sql)
                devices = cursor.fetchall()
                eprint(f"从MySQL中获取到 {len(devices)} 个唯一设备")
                
                # 显示前3个设备的信息作为示例
                for i, dev in enumerate(devices[:3]):
                    eprint(f"设备示例 {i+1}: {dev}")

            # 2. 在Neo4j中创建设备节点
            with self.driver.session() as session:
                # 清除现有的设备节点
                session.run("MATCH (d:V_Device) DELETE d")
                eprint("已清除现有设备节点")

                # 创建新的设备节点
                created = 0
                for device in devices:
                    if not device['device']:  # 跳过设备名为空的记录
                        continue
                            
                    result = session.run("""
                        CREATE (d:V_Device {
                            device: $device,
                            location: $location,
                            function: $function,
                            fdid: $ftid,
                            Type: $Type,
                            isSim: $isSim,
                            isPLC: $isPLC,
                            isTerminal: $isTerminal
                        })
                        RETURN d
                    """, device)
                    
                    if result.single():
                        created += 1
                    
                    # 每处理100个节点记录一次进度
                    if created % 100 == 0:
                        eprint(f"已处理 {created} 个设备节点")
                
                eprint(f"成功创建了 {created} 个设备节点")

                # 创建唯一性约束
                try:
                    session.run("""
                        CREATE CONSTRAINT device_id IF NOT EXISTS 
                        FOR (d:V_Device) REQUIRE d.device IS UNIQUE
                    """)
                    eprint("已创建设备名称唯一性约束")
                except Exception as e:
                    eprint(f"创建约束时出现警告（可能已存在）: {str(e)}")

        except Exception as e:
            eprint(f"创建设备节点失败: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            raise

    def create_terminal_nodes(self):
        """2. 保存设备端点到neo4j"""
        # TODO: 实现从MySQL读取端点数据并创建Neo4j节点
        pass

    def create_external_connections(self):
        """3. 保存设备点和点的外连接到neo4j"""
        # TODO: 实现从MySQL读取外部连接数据并创建Neo4j关系
        pass

    def create_internal_connections(self):
        """4. 创建设备内连接到图论"""
        # TODO: 实现从MySQL读取内部连接数据并创建Neo4j关系
        pass

    def process_all(self):
        """执行所有创建操作"""
        try:
            eprint("开始执行数据处理流程")
            self.create_device_nodes()
            # self.create_terminal_nodes()
            # self.create_external_connections()
            # self.create_internal_connections()
            eprint("\n=== 所有操作完成 ===")
        except Exception as e:
            eprint(f"处理过程失败: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            raise

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()
            eprint("Neo4j连接已关闭")
        if hasattr(self, 'mysql_conn') and self.mysql_conn:
            self.mysql_conn.close()
            eprint("MySQL连接已关闭")

def main():
    try:
        eprint("=== 程序开始执行 ===")
        creator = GraphDeviceCreator()
        creator.process_all()
        eprint("=== 程序执行完成 ===")
        return 0
    except Exception as e:
        eprint(f"程序执行失败: {str(e)}")
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        if 'creator' in locals():
            creator.close()

if __name__ == "__main__":
    sys.exit(main())