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

def create_and_fill_tables():
    try:
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
                    FDID VARCHAR(255) NOT NULL,
                    Function VARCHAR(255),
                    Location VARCHAR(255),
                    Device VARCHAR(255),
                    isInPanel TINYINT(1) DEFAULT 1,
                    Type VARCHAR(50),
                    isSim TINYINT(1) DEFAULT 0,
                    isPLC TINYINT(1) DEFAULT 0,
                    isTerminal TINYINT(1) DEFAULT 0,
                    PRIMARY KEY (id),
                    INDEX idx_fdid (FDID),
                    INDEX idx_location (Location),
                    INDEX idx_device (Device)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # 2. 创建端子表
            logger.info("创建v_csv_devpoint表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS v_csv_devpoint (
                    id INT NOT NULL AUTO_INCREMENT,
                    raw VARCHAR(255) NOT NULL,
                    FTID VARCHAR(255) NOT NULL,
                    belongtoDevice VARCHAR(255),
                    Function VARCHAR(255),
                    Location VARCHAR(255),
                    Device VARCHAR(255),
                    Type VARCHAR(50),
                    description VARCHAR(255),
                    voltage DOUBLE DEFAULT 0,
                    current DOUBLE DEFAULT 0,
                    resistance DOUBLE DEFAULT 0,
                    isSocket TINYINT(1) DEFAULT 0,
                    isSetPoint TINYINT(1) DEFAULT 0,
                    isSensePoint TINYINT(1) DEFAULT 0,
                    PRIMARY KEY (id),
                    INDEX idx_ftid (FTID),
                    INDEX idx_location_device (Location, Device)
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
                    PRIMARY KEY (id),
                    INDEX idx_source (source),
                    INDEX idx_target (target)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            conn.commit()
            logger.info("表创建完成")

            # 4. 插入设备数据
            logger.info("导入设备数据...")
            cursor.execute("""
                INSERT INTO v_csv_device (FDID, Function, Location, Device, Type, isPLC)
                SELECT DISTINCT
                    MIN(dev.FDID) as FDID,
                    MAX(dev.Function) as Function,
                    dev.Location,
                    dev.Device,
                    MAX(dev.Type) as Type,
                    MAX(dev.isPLC) as isPLC
                FROM (
                    SELECT 
                        SUBSTRING_INDEX(s_ftid, ':', 1) as FDID,
                        s_function as Function,
                        s_location as Location,
                        s_device as Device,
                        CASE 
                            WHEN s_device LIKE 'A2%' THEN 'PLC'
                            ELSE 'DEVICE'
                        END as Type,
                        CASE 
                            WHEN s_device LIKE 'A2%' THEN 1
                            ELSE 0
                        END as isPLC
                    FROM v_csv_raw
                    WHERE s_ftid IS NOT NULL AND s_device IS NOT NULL
                    UNION ALL
                    SELECT 
                        SUBSTRING_INDEX(t_ftid, ':', 1) as FDID,
                        t_function as Function,
                        t_location as Location,
                        t_device as Device,
                        CASE 
                            WHEN t_device LIKE 'A2%' THEN 'PLC'
                            ELSE 'DEVICE'
                        END as Type,
                        CASE 
                            WHEN t_device LIKE 'A2%' THEN 1
                            ELSE 0
                        END as isPLC
                    FROM v_csv_raw
                    WHERE t_ftid IS NOT NULL AND t_device IS NOT NULL
                ) as dev
                GROUP BY dev.Location, dev.Device
            """)
            device_count = cursor.rowcount
            logger.info(f"已导入 {device_count} 条设备数据")

            # 5. 插入端子数据
            logger.info("导入源端数据...")
            cursor.execute("""
                INSERT INTO v_csv_devpoint 
                (raw, FTID, belongtoDevice, Function, Location, Device, Type, description)
                SELECT
                    MIN(s_raw) as raw,
                    s_ftid as FTID,
                    SUBSTRING_INDEX(s_ftid, ':', 1) as belongtoDevice,
                    MAX(s_function) as Function,
                    s_location as Location,
                    s_device as Device,
                    CASE 
                        WHEN s_terminal LIKE 'A%' THEN 'A'
                        WHEN s_terminal LIKE 'D%' THEN 'D'
                        WHEN s_terminal LIKE 'L%' THEN 'L'
                        WHEN s_terminal LIKE 'K%' THEN 'K'
                        WHEN s_terminal LIKE 'T%' THEN 'T'
                        ELSE 'OTHER'
                    END as Type,
                    s_terminal as description
                FROM v_csv_raw
                WHERE s_ftid IS NOT NULL 
                AND s_terminal IS NOT NULL
                AND s_location IS NOT NULL
                AND s_device IS NOT NULL
                GROUP BY s_ftid, s_location, s_device, s_terminal
            """)
            source_count = cursor.rowcount
            logger.info(f"已导入 {source_count} 条源端数据")

            logger.info("导入目标端数据...")
            cursor.execute("""
                INSERT IGNORE INTO v_csv_devpoint 
                (raw, FTID, belongtoDevice, Function, Location, Device, Type, description)
                SELECT
                    MIN(t_raw) as raw,
                    t_ftid as FTID,
                    SUBSTRING_INDEX(t_ftid, ':', 1) as belongtoDevice,
                    MAX(t_function) as Function,
                    t_location as Location,
                    t_device as Device,
                    CASE 
                        WHEN t_terminal LIKE 'A%' THEN 'A'
                        WHEN t_terminal LIKE 'D%' THEN 'D'
                        WHEN t_terminal LIKE 'L%' THEN 'L'
                        WHEN t_terminal LIKE 'K%' THEN 'K'
                        WHEN t_terminal LIKE 'T%' THEN 'T'
                        ELSE 'OTHER'
                    END as Type,
                    t_terminal as description
                FROM v_csv_raw
                WHERE t_ftid IS NOT NULL 
                AND t_terminal IS NOT NULL
                AND t_location IS NOT NULL
                AND t_device IS NOT NULL
                GROUP BY t_ftid, t_location, t_device, t_terminal
            """)
            target_count = cursor.rowcount
            logger.info(f"已导入 {target_count} 条目标端数据")

            # 6. 插入连接数据
            logger.info("导入连接数据...")
            cursor.execute("""
                INSERT INTO v_csv_conn 
                (connNo, source, target, isInPanel, connType)
                SELECT DISTINCT
                    cnumber as connNo,
                    s_ftid as source,
                    t_ftid as target,
                    1 as isInPanel,
                    CASE
                        WHEN s_location = t_location THEN 'internal'
                        ELSE 'external'
                    END as connType
                FROM v_csv_raw
                WHERE s_ftid IS NOT NULL 
                AND t_ftid IS NOT NULL
                AND s_terminal IS NOT NULL
                AND t_terminal IS NOT NULL
            """)
            conn_count = cursor.rowcount
            logger.info(f"已导入 {conn_count} 条连接数据")

            conn.commit()

            # 7. 验证数据
            logger.info("\n=== 数据验证 ===")

            # 检查设备数据
            cursor.execute("SELECT COUNT(*) as count FROM v_csv_device")
            logger.info(f"设备总数: {cursor.fetchone()['count']}")

            # 检查端子数据
            cursor.execute("SELECT COUNT(*) as count FROM v_csv_devpoint")
            logger.info(f"端子总数: {cursor.fetchone()['count']}")

            # 检查连接数据
            cursor.execute("SELECT COUNT(*) as count FROM v_csv_conn")
            logger.info(f"连接总数: {cursor.fetchone()['count']}")

            # 检查端子类型分布
            cursor.execute("""
                SELECT Type, COUNT(*) as count
                FROM v_csv_devpoint
                GROUP BY Type
                ORDER BY count DESC
            """)
            logger.info("\n端子类型分布:")
            for row in cursor.fetchall():
                logger.info(f"  {row['Type']}: {row['count']}")

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