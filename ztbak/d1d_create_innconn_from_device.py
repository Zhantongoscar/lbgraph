# -*- coding: utf-8 -*-
import sys
import traceback
import os
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
            logger.info("\n=== 初始化数据库连接 ===")
            # 连接MySQL数据库
            self.mysql_conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            
            # 连接Neo4j数据库
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
            if not desc or len(desc) < 2:  # 至少需要一个字母和一个数字
                logger.warning(f"无效的点位描述: {description}")
                return None, None
                
            # 获取点位类型
            prefix = desc[0].upper()  # 转换为大写以统一处理
            if prefix not in ['A', 'D', 'L', 'K', 'T']:
                logger.warning(f"未知的点位类型: {prefix} (来自 {description})")
                return None, None
                
            # 提取序号
            num_str = ''
            for char in desc[1:]:  # 从第二个字符开始
                if char.isdigit():
                    num_str += char
                else:
                    break  # 遇到非数字字符就停止
                    
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

    def _create_connection(self, session, point1, point2):
        """创建两个点位之间的双向连接"""
        try:
            # 首先验证点位存在性
            check_query = """
            MATCH (p1:V_Terminal {FTID: $point1_id}), (p2:V_Terminal {FTID: $point2_id})
            RETURN p1, p2
            """
            logger.info("\n" + "="*50)
            logger.info("执行点位验证查询")
            logger.info("-"*50)
            logger.info("CQL语句:")
            logger.info(check_query.strip())
            logger.info("-"*50)
            logger.info("参数:")
            logger.info(f"  point1_id: {point1['FTID']}")
            logger.info(f"  point2_id: {point2['FTID']}")
            logger.info("="*50)
            result = session.run(check_query,
                               point1_id=point1['FTID'],
                               point2_id=point2['FTID'])
            if not result.single():
                logger.error(f"点位不存在: {point1['description']} 或 {point2['description']}")
                return False
            
            # 创建连接属性
            conn_props = {
                "voltage": 24.0,
                "current": 0.1,
                "resistance": 240.0,
                "isCable": False,
                "isInPanel": True,
                "connType": "in_conn"
            }
            
            # 创建双向连接
            query = """
            MATCH (p1:V_Terminal {FTID: $point1_id}), (p2:V_Terminal {FTID: $point2_id})
            MERGE (p1)-[r1:CONN {
                voltage: 24.0,
                current: 0.1,
                resistance: 240.0,
                isCable: false,
                isInPanel: true,
                connType: 'in_conn'
            }]->(p2)
            MERGE (p2)-[r2:CONN {
                voltage: 24.0,
                current: 0.1,
                resistance: 240.0,
                isCable: false,
                isInPanel: true,
                connType: 'in_conn'
            }]->(p1)
            RETURN COUNT(r1) + COUNT(r2) as count
            """
            
            logger.info("\n" + "="*50)
            logger.info("执行连接创建查询")
            logger.info("-"*50)
            logger.info("CQL语句:")
            logger.info(query.strip())
            logger.info("-"*50)
            logger.info("参数:")
            logger.info(f"  point1_id: {point1['FTID']}")
            logger.info(f"  point2_id: {point2['FTID']}")
            logger.info("  连接属性:")
            for k, v in conn_props.items():
                logger.info(f"    {k}: {v}")
            logger.info("="*50)
            
            result = session.run(query,
                              point1_id=point1['FTID'],
                              point2_id=point2['FTID'])
            
            conn_count = result.single()['count']
            if conn_count == 2:
                logger.info(f"成功创建连接: {point1['description']} <-> {point2['description']}")
                return True
            else:
                logger.error(f"连接创建不完整: 期望2个连接，实际创建{conn_count}个")
                return False
            
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
                device_points = {}
                for point in points:
                    device = point['belongtoDevice']
                    if device not in device_points:
                        device_points[device] = {'A': [], 'D': [], 'L': [], 'K': [], 'T': []}
                    
                    prefix, num = self._analyze_point(point['description'])
                    if prefix and num is not None:  # 只处理能成功解析序号的点位
                        device_points[device][prefix].append((num, point))
                        
                # 处理每个设备的点位组
                logger.info("\n" + "="*50)
                logger.info(f"开始处理 {len(device_points)} 个设备的点位组")
                logger.info("="*50)
                
                for device, type_points in device_points.items():
                    logger.info("\n" + "="*50)
                    logger.info(f"正在处理设备: {device}")
                    logger.info("-"*50)
                    logger.info("设备所有点位信息：")
                    for point_type in ['A', 'D', 'L', 'K', 'T']:
                        points = type_points[point_type]
                        if points:
                            points_info = [f"{p[1]['description']}(FTID:{p[1]['FTID']})" for p in sorted(points, key=lambda x: x[0])]
                            logger.info(f"{point_type}类点位: {points_info}")
                    logger.info("-"*50)
                    
                    # 处理A类点位对
                    if len(type_points['A']) > 0:
                        logger.info(f"\nA类点位配对:")
                        a_points = sorted(type_points['A'], key=lambda x: x[0])
                        logger.info(f"A类点位列表: {[p[1]['description'] for p in a_points]}")
                        
                        # 处理所有A点位
                        for i in range(len(a_points)):
                            point1 = a_points[i][1]
                            # 如果有下一个点，则创建连接
                            if i + 1 < len(a_points):
                                point2 = a_points[i+1][1]
                                logger.info("\n" + "-"*30)
                                logger.info("创建A类点位对连接：")
                                logger.info(f"  点位1: {point1['description']} (FTID:{point1['FTID']})")
                                logger.info(f"  点位2: {point2['description']} (FTID:{point2['FTID']})")
                                logger.info("-"*30)
                                self._create_connection(session, point1, point2)
                    else:
                        logger.info(f"\nA类点位数量不足({len(type_points['A'])}个)，跳过配对")
                        
                    # 处理D类点位对
                    if len(type_points['D']) > 0:
                        logger.info(f"\nD类点位配对:")
                        d_points = sorted(type_points['D'], key=lambda x: x[0])
                        logger.info(f"D类点位列表: {[p[1]['description'] for p in d_points]}")
                        
                        # 处理所有D点位
                        for i in range(len(d_points)):
                            point1 = d_points[i][1]
                            # 如果有下一个点，则创建连接
                            if i + 1 < len(d_points):
                                point2 = d_points[i+1][1]
                                logger.info("\n" + "-"*30)
                                logger.info("创建D类点位对连接：")
                                logger.info(f"  点位1: {point1['description']} (FTID:{point1['FTID']})")
                                logger.info(f"  点位2: {point2['description']} (FTID:{point2['FTID']})")
                                logger.info("-"*30)
                                self._create_connection(session, point1, point2)
                    else:
                        logger.info(f"\nD类点位数量不足({len(type_points['D'])}个)，跳过配对")
                        
                    # L-K-T点位组
                    l_points = sorted(type_points['L'], key=lambda x: x[0])
                    k_points = sorted(type_points['K'], key=lambda x: x[0])
                    t_points = sorted(type_points['T'], key=lambda x: x[0])
                    
                    if len(l_points) > 0 or len(k_points) > 0 or len(t_points) > 0:
                        logger.info(f"\nL-K-T点位配对:")
                        logger.info(f"L类点位: {[p[1]['description'] for p in l_points]}")
                        logger.info(f"K类点位: {[p[1]['description'] for p in k_points]}")
                        logger.info(f"T类点位: {[p[1]['description'] for p in t_points]}")
                        
                        # 构建序号到点位的映射
                        l_map = {p[0]: p[1] for p in l_points}
                        k_map = {p[0]: p[1] for p in k_points}
                        t_map = {p[0]: p[1] for p in t_points}
                        
                        # 找出共同的序号
                        common_nums = set(l_map.keys()) & set(k_map.keys()) & set(t_map.keys())
                        logger.info(f"找到{len(common_nums)}组匹配的L-K-T点位")
                        
                        for num in sorted(common_nums):
                            l_point = l_map[num]
                            k_point = k_map[num]
                            t_point = t_map[num]
                            
                            logger.info("\n" + "-"*30)
                            logger.info(f"创建L-K-T类点位组连接 (序号{num})：")
                            logger.info(f"  L点位: {l_point['description']} (FTID:{l_point['FTID']})")
                            logger.info(f"  K点位: {k_point['description']} (FTID:{k_point['FTID']})")
                            logger.info(f"  T点位: {t_point['description']} (FTID:{t_point['FTID']})")
                            logger.info("-"*30)
                            
                            # 创建L-K连接
                            self._create_connection(session, l_point, k_point)
                            # 创建K-T连接
                            self._create_connection(session, k_point, t_point)
                    else:
                        logger.info(f"L、K或T点位不足，跳过L-K-T配对")
                
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
