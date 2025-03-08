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
                    
            # 获取点位类型
            prefix = desc[0].upper()  # 转换为大写以统一处理
            if prefix not in ['A', 'D', 'L', 'K', 'T']:
                # 检查特殊格式，如 "ANA.10", "ANALOG.1" 等
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
                elif char == '.':  # 忽略小数点后的内容，如 V1.1 中的 .1
                    break
                elif char.isdigit():
                    num_str += char
                elif not in_brackets and not char.isdigit():
                    break  # 遇到非数字字符就停止，除非在括号内
                    
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
            
    def _apply_point_type_rules(self, device_points, session):
        """应用点位类型规则"""
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
                        if len(suffix_points) >= 2:  # 至少有两个点位才能连接
                            points_list = list(suffix_points.values())
                            for i in range(len(points_list)):
                                for j in range(i + 1, len(points_list)):
                                    self._create_connection(
                                        session,
                                        points_list[i],
                                        points_list[j],
                                        conn_props
                                    )

    def _create_device_connections(self, session):
        """处理所有设备的内部连接"""
        try:
            # 读取点位数据
            with self.mysql_conn.cursor() as cursor:
                logger.info("\n=== 读取点位数据 ===")
                query = """
                    SELECT id, description, belongtoDevice, FTID
                    FROM v_device_points
                    WHERE belongtoDevice IS NOT NULL
                    AND description != ''
                    AND LEFT(description, 1) IN ('A', 'D', 'L', 'K', 'T')
                    ORDER BY belongtoDevice, description
                """
                cursor.execute(query)
                points = cursor.fetchall()
                
                if not points:
                    logger.info("未找到有效的点位数据")
                    return
                    
                logger.info(f"找到 {len(points)} 个点位")
                
                # 按设备和类型分组点位
                current_device = None
                device_points = {}
                
                for point in points:
                    device = point['belongtoDevice']
                    if device != current_device:
                        # 处理前一个设备的连接
                        if current_device:
                            logger.info(f"\n处理设备 {current_device} 的连接")
                            self._apply_point_type_rules(device_points, session)
                        
                        # 开始新设备的处理
                        current_device = device
                        device_points = {'A': [], 'D': [], 'L': [], 'K': [], 'T': []}
                    
                    prefix, num = self._analyze_point(point['description'])
                    if prefix and num is not None:
                        device_points[prefix].append((num, point))
                
                # 处理最后一个设备
                if current_device:
                    logger.info(f"\n处理设备 {current_device} 的连接")
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
