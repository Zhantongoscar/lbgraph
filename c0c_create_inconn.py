#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
import json
import logging
from datetime import datetime
import re
import os
from typing import Dict, List, Set
from c0c_device_rules import create_ks_rule

# 配置日志输出到文件和控制台
log_file = f'create_inconn_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)['mysql']
    return pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def strip_device_prefix(terminal):
    """从端子号中去除设备前缀，只保留实际的端子号部分"""
    if ':' in terminal:
        return terminal.split(':')[-1]
    return terminal

def get_device_type(device_name):
    """获取设备类型（第一个字母）"""
    if device_name and len(device_name) > 0:
        return device_name[0].upper()
    return None

def get_unused_points(all_points, used_point_ids):
    """获取未使用的端子点"""
    return [point for point in all_points if point['ftid'] not in used_point_ids]

def create_innerconn_table(cursor):
    """创建v_csv_innerconn表"""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS v_csv_innerconn (
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
        logger.info("v_csv_innerconn表创建成功")
    except Exception as e:
        logger.error(f"创建v_csv_innerconn表失败: {str(e)}")
        raise

def process_device(cursor, device: Dict, device_rules: Dict, global_conn_id: int) -> int:
    """处理单个设备"""
    belongtoDevice = device['belongtoDevice']
    device_name = device['Device']
    device_type = get_device_type(device_name)
    
    # 获取当前设备的所有端子点
    cursor.execute("""
        SELECT DISTINCT ftid, Terminal
        FROM v_csv_devpoint
        WHERE belongtoDevice = %s
        ORDER BY Terminal
    """, (belongtoDevice,))
    points = cursor.fetchall()

    # 设备规则匹配
    rule = None
    if device_type == 'K':
        rule = create_ks_rule()
        terminal_set = {strip_device_prefix(p['Terminal']) for p in points}
        if rule.match(device_name, terminal_set):
            connections = rule.get_connections(points)
            logger.info(f"为设备 {device_name} 应用KS规则")
            
            # 创建连接
            for conn in connections:
                global_conn_id += 1
                conn_id = f"in{global_conn_id}"
                props = conn['properties']
                
                cursor.execute("""
                    INSERT INTO v_csv_innerconn
                    (connNo, source, target, color, isCable, isInPanel, connType, voltage, current, resistance)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    conn_id,
                    conn['source'],
                    conn['target'],
                    None,
                    1 if props.get('isCable', False) else 0,
                    1 if props.get('isInPanel', True) else 0,
                    props.get('connType', 'devInConn'),
                    props.get('voltage', 0.0),
                    props.get('current', 0.0),
                    props.get('resistance', 0.0)
                ))
                
                logger.info(f"创建连接: {strip_device_prefix(conn['sourceTerminal'])} -> "
                           f"{strip_device_prefix(conn['targetTerminal'])} "
                           f"({props.get('connType', 'unknown')})")

    return global_conn_id

def create_internal_connections():
    """创建设备内部连接的主函数"""
    conn = None
    try:
        # 连接数据库
        conn = get_db_connection()
        logger.info("已连接到数据库")

        # 创建v_csv_innerconn表
        with conn.cursor() as cursor:
            create_innerconn_table(cursor)
            # 清空已有数据
            cursor.execute("TRUNCATE TABLE v_csv_innerconn")
            logger.info("清空v_csv_innerconn表中的现有数据")
            
            # 获取所有设备信息
            cursor.execute("""
                SELECT DISTINCT belongtoDevice, Location, Device
                FROM v_csv_devpoint
                WHERE Location LIKE 'K1.%'
                ORDER BY Location, Device
            """)
            devices = cursor.fetchall()
            logger.info(f"找到 {len(devices)} 个设备")

            # 过滤只处理特定类型的设备
            allowed_device_types = ["K", "Q", "S"]
            filtered_devices = [
                device for device in devices
                if device['Device'] and get_device_type(device['Device']) in allowed_device_types
            ]
            
            logger.info(f"筛选出 {len(filtered_devices)} 个符合条件的设备")
            
            # 处理每个设备
            global_conn_id = 0
            for device in filtered_devices:
                try:
                    global_conn_id = process_device(cursor, device, None, global_conn_id)
                    conn.commit()
                except Exception as e:
                    logger.error(f"处理设备 {device['Device']} 时出错: {str(e)}")
                    continue

            logger.info(f"总共创建了 {global_conn_id} 个内部连接")
        return 0

    except Exception as e:
        logger.error(f"错误: {str(e)}")
        if conn:
            conn.rollback()
        return 1

    finally:
        if conn:
            conn.close()
            logger.info("数据库连接已关闭")

if __name__ == "__main__":
    sys.exit(create_internal_connections())