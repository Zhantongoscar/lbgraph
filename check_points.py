# -*- coding: utf-8 -*-
import sys
import logging
from neo4j import GraphDatabase
import pymysql
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_mysql_points():
    """检查MySQL中的点位数据"""
    logger.info("\n=== MySQL点位数据检查 ===")
    try:
        conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            # 1. 点位类型分布
            cursor.execute("""
                SELECT LEFT(description, 1) as type, COUNT(*) as count
                FROM v_device_points
                WHERE description != '' AND belongtoDevice IS NOT NULL
                GROUP BY LEFT(description, 1)
                ORDER BY type
            """)
            logger.info("\n1. 点位类型分布:")
            for row in cursor.fetchall():
                logger.info(f"类型 {row['type']}: {row['count']}个")
            
            # 2. 按设备分组查看点位
            cursor.execute("""
                SELECT belongtoDevice, 
                       COUNT(*) as total,
                       SUM(CASE WHEN LEFT(description, 1) = 'A' THEN 1 ELSE 0 END) as A_count,
                       SUM(CASE WHEN LEFT(description, 1) = 'D' THEN 1 ELSE 0 END) as D_count,
                       SUM(CASE WHEN LEFT(description, 1) = 'L' THEN 1 ELSE 0 END) as L_count,
                       SUM(CASE WHEN LEFT(description, 1) = 'T' THEN 1 ELSE 0 END) as T_count
                FROM v_device_points
                WHERE description != '' AND belongtoDevice IS NOT NULL
                GROUP BY belongtoDevice
                ORDER BY belongtoDevice
            """)
            logger.info("\n2. 设备点位分布:")
            for row in cursor.fetchall():
                logger.info(f"\n设备: {row['belongtoDevice']}")
                logger.info(f"  总点位数: {row['total']}")
                logger.info(f"  A类点位: {row['A_count']}个")
                logger.info(f"  D类点位: {row['D_count']}个")
                logger.info(f"  L类点位: {row['L_count']}个")
                logger.info(f"  T类点位: {row['T_count']}个")
                
                # 检查具体点位
                cursor.execute("""
                    SELECT description, LEFT(description, 1) as type
                    FROM v_device_points
                    WHERE belongtoDevice = %s
                    AND LEFT(description, 1) IN ('A', 'D', 'L', 'T')
                    ORDER BY description
                """, (row['belongtoDevice'],))
                points = cursor.fetchall()
                if points:
                    logger.info("  点位列表:")
                    for point in points:
                        logger.info(f"    - {point['description']}")
                
    except Exception as e:
        logger.error(f"MySQL查询错误: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def check_neo4j_points():
    """检查Neo4j中的点位数据"""
    logger.info("\n=== Neo4j点位数据检查 ===")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # 1. 总体统计
            result = session.run("""
                MATCH (p:DevicePoint)
                WHERE p.description IS NOT NULL AND p.belongtoDevice IS NOT NULL
                RETURN COUNT(p) as total,
                       COUNT(DISTINCT p.belongtoDevice) as device_count
            """)
            stats = result.single()
            logger.info("\n1. 基本统计:")
            logger.info(f"总点位数: {stats['total']}")
            logger.info(f"设备数量: {stats['device_count']}")

            # 2. 点位类型分布
            results = session.run("""
                MATCH (p:DevicePoint)
                WHERE p.description IS NOT NULL AND p.belongtoDevice IS NOT NULL
                WITH LEFT(p.description, 1) as type, COUNT(*) as count
                ORDER BY type
                RETURN type, count
            """)
            logger.info("\n2. 点位类型分布:")
            for record in results:
                logger.info(f"类型 {record['type']}: {record['count']}个")

            # 3. 按设备分组的点位统计
            results = session.run("""
                MATCH (p:DevicePoint)
                WHERE p.description IS NOT NULL AND p.belongtoDevice IS NOT NULL
                WITH p.belongtoDevice as device,
                     COUNT(*) as total,
                     COUNT(CASE WHEN LEFT(p.description, 1) = 'A' THEN 1 END) as A_count,
                     COUNT(CASE WHEN LEFT(p.description, 1) = 'D' THEN 1 END) as D_count,
                     COUNT(CASE WHEN LEFT(p.description, 1) = 'L' THEN 1 END) as L_count,
                     COUNT(CASE WHEN LEFT(p.description, 1) = 'T' THEN 1 END) as T_count,
                     COLLECT(p.description) as points
                ORDER BY device
                RETURN *
            """)
            logger.info("\n3. 设备点位详情:")
            for record in results:
                logger.info(f"\n设备: {record['device']}")
                logger.info(f"  总点位数: {record['total']}")
                logger.info(f"  A类点位: {record['A_count']}个")
                logger.info(f"  D类点位: {record['D_count']}个")
                logger.info(f"  L类点位: {record['L_count']}个")
                logger.info(f"  T类点位: {record['T_count']}个")
                logger.info(f"  点位列表: {', '.join(record['points'])}")

            # 4. 检查连接情况
            results = session.run("""
                MATCH (p:DevicePoint)
                WHERE p.description IS NOT NULL AND p.belongtoDevice IS NOT NULL
                OPTIONAL MATCH (p)-[r:CONN]->()
                WITH p.description as desc, p.belongtoDevice as device,
                     COUNT(r) as conn_count
                WHERE conn_count = 0
                RETURN desc, device
                ORDER BY device, desc
            """)
            logger.info("\n4. 未创建连接的点位:")
            no_conn_points = list(results)
            for record in no_conn_points:
                logger.info(f"  {record['desc']} (设备: {record['device']})")
            logger.info(f"\n总计 {len(no_conn_points)} 个点位未创建连接")

    except Exception as e:
        logger.error(f"Neo4j查询错误: {e}")
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    logger.info("开始检查点位数据...")
    check_mysql_points()
    check_neo4j_points()
    logger.info("\n检查完成")