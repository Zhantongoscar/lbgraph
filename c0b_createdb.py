#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import logging
import pymysql
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.config = self._load_config()
        self._connect_database()

    def _load_config(self) -> Dict:
        """从config.json加载数据库配置"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config['mysql']
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            raise

    def _connect_database(self):
        """连接到MySQL数据库"""
        try:
            self.conn = pymysql.connect(
                host=self.config['host'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"已连接到数据库: {self.config['host']}")
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise

    def _create_tables(self):
        """创建所需的数据表"""
        try:
            with self.conn.cursor() as cursor:
                # 创建设备表
                cursor.execute("DROP TABLE IF EXISTS v_csv_device")
                cursor.execute("""
                    CREATE TABLE v_csv_device (
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
                        UNIQUE KEY FDID (FDID)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                logger.info("设备表创建成功")

                # 创建端子表
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
                        UNIQUE KEY FTID (FTID)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                logger.info("端子表创建成功")

                # 创建连接表
                cursor.execute("DROP TABLE IF EXISTS v_csv_conn")
                cursor.execute("""
                    CREATE TABLE v_csv_conn (
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
                        UNIQUE KEY conn_unique (source, target),
                        INDEX idx_source (source),
                        INDEX idx_target (target),
                        INDEX idx_conn_type (connType),
                        INDEX idx_in_panel (isInPanel)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                logger.info("连接表创建成功")

                self.conn.commit()
        except Exception as e:
            logger.error(f"创建表失败: {str(e)}")
            self.conn.rollback()
            raise

    def _extract_device_data(self):
        """从v_csv_raw提取并插入设备数据"""
        try:
            with self.conn.cursor() as cursor:
                # 清除现有数据
                cursor.execute("TRUNCATE TABLE v_csv_device")
                
                # 提取并插入设备数据
                cursor.execute("""
                    INSERT INTO v_csv_device (FDID, Function, Location, Device, Type, isPLC)
                    SELECT DISTINCT
                        dev.FDID,
                        dev.Function,
                        dev.Location,
                        dev.Device,
                        dev.Type,
                        dev.isPLC
                    FROM (
                        SELECT DISTINCT
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
                        UNION
                        SELECT DISTINCT
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
                """)
                
                self.conn.commit()
                logger.info(f"设备数据提取完成，插入了 {cursor.rowcount} 条记录")
        except Exception as e:
            logger.error(f"设备数据处理失败: {str(e)}")
            self.conn.rollback()
            raise

    def _extract_devpoint_data(self):
        """从v_csv_raw提取并插入端子数据"""
        try:
            with self.conn.cursor() as cursor:
                # 清除现有数据
                cursor.execute("TRUNCATE TABLE v_csv_devpoint")
                
                # 创建临时表存储所有端子数据
                cursor.execute("DROP TABLE IF EXISTS temp_points")
                cursor.execute("""
                    CREATE TEMPORARY TABLE temp_points (
                        raw VARCHAR(255) NOT NULL,
                        FTID VARCHAR(255) NOT NULL,
                        belongtoDevice VARCHAR(255),
                        Function VARCHAR(255),
                        Location VARCHAR(255),
                        Device VARCHAR(255),
                        Type VARCHAR(50),
                        description VARCHAR(255)
                    ) ENGINE=InnoDB
                """)
                
                # 插入源端数据
                cursor.execute("""
                    INSERT INTO temp_points 
                    SELECT DISTINCT s_raw, s_ftid, 
                        SUBSTRING_INDEX(s_ftid, ':', 1) as belongtoDevice,
                        s_function, s_location, s_device,
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
                    WHERE s_ftid IS NOT NULL AND s_terminal IS NOT NULL
                """)

                # 插入目标端数据（避免重复）
                cursor.execute("""
                    INSERT IGNORE INTO temp_points 
                    SELECT DISTINCT t_raw, t_ftid,
                        SUBSTRING_INDEX(t_ftid, ':', 1) as belongtoDevice,
                        t_function, t_location, t_device,
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
                    WHERE t_ftid IS NOT NULL AND t_terminal IS NOT NULL
                """)

                # 从临时表导入到最终表
                cursor.execute("""
                    INSERT INTO v_csv_devpoint 
                    (raw, FTID, belongtoDevice, Function, Location, Device, Type, description)
                    SELECT DISTINCT * FROM temp_points
                """)
                
                self.conn.commit()
                
                # 获取插入的记录数
                cursor.execute("SELECT COUNT(*) as count FROM v_csv_devpoint")
                count = cursor.fetchone()['count']
                logger.info(f"端子数据提取完成，插入了 {count} 条记录")

                # 清理临时表
                cursor.execute("DROP TABLE IF EXISTS temp_points")
                
        except Exception as e:
            logger.error(f"端子数据处理失败: {str(e)}")
            self.conn.rollback()
            raise

    def _extract_conn_data(self):
        """从v_csv_raw提取并插入连接数据"""
        try:
            with self.conn.cursor() as cursor:
                # 清除现有数据
                cursor.execute("TRUNCATE TABLE v_csv_conn")
                
                # 提取并插入连接数据
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
                
                self.conn.commit()
                logger.info(f"连接数据提取完成，插入了 {cursor.rowcount} 条记录")
        except Exception as e:
            logger.error(f"连接数据处理失败: {str(e)}")
            self.conn.rollback()
            raise

    def _verify_data(self):
        """验证数据的完整性和关联关系"""
        try:
            with self.conn.cursor() as cursor:
                # 检查设备数量
                cursor.execute("SELECT COUNT(*) as count FROM v_csv_device")
                device_count = cursor.fetchone()['count']
                logger.info(f"设备总数: {device_count}")

                # 检查端子数量
                cursor.execute("SELECT COUNT(*) as count FROM v_csv_devpoint")
                point_count = cursor.fetchone()['count']
                logger.info(f"端子总数: {point_count}")

                # 检查连接数量
                cursor.execute("SELECT COUNT(*) as count FROM v_csv_conn")
                conn_count = cursor.fetchone()['count']
                logger.info(f"连接总数: {conn_count}")

                # 验证端子和设备的关联
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM v_csv_devpoint p
                    LEFT JOIN v_csv_device d ON p.belongtoDevice = d.FDID
                    WHERE d.FDID IS NULL
                """)
                orphan_points = cursor.fetchone()['count']
                if orphan_points > 0:
                    logger.warning(f"发现 {orphan_points} 个孤立端子（未关联到设备）")

                # 验证连接的端子存在性
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM v_csv_conn c
                    LEFT JOIN v_csv_devpoint p1 ON c.source = p1.FTID
                    LEFT JOIN v_csv_devpoint p2 ON c.target = p2.FTID
                    WHERE p1.FTID IS NULL OR p2.FTID IS NULL
                """)
                invalid_conns = cursor.fetchone()['count']
                if invalid_conns > 0:
                    logger.warning(f"发现 {invalid_conns} 个无效连接（端子不存在）")

        except Exception as e:
            logger.error(f"数据验证失败: {str(e)}")
            raise

    def process_data(self):
        """处理所有数据转换步骤"""
        try:
            logger.info("开始数据处理...")
            self._create_tables()
            self._extract_device_data()
            self._extract_devpoint_data()
            self._extract_conn_data()
            self._verify_data()
            logger.info("数据处理完成")
        except Exception as e:
            logger.error(f"数据处理失败: {str(e)}")
            raise
        finally:
            if self.conn:
                self.conn.close()
                logger.info("数据库连接已关闭")

def main():
    try:
        manager = DatabaseManager()
        manager.process_data()
        return 0
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())