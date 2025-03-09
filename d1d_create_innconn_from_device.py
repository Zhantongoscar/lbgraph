# -*- coding: utf-8 -*-
import sys
import traceback
import os
import json
import logging
from neo4j import GraphDatabase
import pymysql
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 设置日志记录
def setup_logger():
    logger = logging.getLogger('InnerConnLogger')
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()

class InnerConnCreator:
    def __init__(self):
        try:
            logger.info("\n=== 初始化数据库连接和加载规则 ===")
            # 加载规则文件
            rules_path = os.path.join(os.path.dirname(__file__), 'd1d_inner_rules.json')
            with open(rules_path, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
            logger.info(f"已加载规则文件: {rules_path}")
            
            # 连接数据库
            self.mysql_conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            
            # 测试连接
            self._test_connections()
            logger.info("数据库连接测试成功")
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            logger.error(traceback.format_exc())
            raise

    def _test_connections(self):
        """测试数据库连接"""
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            if not cursor.fetchone():
                raise Exception("MySQL连接测试失败")
                
        with self.driver.session() as session:
            result = session.run("RETURN 1 AS test")
            if result.single()["test"] != 1:
                raise Exception("Neo4j连接测试失败")

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'driver'):
            self.driver.close()
        if hasattr(self, 'mysql_conn'):
            self.mysql_conn.close()
        logger.info("数据库连接已关闭")

    def _analyze_point(self, description):
        """分析点位描述，返回类型和序号"""
        try:
            # 清理和标准化描述
            desc = description.strip()
            if not desc:
                logger.warning(f"空的点位描述")
                return None, None
                
            # 处理带斜杠的格式，如 "L/L1"
            if '/' in desc:
                parts = desc.split('/')
                if len(parts) == 2:
                    # 使用第二部分，因为它通常包含完整信息
                    desc = parts[1]
            
            # 处理带.13或.14后缀的数字点位
            if '.' in desc:
                base_num, suffix = desc.split('.')
                if base_num.isdigit() and suffix in ['13', '14']:
                    return 'B', int(base_num)  # 返回基础编号作为按钮类型点位
                    
            # 处理纯数字描述（如按钮点位 "1", "4"）
            if desc.isdigit():
                return 'B', int(desc)  # 使用'B'表示按钮类型
                    
            # 获取点位类型
            prefix = desc[0].upper()  # 转换为大写以统一处理
            if prefix not in ['A', 'D', 'L', 'K', 'T', 'B']:
                # 检查特殊格式
                if desc.startswith(('ANA.', 'ANALOG.')):
                    logger.info(f"跳过模拟量点位: {description}")
                    return None, None
                else:
                    logger.warning(f"未知的点位类型: {prefix} (来自 {description})")
                    return None, None
                
            # 提取序号，支持更多格式
            num_str = ''
            in_brackets = False
            for char in desc[1:]:
                if char == '(':
                    in_brackets = True
                    continue
                elif char == ')':
                    in_brackets = False
                    continue
                elif char == '.':  # 处理小数点后的内容
                    if num_str:  # 如果已经有数字，就停止解析
                        break
                    continue  # 否则继续解析（对于 .1 .2 这样的后缀）
                elif char.isdigit():
                    num_str += char
                elif not in_brackets and not char.isdigit():
                    break
                    
            if num_str:
                num = int(num_str)
                logger.info(f"解析点位: {description} -> 类型={prefix}, 序号={num}")
                return prefix, num
            else:
                logger.warning(f"无法从点位描述中提取序号: {description}")
                return prefix, None
                
        except Exception as e:
            logger.error(f"点位描述解析错误 ({description}): {str(e)}")
            return None, None

    def _create_connection(self, session, point1, point2, conn_props=None):
        """创建两个点位之间的双向连接"""
        try:
            # 首先验证点位存在性
            check_query = """
            MATCH (p1:V_Terminal {FTID: $point1_id}), (p2:V_Terminal {FTID: $point2_id})
            RETURN p1, p2
            """
            result = session.run(check_query,
                               point1_id=point1['FTID'],
                               point2_id=point2['FTID'])
            if not result.single():
                logger.error(f"点位不存在: {point1['description']} 或 {point2['description']}")
                return False
            
            # 使用默认连接属性，如果没有提供特定属性
            if conn_props is None:
                conn_props = self.rules.get('defaultConnectionProperties', {
                    "voltage": 24.0,
                    "current": 0.1,
                    "resistance": 240.0,
                    "isCable": False,
                    "isInPanel": True,
                    "connType": "devInConn"
                })
            
            # 将属性转换为Cypher语法的字面量字符串
            props_str = "{"
            props_str += ", ".join(f"{k}: {repr(v)}" for k, v in conn_props.items())
            props_str += "}"
            
            # 创建双向连接，使用字面量属性
            query = f"""
            MATCH (p1:V_Terminal {{FTID: $point1_id}}), (p2:V_Terminal {{FTID: $point2_id}})
            MERGE (p1)-[r1:CONN {props_str}]->(p2)
            MERGE (p2)-[r2:CONN {props_str}]->(p1)
            RETURN COUNT(r1) + COUNT(r2) as count
            """
            
            logger.info(f"\n创建连接: {point1['description']} <-> {point2['description']}")
            logger.info(f"连接属性: {conn_props}")
            
            result = session.run(query,
                              point1_id=point1['FTID'],
                              point2_id=point2['FTID'])
            
            conn_count = result.single()['count']
            return conn_count == 2
            
        except Exception as e:
            logger.error(f"创建连接时发生错误: {e}")
            logger.error(f"点位1: {point1}")
            logger.error(f"点位2: {point2}")
            return False

    def create_inner_connections(self):
        """执行设备内部连接创建"""
        try:
            with self.driver.session() as session:
                # 清理现有的连接
                logger.info("\n=== 清理现有连接 ===")
                # 注释掉删除操作
                #session.run("MATCH ()-[r:CONN {connType: 'in_conn'}]->() DELETE r")
                #logger.info("已删除现有的设备内部连接")
                
                # 创建新的连接
                self._create_device_connections(session)
                
                # 验证创建的连接
                self._verify_connections(session)
                
        except Exception as e:
            logger.error(f"创建内部连接时发生错误: {e}")
            logger.error(traceback.format_exc())
            raise
            
    def _create_connections_by_type(self, device_points, session):
        """根据点位的原始Type创建连接"""
        # 收集所有点位
        all_points = []
        for points in device_points.values():
            all_points.extend(points)
            
        # 按原始Type分组
        type_groups = {}
        for num, point in all_points:
            orig_type = point.get('Type', '')
            if orig_type:
                if orig_type not in type_groups:
                    type_groups[orig_type] = []
                type_groups[orig_type].append(point)
                
        # 创建连接
        connected_points = set()  # 记录已连接的点位
        connections_made = False  # 标记是否创建了任何连接
        
        # 处理 AX 类型点位
        for type_name, points in type_groups.items():
            if not type_name.startswith('AX_'):
                continue
                
            # 解析类型编号
            parts = type_name.split('_')
            if len(parts) != 3:
                continue
                
            type_num = parts[2]  # 获取类型编号
            
            # 查找相同编号的其他点位
            related_points = []
            for other_type, other_points in type_groups.items():
                if other_type.startswith('AX_') and other_type.endswith(type_num):
                    related_points.extend(other_points)
                    
            # 创建连接
            if len(related_points) >= 2:
                # 检查是否有COM点位
                com_point = next((p for p in related_points if 'COM' in p['Type']), None)
                if com_point:
                    # 与COM点位相连
                    for point in related_points:
                        if point != com_point:
                            conn_type = 'NC' if 'NC' in point['Type'] else 'NO'
                            conn_props = {
                                "voltage": 24.0,
                                "current": 0.1,
                                "resistance": 240.0,
                                "isCable": False,
                                "isInPanel": True,
                                "connType": conn_type
                            }
                            if self._create_connection(session, com_point, point, conn_props):
                                connected_points.add(com_point['FTID'])
                                connected_points.add(point['FTID'])
                                connections_made = True
                                
        return connections_made, connected_points

    def _apply_point_type_rules(self, device_points, session):
        """应用点位类型规则"""
        # 首先尝试根据原始Type创建连接
        connections_made, connected_points = self._create_connections_by_type(device_points, session)
        
        # 如果没有根据原始Type创建任何连接，则应用外置规则
        if not connections_made:
            for rule in self.rules.get('pointTypeRules', []):
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
                    # 处理相同序号连接规则（如L-K-T点位组）
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
                            
                elif rule_type == 'specificPair':
                    # 处理特定点位对的连接规则
                    for pair in rule.get('pairs', []):
                        desc1, desc2 = pair.get('point1'), pair.get('point2')
                        for points in device_points.values():
                            point1 = next((p[1] for p in points if p[1]['description'].strip() == desc1), None)
                            point2 = next((p[1] for p in points if p[1]['description'].strip() == desc2), None)
                            if point1 and point2:
                                self._create_connection(
                                    session,
                                    point1,
                                    point2,
                                    pair.get('connectionProperties', None)
                                )
                                
                elif rule_type == 'buttonPostfix':
                    # 处理带特定后缀的按钮连接
                    if 'postfixes' in rule:
                        # 原有的.1,.2后缀处理逻辑
                        postfixes = rule.get('postfixes', [])
                        conn_props = rule.get('connectionProperties', None)
                        
                        # 遍历所有点位找到带指定后缀的点位对
                        for points in device_points.values():
                            # 按后缀分组点位
                            postfix_groups = {}
                            for num, point in points:
                                desc = point['description'].strip()
                                base_desc = None
                                matched_postfix = None
                                
                                # 检查点位是否带有指定后缀
                                for postfix in postfixes:
                                    if desc.endswith(postfix):
                                        base_desc = desc[:-len(postfix)]
                                        matched_postfix = postfix
                                        break
                                        
                                if base_desc:
                                    if base_desc not in postfix_groups:
                                        postfix_groups[base_desc] = {}
                                    postfix_groups[base_desc][matched_postfix] = point
                            
                            # 创建具有相同基础描述的点位之间的连接
                            for base_desc, suffix_points in postfix_groups.items():
                                if len(suffix_points) >= 2:
                                    points_list = list(suffix_points.values())
                                    for i in range(len(points_list)):
                                        for j in range(i + 1, len(points_list)):
                                            self._create_connection(
                                                session,
                                                points_list[i],
                                                points_list[j],
                                                conn_props
                                            )
                    
                    # 处理新的postfixPairs规则
                    if 'postfixPairs' in rule:
                        for pair in rule.get('postfixPairs', []):
                            prefix = pair.get('prefix')
                            postfix1 = pair.get('postfix1')
                            postfix2 = pair.get('postfix2')
                            conn_props = pair.get('connectionProperties')
                            
                            # 在所有点位中查找匹配的点位对
                            for points in device_points.values():
                                points_dict = {p[1]['description'].strip(): p[1] for p in points}
                                
                                # 构造完整的点位描述
                                point1_desc = f"{prefix}{postfix1}"
                                point2_desc = f"{prefix}{postfix2}"
                                
                                if point1_desc in points_dict and point2_desc in points_dict:
                                    self._create_connection(
                                        session,
                                        points_dict[point1_desc],
                                        points_dict[point2_desc],
                                        conn_props
                                    )
                
                elif rule_type == 'buttonPair':
                    # 处理成对出现的按钮连接
                    for pair in rule.get('pairs', []):
                        point1_desc = pair.get('point1')
                        point2_desc = pair.get('point2')
                        conn_props = pair.get('connectionProperties', None)
                        
                        # 在所有点位类型中查找匹配的点位对
                        for points in device_points.values():
                            points_dict = {str(p[1]['description'].strip()): p[1] for p in points}
                            
                            if point1_desc in points_dict and point2_desc in points_dict:
                                self._create_connection(
                                    session,
                                    points_dict[point1_desc],
                                    points_dict[point2_desc],
                                    conn_props
                                )

    def _log_device_points_info(self, device_points):
        """记录设备点位的详细信息"""
        total_points = sum(len(points) for points in device_points.values())
        type_counts = {k: len(v) for k, v in device_points.items() if v}
        
        # 简单的统计信息
        logger.info(f"\n点位总数: {total_points}")

        # 添加点位列表概览
        logger.info("\n点位列表:")
        for point_type, points in device_points.items():
            if points:
                points_desc = [f"{p[1]['description']}" for p in sorted(points, key=lambda x: x[0])]
                logger.info(f"  {point_type}类: {', '.join(points_desc)}")
        
        logger.info("\n点位类型统计:")
        if type_counts:
            logger.info("按类型: " + ", ".join([f"{k}:{v}" for k, v in type_counts.items()]))
        
        # 点位详细信息
        logger.info("\n点位详细信息:")
        for point_type, points in device_points.items():
            if points:
                sorted_points = sorted(points, key=lambda x: x[0])
                for num, point in sorted_points:
                    logger.info(f"点位 {point['description']}:")
                    logger.info(f" 所属设备: {point['belongtoDevice']}；设备Device: {point.get('deviceName', 'N/A')}")
                    logger.info(f" FTID: {point['FTID']}   点位原始Type: {point.get('Type', 'N/A')}")

    def _create_device_connections(self, session):
        """处理所有设备的内部连接"""
        try:
            with self.mysql_conn.cursor() as cursor:
                logger.info("\n=== 读取点位数据 ===")
                query = """
                    SELECT 
                        dp.*,
                        d.Type as deviceType,
                        d.Device as deviceName,
                        d.Function as deviceFunction,
                        d.Location as deviceLocation
                    FROM v_device_points dp
                    LEFT JOIN v_devices d ON dp.belongtoDevice = d.FDID
                    WHERE dp.belongtoDevice IS NOT NULL
                    AND dp.description != ''
                    AND dp.Location REGEXP '^K1\\.'  -- 仅处理K1.开头的Location
                    AND (
                        LEFT(dp.description, 1) IN ('A', 'D', 'L', 'K', 'T')
                        OR dp.description REGEXP '^[0-9]+$'
                        OR dp.description REGEXP '[0-9]+\\.[0-9]+$'
                        OR dp.description REGEXP '[A-Za-z]+[0-9]*\\.[0-9]+$'
                    )
                    AND dp.belongtoDevice NOT REGEXP '-X[0-9]'
                    AND dp.belongtoDevice NOT REGEXP '-X[0-9][0-9]'
                    ORDER BY dp.Location, dp.belongtoDevice, dp.Type, dp.description
                """
                cursor.execute(query)
                points = cursor.fetchall()
                
                if not points:
                    logger.info("未找到有效的点位数据")
                    return
                    
                logger.info(f"找到 {len(points)} 个点位")
                
                # 按设备和类型分组点位
                current_device = None
                current_location = None
                device_points = {'A': [], 'D': [], 'L': [], 'K': [], 'T': [], 'B': []}
                current_device_info = None
                
                for point in points:
                    device = point['belongtoDevice']
                    location = point['Location']
                    
                    # 当设备或位置发生变化时处理连接
                    if device != current_device or location != current_location:
                        # 处理前一个设备的连接
                        if current_device:
                            logger.info(f"\n{'='*50}")
                            logger.info(f"处理位置: {current_location}")
                            logger.info(f"处理设备: {current_device}")
                            if current_device_info:
                                logger.info(f"设备类型: {current_device_info['deviceType']}")
                                logger.info(f"设备名称: {current_device_info['deviceName']}")
                            logger.info(f"{'='*50}")
                            self._log_device_points_info(device_points)  # 添加点位信息汇总显示
                            self._apply_point_type_rules(device_points, session)
                        
                        # 开始新设备的处理
                        current_device = device
                        current_location = location
                        device_points = {'A': [], 'D': [], 'L': [], 'K': [], 'T': [], 'B': []}
                        current_device_info = {
                            'deviceType': point['deviceType'],
                            'deviceName': point['deviceName']
                        }
                    
                    prefix, num = self._analyze_point(point['description'])
                    if prefix and num is not None:
                        device_points[prefix].append((num, point))
                
                # 处理最后一个设备
                if current_device:
                    logger.info(f"\n{'='*50}")
                    logger.info(f"处理位置: {current_location}")
                    logger.info(f"处理设备: {current_device}")
                    if current_device_info:
                        logger.info(f"设备类型: {current_device_info['deviceType']}")
                        logger.info(f"设备名称: {current_device_info['deviceName']}")
                    logger.info(f"{'='*50}")
                    self._log_device_points_info(device_points)  # 添加点位信息汇总显示
                    self._apply_point_type_rules(device_points, session)
                
        except Exception as e:
            logger.error(f"处理设备连接时发生错误: {e}")
            logger.error(traceback.format_exc())
            raise

    def _verify_connections(self, session):
        """验证创建的连接"""
        logger.info("\n=== 验证连接结果 ===")
        try:
            # 统计连接数
            count_query = """
            MATCH ()-[r:CONN {connType: 'in_conn'}]->()
            RETURN COUNT(r) as total
            """
            result = session.run(count_query)
            total = result.single()['total']
            logger.info(f"总共创建了 {total} 个连接")
            
            # 检查每个设备的连接
            device_query = """
            MATCH (n1:V_Terminal)-[r:CONN {connType: 'in_conn'}]->(n2:V_Terminal)
            WHERE n1.FTID < n2.FTID  // 避免重复计数
            WITH n1.belongtoDevice as device,
                 COUNT(r) as conn_count,
                 COLLECT(DISTINCT [n1.description, n2.description]) as connections
            RETURN device, conn_count, connections
            ORDER BY device
            """
            results = session.run(device_query)
            
            for record in results:
                device = record['device']
                conn_count = record['conn_count']
                connections = record['connections']
                
                logger.info(f"\n设备 {device}:")
                logger.info(f"  连接数量: {conn_count}")
                logger.info("  连接详情:")
                for conn in connections:
                    logger.info(f"    {conn[0]} <-> {conn[1]}")
                    
        except Exception as e:
            logger.error(f"验证连接时发生错误: {e}")
            logger.error(traceback.format_exc())

def main():
    try:
        creator = InnerConnCreator()
        creator.create_inner_connections()
        return 0
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return 1
    finally:
        if 'creator' in locals():
            creator.close()

if __name__ == "__main__":
    sys.exit(main())
