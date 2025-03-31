#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
import json
import logging
from datetime import datetime

# 配置日志输出到文件和控制台
log_file = f'create_db_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_project_id():
    project_id = input("请输入项目ID（直接回车默认为EOS1550）：").strip()
    return project_id if project_id else 'EOS1550'

def create_and_fill_tables():
    try:
        # 获取项目ID
        project_id = get_project_id()
        logger.info(f"使用项目ID: {project_id}")

        # 加载数据库配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)['mysql']

        # 连接到数据库
        conn = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info(f"已连接到数据库 {config['host']}")

        with conn.cursor() as cursor:
            # 1. 创建设备表
            logger.info("创建v_csv_device表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS v_csv_device (
                    id INT NOT NULL AUTO_INCREMENT,
                    fdid VARCHAR(255) NOT NULL,
                    Function VARCHAR(255),
                    Location VARCHAR(255),
                    Device VARCHAR(255),
                    isInPanel TINYINT(1) DEFAULT 1,
                    Type VARCHAR(50),
                    isSim TINYINT(1) DEFAULT 0,
                    isPLC TINYINT(1) DEFAULT 0,
                    isTerminal TINYINT(1) DEFAULT 0,
                    project_id VARCHAR(255) DEFAULT 'EOS1550',
                    PRIMARY KEY (id),
                    UNIQUE KEY uk_fdid (fdid),
                    INDEX idx_location (Location),
                    INDEX idx_device (Device),
                    INDEX idx_project (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 2. 创建端子表
            logger.info("创建v_csv_devpoint表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS v_csv_devpoint (
                    id INT NOT NULL AUTO_INCREMENT,
                    raw VARCHAR(255) NOT NULL,
                    ftid VARCHAR(255) NOT NULL,
                    belongtoDevice VARCHAR(255),
                    Function VARCHAR(255),
                    Location VARCHAR(255),
                    Device VARCHAR(255),
                    Terminal VARCHAR(255),
                    Type VARCHAR(50),
                    voltage DOUBLE DEFAULT 0,
                    current DOUBLE DEFAULT 0,
                    resistance DOUBLE DEFAULT 0,
                    isInPanel TINYINT(1) DEFAULT 0,
                    isSocket TINYINT(1) DEFAULT 0,
                    isSetPoint TINYINT(1) DEFAULT 0,
                    isSensePoint TINYINT(1) DEFAULT 0,
                    project_id VARCHAR(255) DEFAULT 'EOS1550',
                    PRIMARY KEY (id),
                    INDEX idx_ftid (ftid),
                    INDEX idx_location_device (Location, Device),
                    INDEX idx_project (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 3. 创建连接表
            logger.info("创建v_csv_conn表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS v_csv_conn (
                    id INT NOT NULL AUTO_INCREMENT,
                    connNo VARCHAR(255) NOT NULL,
                    source VARCHAR(255) NOT NULL,
                    target VARCHAR(255) NOT NULL,
                    color VARCHAR(50),
                    isCable TINYINT(1) DEFAULT 0,
                    isInPanel TINYINT(1) DEFAULT 0,
                    connType VARCHAR(50),
                    voltage DOUBLE DEFAULT 0,
                    current DOUBLE DEFAULT 0,
                    resistance DOUBLE DEFAULT 0,
                    project_id VARCHAR(255) DEFAULT 'EOS1550',
                    PRIMARY KEY (id),
                    UNIQUE KEY uk_connNo (connNo),
                    INDEX idx_source (source),
                    INDEX idx_target (target),
                    INDEX idx_project (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 创建device_types表
            logger.info("创建device_types表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_types (
                    id INT NOT NULL AUTO_INCREMENT,
                    type_name VARCHAR(50) NOT NULL,
                    point_count INT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY type_name (type_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备类型定义表'
            """)

            # 创建device_type_points表
            logger.info("创建device_type_points表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_type_points (
                    id INT NOT NULL AUTO_INCREMENT,
                    device_type_id INT NOT NULL,
                    point_index VARCHAR(60) NOT NULL COMMENT '点位索引，支持数字和特殊字符',
                    point_type ENUM('DI','DO','AI','AO') NOT NULL,
                    sim_type ENUM('A','B','C','D','F','U','W','DD','PDI','PDO','PAI','PAO','HI','HO') NOT NULL COMMENT '模拟类型',
                    point_name VARCHAR(50) NOT NULL,
                    mode ENUM('read','write') NOT NULL DEFAULT 'read',
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    UNIQUE KEY unique_point (device_type_id, point_index),
                    CONSTRAINT device_type_points_ibfk_1 FOREIGN KEY (device_type_id) REFERENCES device_types (id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备点位配置表'
            """)

            # 创建simpoint表
            logger.info("创建simpoint表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simpoint (
                    id INT NOT NULL AUTO_INCREMENT,
                    ftid VARCHAR(50) NOT NULL,
                    target_ftid VARCHAR(50),
                    project_name VARCHAR(50) NOT NULL,
                    moduler VARCHAR(50) NOT NULL,
                    device_name VARCHAR(50) NOT NULL,
                    point_type VARCHAR(10) NOT NULL,
                    point_index VARCHAR(60) NOT NULL,
                    sim_type VARCHAR(10) NOT NULL,
                    mode VARCHAR(10) NOT NULL,
                    description VARCHAR(255),
                    hartingbox VARCHAR(50),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 初始化device_types表的基础数据
            logger.info("初始化device_types基础数据...")
            cursor.execute("""
                INSERT IGNORE INTO device_types (type_name, point_count, description)
                VALUES
                ('EDB', 16, 'DI数字输入模块'),
                ('EBD', 16, 'DO数字输出模块')
            """)

            # 初始化device_type_points表的基础数据
            logger.info("初始化device_type_points基础数据...")
            
            # 为EDB模块添加点位
            cursor.execute("SELECT id FROM device_types WHERE type_name = 'EDB'")
            edb_id = cursor.fetchone()['id']
            for i in range(1, 17):
                cursor.execute("""
                    INSERT IGNORE INTO device_type_points
                    (device_type_id, point_index, point_type, sim_type, point_name, mode)
                    VALUES (%s, %s, 'DI', 'DD', %s, 'read')
                """, (edb_id, str(i), f'DI_{i}'))

            # 为EBD模块添加点位
            cursor.execute("SELECT id FROM device_types WHERE type_name = 'EBD'")
            ebd_id = cursor.fetchone()['id']
            for i in range(1, 17):
                cursor.execute("""
                    INSERT IGNORE INTO device_type_points
                    (device_type_id, point_index, point_type, sim_type, point_name, mode)
                    VALUES (%s, %s, 'DO', 'DD', %s, 'write')
                """, (ebd_id, str(i), f'DO_{i}'))

            conn.commit()
            logger.info("表创建完成")

            # Check if v_csv_raw has data
            cursor.execute("SELECT COUNT(*) as count FROM v_csv_raw")
            raw_count = cursor.fetchone()['count']
            logger.info(f"v_csv_raw表中有 {raw_count} 条记录")
            
            # Check specifically for records with K1.% locations
            cursor.execute("SELECT COUNT(*) as count FROM v_csv_raw WHERE s_location LIKE 'K1.%' OR t_location LIKE 'K1.%'")
            k1_count = cursor.fetchone()['count']
            logger.info(f"v_csv_raw表中有 {k1_count} 条K1.%位置的记录")
            
            # 4. 插入设备数据
            logger.info("导入设备数据...")
            sql = """
                INSERT IGNORE INTO v_csv_device 
                (fdid, Function, Location, Device, Type, isPLC, project_id)
                SELECT DISTINCT
                    dev.fdid,
                    dev.Function,
                    dev.Location,
                    dev.Device,
                    dev.Type,
                    dev.isPLC,
                    '{0}' as project_id
                FROM (
                    SELECT DISTINCT
                        SUBSTRING_INDEX(s_ftid, ':', 1) as fdid,
                        s_function as Function,
                        s_location as Location,
                        s_device as Device,
                        CASE
                            WHEN s_device LIKE 'A%' THEN 'PLC'
                            ELSE 'DEVICE'
                        END as Type,
                        CASE
                            WHEN s_device LIKE 'A%' THEN 1
                            ELSE 0
                        END as isPLC
                    FROM v_csv_raw
                    WHERE s_ftid IS NOT NULL 
                    AND s_device IS NOT NULL 
                    AND s_location LIKE 'K1.%'
                    UNION
                    SELECT DISTINCT
                        SUBSTRING_INDEX(t_ftid, ':', 1) as fdid,
                        t_function as Function,
                        t_location as Location,
                        t_device as Device,
                        CASE
                            WHEN t_device LIKE 'A%' THEN 'PLC'
                            ELSE 'DEVICE'
                        END as Type,
                        CASE
                            WHEN t_device LIKE 'A%' THEN 1
                            ELSE 0
                        END as isPLC
                    FROM v_csv_raw
                    WHERE t_ftid IS NOT NULL 
                    AND t_device IS NOT NULL 
                    AND t_location LIKE 'K1.%'
                ) as dev
            """.format(project_id)
            cursor.execute(sql)
            device_count = cursor.rowcount
            logger.info(f"已导入 {device_count} 条设备数据")

            # 5. 插入端子数据
            logger.info("导入源端数据...")
            sql = """
                INSERT IGNORE INTO v_csv_devpoint
                (raw, ftid, belongtoDevice, Function, Location, Device, Terminal, Type, isInPanel, project_id)
                SELECT
                    MIN(s_raw) as raw,
                    s_ftid as ftid,
                    SUBSTRING_INDEX(s_ftid, ':', 1) as belongtoDevice,
                    MAX(s_function) as Function,
                    s_location as Location,
                    s_device as Device,
                    s_terminal as Terminal,
                    CASE
                        WHEN s_terminal LIKE 'A%' THEN 'A'
                        WHEN s_terminal LIKE 'D%' THEN 'D'
                        WHEN s_terminal LIKE 'L%' THEN 'L'
                        WHEN s_terminal LIKE 'K%' THEN 'K'
                        WHEN s_terminal LIKE 'T%' THEN 'T'
                        ELSE 'OTHER'
                    END as Type,
                    1 as isInPanel,
                    '{0}' as project_id
                FROM v_csv_raw
                WHERE s_ftid IS NOT NULL
                AND s_terminal IS NOT NULL
                AND s_location IS NOT NULL
                AND s_device IS NOT NULL
                AND s_location LIKE 'K1.%'
                GROUP BY s_ftid, s_location, s_device, s_terminal
            """.format(project_id)
            cursor.execute(sql)
            source_count = cursor.rowcount
            logger.info(f"已导入 {source_count} 条源端数据")

            logger.info("导入目标端数据...")
            sql = """
                INSERT IGNORE INTO v_csv_devpoint
                (raw, ftid, belongtoDevice, Function, Location, Device, Terminal, Type, isInPanel, project_id)
                SELECT
                    MIN(t_raw) as raw,
                    t_ftid as ftid,
                    SUBSTRING_INDEX(t_ftid, ':', 1) as belongtoDevice,
                    MAX(t_function) as Function,
                    t_location as Location,
                    t_device as Device,
                    t_terminal as Terminal,
                    CASE
                        WHEN t_terminal LIKE 'A%' THEN 'A'
                        WHEN t_terminal LIKE 'D%' THEN 'D'
                        WHEN t_terminal LIKE 'L%' THEN 'L'
                        WHEN t_terminal LIKE 'K%' THEN 'K'
                        WHEN t_terminal LIKE 'T%' THEN 'T'
                        ELSE 'OTHER'
                    END as Type,
                    1 as isInPanel,
                    '{0}' as project_id
                FROM v_csv_raw
                WHERE t_ftid IS NOT NULL
                AND t_terminal IS NOT NULL
                AND t_location IS NOT NULL
                AND t_device IS NOT NULL
                AND t_location LIKE 'K1.%'
                GROUP BY t_ftid, t_location, t_device, t_terminal
            """.format(project_id)
            cursor.execute(sql)
            target_count = cursor.rowcount
            logger.info(f"已导入 {target_count} 条目标端数据")

            # 6. 插入连接数据
            logger.info("导入连接数据...")
            sql = """
                INSERT IGNORE INTO v_csv_conn
                (connNo, source, target, color, isInPanel, connType, project_id)
                SELECT DISTINCT
                    cnumber as connNo,
                    s_ftid as source,
                    t_ftid as target,
                    color,
                    1 as isInPanel,
                    'external' as connType,
                    '{0}' as project_id
                FROM v_csv_raw r
                WHERE s_ftid IS NOT NULL
                AND t_ftid IS NOT NULL
                AND s_terminal IS NOT NULL
                AND t_terminal IS NOT NULL
                AND s_location LIKE 'K1.%'
                AND t_location LIKE 'K1.%'
            """.format(project_id)
            cursor.execute(sql)
            conn_count = cursor.rowcount
            logger.info(f"已导入 {conn_count} 条连接数据")

            conn.commit()

            # 7. 验证数据
            logger.info("\n=== 数据验证 ===")

            # 检查设备数据
            cursor.execute("SELECT COUNT(*) as count FROM v_csv_device WHERE project_id = %s", (project_id,))
            logger.info(f"设备总数: {cursor.fetchone()['count']}")

            # 检查端子数据
            cursor.execute("SELECT COUNT(*) as count FROM v_csv_devpoint WHERE project_id = %s", (project_id,))
            logger.info(f"端子总数: {cursor.fetchone()['count']}")

            # 检查连接数据
            cursor.execute("SELECT COUNT(*) as count FROM v_csv_conn WHERE project_id = %s", (project_id,))
            logger.info(f"连接总数: {cursor.fetchone()['count']}")

            # 检查端子类型分布
            cursor.execute("""
                SELECT Type, COUNT(*) as count
                FROM v_csv_devpoint
                WHERE project_id = %s
                GROUP BY Type
                ORDER BY count DESC
            """, (project_id,))
            logger.info("\n端子类型分布:")
            for row in cursor.fetchall():
                logger.info(f"  {row['Type']}: {row['count']}")

            # 验证新建表数据
            logger.info("\n=== 新建表验证 ===")
            
            # 验证device_types表
            cursor.execute("SELECT COUNT(*) as count FROM device_types")
            device_types_count = cursor.fetchone()['count']
            logger.info(f"设备类型总数: {device_types_count}")
            
            # 验证device_type_points表
            cursor.execute("""
                SELECT dt.type_name, COUNT(dtp.id) as point_count
                FROM device_types dt
                LEFT JOIN device_type_points dtp ON dt.id = dtp.device_type_id
                GROUP BY dt.type_name
                ORDER BY dt.type_name
            """)
            logger.info("\n设备类型点位配置:")
            for row in cursor.fetchall():
                logger.info(f"  {row['type_name']}: 配置了{row['point_count']}个点位")

            # 验证simpoint表结构
            logger.info("\nsimpoint表验证:")
            cursor.execute("SELECT COUNT(*) as count FROM simpoint")
            simpoint_count = cursor.fetchone()['count']
            logger.info(f"  总记录数: {simpoint_count}")
            
            cursor.execute("""
                SELECT COALESCE(moduler, '未分配') as moduler,
                       COUNT(*) as count,
                       COUNT(CASE WHEN target_ftid IS NOT NULL THEN 1 END) as used_count,
                       COUNT(CASE WHEN hartingbox IS NOT NULL THEN 1 END) as harting_count
                FROM simpoint
                GROUP BY moduler
                ORDER BY moduler
            """)
            logger.info("模块使用情况:")
            for row in cursor.fetchall():
                logger.info(f"  {row['moduler']}: "
                          f"总点位={row['count']}, "
                          f"已使用={row['used_count']}, "
                          f"已分配hartingbox={row['harting_count']}")

        logger.info("\n所有操作完成")
        return 0

    except Exception as e:
        logger.error(f"错误: {str(e)}")
        return 1

    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("数据库连接已关闭")

if __name__ == "__main__":
    sys.exit(create_and_fill_tables())