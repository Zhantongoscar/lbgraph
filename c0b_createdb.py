#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
from config import MYSQL_CONFIG
import logging
from datetime import datetime

# 配置日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
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

        # 使用config.py中的数据库配置
        config = MYSQL_CONFIG

        # 连接到数据库
        conn = pymysql.connect(
            **config,
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
                    drawingPage INT NULL,
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
                    connMode VARCHAR(50) DEFAULT 'direct',
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
            
            conn.commit()
            logger.info("表创建完成")

            # 删除旧数据
            cursor.execute(f"DELETE FROM v_csv_device WHERE project_id = '{project_id}'")
            cursor.execute(f"DELETE FROM v_csv_devpoint WHERE project_id = '{project_id}'")
            cursor.execute(f"DELETE FROM v_csv_conn WHERE project_id = '{project_id}'")
            conn.commit()

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
                INSERT INTO v_csv_device 
                (fdid, Function, Location, Device, isInPanel, project_id)
                SELECT DISTINCT
                    dev.fdid,
                    dev.Function,
                    dev.Location,
                    dev.Device,
                    1 as isInPanel,
                    '{0}' as project_id
                FROM (
                    SELECT DISTINCT
                        SUBSTRING_INDEX(s_ftid, ':', 1) as fdid,
                        s_function as Function,
                        s_location as Location,
                        s_device as Device
                    FROM v_csv_raw
                    WHERE s_ftid IS NOT NULL 
                    AND s_device IS NOT NULL 
                    AND s_location LIKE 'K1.%'
                    UNION
                    SELECT DISTINCT
                        SUBSTRING_INDEX(t_ftid, ':', 1) as fdid,
                        t_function as Function,
                        t_location as Location,
                        t_device as Device
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
                INSERT INTO v_csv_devpoint
                (raw, ftid, belongtoDevice, Function, Location, Device, Terminal, isInPanel, project_id)
                SELECT
                    MIN(s_raw) as raw,
                    s_ftid as ftid,
                    SUBSTRING_INDEX(s_ftid, ':', 1) as belongtoDevice,
                    MAX(s_function) as Function,
                    s_location as Location,
                    s_device as Device,
                    s_terminal as Terminal,
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
                INSERT INTO v_csv_devpoint
                (raw, ftid, belongtoDevice, Function, Location, Device, Terminal, isInPanel, project_id)
                SELECT
                    MIN(t_raw) as raw,
                    t_ftid as ftid,
                    SUBSTRING_INDEX(t_ftid, ':', 1) as belongtoDevice,
                    MAX(t_function) as Function,
                    t_location as Location,
                    t_device as Device,
                    t_terminal as Terminal,
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
                INSERT INTO v_csv_conn
                (connNo, source, target, color, isInPanel, connType, connMode, project_id)
                SELECT DISTINCT
                    cnumber as connNo,
                    s_ftid as source,
                    t_ftid as target,
                    color,
                    1 as isInPanel,
                    'ex' as connType,
                    'direct' as connMode,
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