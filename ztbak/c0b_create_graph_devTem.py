# -*- coding: utf-8 -*-
import sys
import traceback
import logging
from neo4j import GraphDatabase
import pymysql
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import os
import json

# 加载规则文件
RULES_PATH = os.path.join(os.path.dirname(__file__), 'c0b_inner_rules.json')
with open(RULES_PATH, 'r', encoding='utf-8') as f:
    RULES = json.load(f)

def eprint(*args, **kwargs):
    """打印到stderr"""
    print(*args, file=sys.stderr, **kwargs)
    sys.stderr.flush()

# 创建设备节点
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
# 测试数据库连接
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
# 创建设备节点
    # 创建端子节点
    def create_terminal_nodes(self):
        """2. 保存设备端点到neo4j"""
        try:
            eprint("\n=== 开始创建端子节点 ===")
            
            # 查询端子数据
            with self.mysql_conn.cursor() as cursor:
                # 查询端子数据
                # 注意：添加了location LIKE 'K1.%' 条件
                sql = """
                SELECT DISTINCT
                    s_terminal as terminal,
                    s_device as device,
                    s_location as location,
                    s_function as function,
                    s_ftid as ftid
                FROM v_csv_raw
                WHERE s_terminal IS NOT NULL
                AND s_location LIKE 'K1.%'  -- 只处理K1.开头的位置
                UNION
                SELECT DISTINCT
                    t_terminal as terminal,
                    t_device as device,
                    t_location as location,
                    t_function as function,
                    t_ftid as ftid
                FROM v_csv_raw
                WHERE t_terminal IS NOT NULL
                AND t_location LIKE 'K1.%'  -- 只处理K1.开头的位置
                """
                eprint("仅处理K1.位置的设备的端子")
                cursor.execute(sql)
                terminals = cursor.fetchall()
                eprint(f"从MySQL中获取到 {len(terminals)} 个端子记录")
            
            # 创建端子节点并关联设备
            with self.driver.session() as session:
                # 删除旧数据
                session.run("MATCH (t:V_Terminal) DETACH DELETE t")
                eprint("已清除现有端子节点")

                created = 0
                for terminal in terminals:
                    if not terminal['ftid']:
                        continue
                    
                    # 提取 full_device（即设备的 fdid）
                    full_device = terminal['ftid'].split(':')[0] if ':' in terminal['ftid'] else terminal['ftid']
                    
                    # 创建端子节点并关联设备
                    result = session.run("""
                        // 创建设备节点，并设置属性
                        MERGE (d:V_Device {fdid: $full_device})
                        SET d.function = $function,
                            d.location = $location,
                            d.device = $device,
                            d.isPlc = CASE WHEN $device STARTS WITH 'A2' THEN '1' ELSE '0' END,
                            d.isSim = '0',
                            d.isEnd = '0'
                        // 创建或匹配端子节点
                        MERGE (t:V_Terminal {ftid: $ftid})
                        // 设置端子节点的属性
                        SET t.id = $id,
                            t.function = $function,
                            t.location = $location,
                            t.device = $device,
                            t.terminal = $terminal,
                            t.full_device = $full_device
                        // 创建关系（如果不存在）
                        MERGE (t)-[:belongTo]->(d)
                        MERGE (d)-[:hasTerminal]->(t)
                        RETURN t
                    """, {
                        'id': terminal['ftid'],
                        'ftid': terminal['ftid'],
                        'function': terminal['function'],
                        'location': terminal['location'],
                        'device': terminal['device'],
                        'terminal': terminal['terminal'],
                        'full_device': full_device
                    })
                    if result.single():
                        created += 1
                    if created % 100 == 0 and created > 0:
                        eprint(f"已处理 {created} 个端子节点")
                eprint(f"成功创建了 {created} 个端子节点")
        except Exception as e:
            eprint(f"创建端子节点失败: {str(e)}")
            raise
    def _apply_point_type_rules(self, device_points, session):
        """应用点位类型规则"""
        for rule in RULES.get('pointTypeRules', []):
            rule_type = rule.get('type')
            
            if rule_type == 'adjacentSequence':
                # 处理相邻序号连接规则（如A类和D类点位）
                for point_type in rule.get('pointTypes', []):
                    points = sorted(device_points.get(point_type, []), key=lambda x: x[0])
                    for i in range(len(points) - 1):
                        self._create_connection(
                            session,
                            points[i][1],
                            points[i + 1][1],
                            rule.get('connectionProperties', None)
                        )
                        
            elif rule_type == 'matchingNumbers':
                # 处理相同序号连接规则（如L-T点位组）
                for group in rule.get('pointGroups', []):
                    if len(group) != 2:
                        continue
                    
                    type1, type2 = group
                    points1 = {p[0]: p[1] for p in device_points.get(type1, [])}
                    points2 = {p[0]: p[1] for p in device_points.get(type2, [])}
                    
                    common_nums = set(points1.keys()) & set(points2.keys())
                    for num in common_nums:
                        self._create_connection(
                            session,
                            points1[num],
                            points2[num],
                            rule.get('connectionProperties', None)
                        )
                        
            elif rule_type in ['specificPair', 'buttonPostfix']:
                # 处理特定点位对的连接规则
                for pair in rule.get('pairs', []):
                    desc1, desc2 = pair.get('point1'), pair.get('point2')
                    for points in device_points.values():
                        point1 = next((p[1] for p in points if p[1].get('terminal', '').strip() == desc1), None)
                        point2 = next((p[1] for p in points if p[1].get('terminal', '').strip() == desc2), None)
                        if point1 and point2 and self._check_same_group(point1, point2):
                            self._create_connection(
                                session,
                                point1,
                                point2,
                                pair.get('connectionProperties', None)
                            )
    # 创建内部连接
    def create_connections(self):
        """创建端子之间的内部连接关系"""
        try:
            eprint("\n=== 开始创建端子内部连接 ===")
            
            # 从Neo4j获取设备和端子数据
            with self.driver.session() as session:
                # 按设备分组获取端子
                result = session.run("""
                MATCH (d:V_Device)<-[:belongTo]-(t:V_Terminal)
                WITH d.device as device, d.fdid as fdid, collect(t) as terminals
                RETURN device, fdid, terminals
                """)
                
                for record in result:
                    device = record['device']
                    fdid = record['fdid']
                    terminals = record['terminals']
                    
                    eprint(f"\n处理设备: {device} (FDID: {fdid})")
                    eprint(f"端子数量: {len(terminals)}")
                    
                    # 按类型分组端子
                    device_points = {'A': [], 'D': [], 'L': [], 'K': [], 'T': [], 'B': []}
                    
                    # 分析每个端子的类型和序号
                    for terminal in terminals:
                        terminal_data = dict(terminal)  # 转换Neo4j节点为字典
                        desc = terminal_data.get('terminal', '')
                        prefix, num = self._analyze_point(desc)
                        
                        if prefix and num is not None:
                            terminal_data['description'] = desc  # 添加description字段
                            device_points[prefix].append((num, terminal_data))
                    
                    # 应用连接规则
                    self._apply_point_type_rules(device_points, session)
                
                # 验证连接
                self._verify_connections(session)
                    
        except Exception as e:
            eprint(f"创建内部连接失败: {str(e)}")
            traceback.print_exc(file=sys.stderr)
            raise


    # 分析点位描述，返回类型和序号
    def _analyze_point(self, description):
        """分析点位描述，返回类型和序号"""
        try:
            # 清理和标准化描述
            desc = description.strip()
            if not desc:
                eprint(f"空的点位描述")
                return None, None
                
            # 处理带斜杠的格式，如 "L/L1"
            if '/' in desc:
                parts = desc.split('/')
                if len(parts) == 2:
                    desc = parts[1]
            
            # 处理带.13或.14后缀的数字点位
            if '.' in desc:
                base_num, suffix = desc.split('.')
                if base_num.isdigit() and suffix in ['13', '14']:
                    return 'B', int(base_num)
                    
            # 处理纯数字描述（按钮点位）
            if desc.isdigit():
                return 'B', int(desc)
                    
            # 获取点位类型
            prefix = desc[0].upper()
            if prefix not in ['A', 'D', 'L', 'K', 'T', 'B']:
                if desc.startswith(('ANA.', 'ANALOG.')):
                    eprint(f"跳过模拟量点位: {description}")
                    return None, None
                else:
                    eprint(f"未知的点位类型: {prefix} (来自 {description})")
                    return None, None
                
            # 提取序号
            num_str = ''
            in_brackets = False
            for char in desc[1:]:
                if char == '(':
                    in_brackets = True
                    continue
                elif char == ')':
                    in_brackets = False
                    continue
                elif char == '.':
                    if num_str:
                        break
                    continue
                elif char.isdigit():
                    num_str += char
                elif not in_brackets and not char.isdigit():
                    break
                    
            if num_str:
                num = int(num_str)
                eprint(f"解析点位: {description} -> 类型={prefix}, 序号={num}")
                return prefix, num
            else:
                eprint(f"无法从点位描述中提取序号: {description}")
                return prefix, None
                
        except Exception as e:
            eprint(f"点位描述解析错误 ({description}): {str(e)}")
            return None, None

    def _check_same_group(self, point1, point2):
        """检查两个点位是否属于同一组"""
        def get_group(point):
            ftid = point['ftid']
            parts = ftid.split(':')
            if len(parts) != 2:
                return None
            device_path = parts[0]
            device_parts = device_path.split('-')
            if len(device_parts) < 2:
                return None
            return device_parts[-1]
            
        group1 = get_group(point1)
        group2 = get_group(point2)
        return group1 and group2 and group1 == group2

    def _create_connection(self, session, point1, point2, conn_props=None):
        """创建两个点位之间的双向连接"""
        try:
            # 如果没有提供特定属性，使用默认连接属性
            if conn_props is None:
                conn_props = RULES.get('defaultConnectionProperties', {
                    "voltage": 24.0,
                    "current": 0.1,
                    "resistance": 240.0,
                    "isCable": False,
                    "isInPanel": True,
                    "connType": "devInConn"
                })
            
            # 验证点位存在性并创建连接
            result = session.run("""
                MATCH (p1:V_Terminal {ftid: $point1_id})
                MATCH (p2:V_Terminal {ftid: $point2_id})
                MERGE (p1)-[r1:conn]->(p2)
                SET r1 = $props
                MERGE (p2)-[r2:conn]->(p1)
                SET r2 = $props
                RETURN r1, r2
            """, {
                'point1_id': point1['ftid'],
                'point2_id': point2['ftid'],
                'props': conn_props
            })
            
            return bool(result.single())
            
        except Exception as e:
            eprint(f"创建连接时发生错误: {e}")
            eprint(f"点位1: {point1}")
            eprint(f"点位2: {point2}")
            return False

    def _verify_connections(self, session):
        """验证创建的连接"""
        eprint("\n=== 验证连接结果 ===")
        try:
            # 统计连接数
            result = session.run("""
            MATCH ()-[r:conn]->()
            RETURN COUNT(r) as total
            """)
            total = result.single()['total']
            eprint(f"总共创建了 {total} 个连接")
            
            # 检查每个设备的连接
            results = session.run("""
            MATCH (n1:V_Terminal)-[r:conn]->(n2:V_Terminal)
            WHERE n1.ftid < n2.ftid
            WITH n1.belongtoDevice as device,
                 COUNT(r) as conn_count,
                 COLLECT(DISTINCT [n1.terminal, n2.terminal]) as connections
            RETURN device, conn_count, connections
            ORDER BY device
            """)
            
            for record in results:
                device = record['device']
                conn_count = record['conn_count']
                connections = record['connections']
                
                eprint(f"\n设备 {device}:")
                eprint(f"  连接数量: {conn_count}")
                if connections:
                    eprint("  连接详情:")
                    for conn in connections:
                        eprint(f"    {conn[0]} <-> {conn[1]}")
                    
        except Exception as e:
            eprint(f"验证连接时发生错误: {e}")
            traceback.print_exc(file=sys.stderr)

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

            try:
                self.create_connections()
            except Exception as e:
                eprint(f"创建连接关系失败，但继续执行后续步骤: {str(e)}")
                traceback.print_exc(file=sys.stderr)

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