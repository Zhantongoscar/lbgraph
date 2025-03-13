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
            
            # 2. 从MySQL查询设备数据
            with self.mysql_conn.cursor() as cursor:
                # 修改查询，分别获取源设备和目标设备
                sql = """
                SELECT 
                    s_device as device,
                    s_location as location,
                    s_function as function,
                    s_ftid as ftid,
                    'Device' as Type,
                    IF(s_device LIKE '%sim%', 'true', 'false') as isSim,
                    IF(s_device LIKE '%plc%', 'true', 'false') as isPLC,
                    'false' as isTerminal,
                    'source' as role
                FROM v_csv_raw 
                WHERE s_device IS NOT NULL
                UNION
                SELECT 
                    t_device as device,
                    t_location as location,
                    t_function as function,
                    t_ftid as ftid,
                    'Device' as Type,
                    IF(t_device LIKE '%sim%', 'true', 'false') as isSim,
                    IF(t_device LIKE '%plc%', 'true', 'false') as isPLC,
                    'false' as isTerminal,
                    'target' as role
                FROM v_csv_raw 
                WHERE t_device IS NOT NULL
                """
                cursor.execute(sql)
                devices = cursor.fetchall()
                eprint(f"从MySQL中获取到 {len(devices)} 个设备记录")
                
                # 显示前3个设备的信息作为示例
                for i, dev in enumerate(devices[:3]):
                    eprint(f"设备示例 {i+1}: {dev}")
                
                # 按设备名称对记录进行分组，保留唯一设备
                unique_devices = {}
                for device in devices:
                    device_name = device['device']
                    if device_name not in unique_devices:
                        unique_devices[device_name] = device
                eprint(f"合并后得到 {len(unique_devices)} 个唯一设备")

            # 2. 在Neo4j中创建设备节点
            with self.driver.session() as session:
                # 首先删除所有关系，然后再删除节点
                try:
                    # 删除与V_Device相关的所有关系
                    session.run("MATCH (d:V_Device)-[r]-() DELETE r")
                    eprint("已删除设备节点的所有关系")
                    
                    # 删除所有V_Device节点
                    session.run("MATCH (d:V_Device) DELETE d")
                    eprint("已清除现有设备节点")
                except Exception as e:
                    eprint(f"清除现有设备节点时出错: {str(e)}")
                    # 尝试使用DETACH DELETE（这会同时删除节点和关系）
                    try:
                        session.run("MATCH (d:V_Device) DETACH DELETE d")
                        eprint("已使用DETACH DELETE清除现有设备节点")
                    except Exception as e2:
                        eprint(f"尝试DETACH DELETE设备节点时出错: {str(e2)}")
                        eprint("继续执行，将尝试创建新节点")

                # 创建新的设备节点
                created = 0
                for device_name, device in unique_devices.items():
                    # 从ftid提取设备ID
                    device_id = None
                    if device['ftid']:
                        try:
                            # 尝试从ftid中提取设备ID
                            parts = device['ftid'].split(':')
                            if len(parts) > 1:
                                pre_colon = parts[0]
                                if '-' in pre_colon:
                                    device_id = pre_colon.split('-')[-1]
                                else:
                                    device_id = pre_colon
                            else:
                                device_id = device['ftid']
                            eprint(f"从ftid '{device['ftid']}' 提取出的设备ID: '{device_id}'")
                        except Exception as e:
                            eprint(f"提取设备ID时出错: {str(e)}, ftid: {device['ftid']}")
                            device_id = device_name
                    
                    if not device_id:
                        device_id = device_name
                    
                    # 更新设备字典，添加设备ID
                    device_data = device.copy()
                    device_data['device_id'] = device_id
                    
                    # 创建或更新节点
                    result = session.run(""" MERGE (d:V_Device {device: $device})
                        ON CREATE SET d.location = $location, d.function = $function, d.fdid = $ftid, d.device_id = $device_id, d.Type = $Type, d.isSim = $isSim, d.isPLC = $isPLC, d.isTerminal = $isTerminal, d.roles = [$role]
                        ON MATCH SET
                            d.roles = CASE WHEN $role IN d.roles THEN d.roles ELSE d.roles + $role END
                        RETURN d
                    """, device_data)
                    
                    if result.single():
                        created += 1
                    
                    if created % 100 == 0:
                        eprint(f"已处理 {created} 个设备节点")
                
                eprint(f"成功创建或更新了 {created} 个设备节点")
                
        except Exception as e:
            eprint(f"创建设备节点失败: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            raise
    
    def create_terminal_nodes(self):
        """2. 保存设备端点到neo4j"""
        try:
            eprint("\n=== 开始创建端子节点 ===")
            
            # 1. 从MySQL查询端子数据
            with self.mysql_conn.cursor() as cursor:
                # 查询源端点，只包含实际存在的列
                sql_source = """
                SELECT 
                    s_ftid as ftid,
                    COALESCE(s_device, '') as device,
                    COALESCE(s_function, '') as function,
                    COALESCE(s_location, '') as location,
                    COALESCE(s_terminal, '') as terminal
                FROM v_csv_raw 
                WHERE s_ftid IS NOT NULL
                """
                try:
                    cursor.execute(sql_source)
                    source_terminals = cursor.fetchall()
                    eprint(f"从MySQL中获取到 {len(source_terminals)} 个源端子")
                except Exception as e:
                    eprint(f"查询源端子时出错: {str(e)}")
                    source_terminals = []
                
                # 查询目标端点
                sql_target = """
                SELECT 
                    t_ftid as ftid,
                    COALESCE(t_device, '') as device,
                    COALESCE(t_function, '') as function,
                    COALESCE(t_location, '') as location,
                    COALESCE(t_terminal, '') as terminal
                FROM v_csv_raw 
                WHERE t_ftid IS NOT NULL
                """
                try:
                    cursor.execute(sql_target)
                    target_terminals = cursor.fetchall()
                    eprint(f"从MySQL中获取到 {len(target_terminals)} 个目标端子")
                except Exception as e:
                    eprint(f"查询目标端子时出错: {str(e)}")
                    target_terminals = []
                
                # 合并端子列表
                all_terminals = source_terminals + target_terminals
                # 使用字典进行去重
                unique_terminals = {}
                for terminal in all_terminals:
                    ftid = terminal['ftid']
                    if ftid not in unique_terminals:
                        unique_terminals[ftid] = terminal
                
                terminals = list(unique_terminals.values())
                eprint(f"合并并去重后共有 {len(terminals)} 个唯一端子")
                
                # 显示前3个端子的信息作为示例
                for i, term in enumerate(terminals[:3]):
                    eprint(f"端子示例 {i+1}: {term}")

            # 2. 在Neo4j中创建端子节点
            with self.driver.session() as session:
                # 首先删除所有关系，然后再删除节点
                try:
                    session.run("MATCH (t:V_Terminal)-[r]-() DELETE r")
                    eprint("已删除端子节点的所有关系")
                    session.run("MATCH (t:V_Terminal) DELETE t")
                    eprint("已清除现有端子节点")
                except Exception as e:
                    eprint(f"清除现有端子节点时出错: {str(e)}")
                    try:
                        session.run("MATCH (t:V_Terminal) DETACH DELETE t")
                        eprint("已使用DETACH DELETE清除现有端子节点")
                    except Exception as e2:
                        eprint(f"尝试DETACH DELETE端子节点时出错: {str(e2)}")
                        eprint("继续执行，将尝试创建新节点")

                # 创建新的端子节点
                created = 0
                for terminal in terminals:
                    if not terminal['ftid']:  # 跳过ftid为空的记录
                        continue
                    
                    # 从ftid提取设备ID和端子ID（这些信息仅供内部使用，不写入Neo4j）
                    device_id = None
                    terminal_id = None
                    if terminal['ftid'] and ':' in terminal['ftid']:
                        parts = terminal['ftid'].split(':')
                        if '-' in parts[0]:
                            device_part = parts[0].split('-')[-1]
                            device_id = device_part
                        else:
                            device_id = parts[0]
                        terminal_id = parts[1] if len(parts) > 1 else ""
                    
                    # 提取full_device（从ftid中获取冒号前的部分）
                    f_device = terminal['ftid'].split(':')[0] if ':' in terminal['ftid'] else terminal['ftid']
                    
                    # 生成一个唯一ID，可以使用ftid作为唯一ID
                    terminal_id_value = terminal['ftid']
                    
                    result = session.run("""
                        CREATE (t:V_Terminal {
                            id: $id,
                            ftid: $ftid,
                            function: $function,
                            location: $location,
                            device: $device,
                            terminal: $terminal,
                            Type: $Type,
                            isSocket: $isSocket,
                            isSetPoint: $isSetPoint,
                            isSensePoint: $isSensePoint,
                            current: $current,
                            voltage: $voltage,
                            resistance: $resistance,
                            full_device: $full_device
                        })
                        RETURN t
                    """, {
                        'id': terminal_id_value,  # 使用ftid作为id
                        'ftid': terminal['ftid'],
                        'function': terminal['function'],
                        'location': terminal['location'],
                        'device': terminal['device'],
                        'terminal': terminal['terminal'],
                        'Type': '',  # 不使用查询的Type
                        'isSocket': None,
                        'isSetPoint': None,
                        'isSensePoint': None,
                        'current': None,
                        'voltage': None,
                        'resistance': None,
                        'full_device': f_device
                        # 排除 'description', 'device_id', 'raw', 'terminal_id'
                    })
                    
                    if result.single():
                        created += 1
                    
                    # 每处理100个节点记录一次进度
                    if created % 100 == 0 and created > 0:
                        eprint(f"已处理 {created} 个端子节点")
                
                eprint(f"成功创建了 {created} 个端子节点")

                # 创建唯一性约束 - 使用id属性作为唯一性约束
                try:
                    session.run(""" CREATE CONSTRAINT terminal_id IF NOT EXISTS 
                        FOR (t:V_Terminal) REQUIRE t.id IS UNIQUE
                    """)
                    eprint("已创建端子ID唯一性约束")
                except Exception as e:
                    eprint(f"创建约束时出现警告（可能已存在）: {str(e)}")

        except Exception as e:
            eprint(f"创建端子节点失败: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            raise

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
            
            # 在开始处理前，先尝试清理数据库（如果有必要）
            try:
                with self.driver.session() as session:
                    # 删除所有关系
                    session.run("MATCH ()-[r]-() DELETE r")
                    eprint("已删除所有关系")
                    
                    # 删除所有节点
                    session.run("MATCH (n) DELETE n")
                    eprint("已删除所有节点")
            except Exception as e:
                eprint(f"清理数据库时出错（可能是正常的）: {str(e)}")
            
            # 继续正常流程

            try:
                self.create_terminal_nodes()
            except Exception as e:
                eprint(f"创建端子节点失败，但继续执行后续步骤: {str(e)}")
                traceback.print_exc(file=sys.stderr)

            # try:
            #     self.create_device_nodes()
            # except Exception as e:
            #     eprint(f"创建设备节点失败，但继续执行后续步骤: {str(e)}")
            #     traceback.print_exc(file=sys.stderr)
                             
            # 其他步骤
            # ...

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