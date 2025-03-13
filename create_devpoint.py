#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import logging
import pymysql

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)['mysql']

        # 连接数据库
        conn = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info(f"已连接到数据库: {config['host']}")

        try:
            with conn.cursor() as cursor:
                # 创建端子表
                logger.info("创建端子表...")
                cursor.execute("DROP TABLE IF EXISTS v_csv_devpoint")
                cursor.execute("""
                    CREATE TABLE v_csv_devpoint (
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
                        INDEX idx_location_device (Location, Device),
                        INDEX idx_device (Device),
                        INDEX idx_type (Type)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                conn.commit()
                logger.info("端子表创建成功")

                # 插入源端数据
                logger.info("插入源端数据...")
                cursor.execute("""
                    INSERT INTO v_csv_devpoint 
                    (raw, FTID, belongtoDevice, Function, Location, Device, Type, description)
                    SELECT DISTINCT 
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
                logger.info(f"插入了 {source_count} 条源端数据")

                # 插入目标端数据
                logger.info("插入目标端数据...")
                cursor.execute("""
                    INSERT IGNORE INTO v_csv_devpoint 
                    (raw, FTID, belongtoDevice, Function, Location, Device, Type, description)
                    SELECT DISTINCT
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
                logger.info(f"插入了 {target_count} 条目标端数据")

                conn.commit()

                # 验证数据
                cursor.execute("SELECT COUNT(*) as count FROM v_csv_devpoint")
                total_count = cursor.fetchone()['count']
                logger.info(f"端子表总记录数: {total_count}")

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

                # 显示示例数据
                logger.info("\n数据示例:")
                cursor.execute("SELECT * FROM v_csv_devpoint LIMIT 5")
                for row in cursor.fetchall():
                    logger.info(f"  FTID: {row['FTID']}")
                    logger.info(f"  Location: {row['Location']}")
                    logger.info(f"  Device: {row['Device']}")
                    logger.info(f"  Type: {row['Type']}")
                    logger.info(f"  Description: {row['description']}")
                    logger.info("---")

        finally:
            conn.close()
            logger.info("数据库连接已关闭")

        return 0

    except Exception as e:
        logger.error(f"错误: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())