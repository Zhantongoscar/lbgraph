#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
import json
import logging
from datetime import datetime
import re
import os
from typing import Dict, List, Set, Tuple
from c0c_device_rules import create_device_rule

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

def get_unused_points(points: List[Dict], used_point_ids: Set[str]) -> List[Dict]:
    """获取未使用的端子点"""
    return [point for point in points if point['ftid'] not in used_point_ids]

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

def print_device_header(index: int, total: int, device: Dict):
    """打印设备处理头部信息"""
    print("\n" + "="*60)
    print(f"正在处理设备 {index}/{total}")
    print("="*60)
    print(f"设备名称: {device['Device']}")
    print(f"位置: {device['Location']}")
    print(f"设备ID: {device['belongtoDevice']}")

def process_device_points(cursor, device: Dict, points: List[Dict]) -> None:
    """处理并显示设备端子信息"""
    print("\n可用端子点:")
    terminal_set = {strip_device_prefix(p['Terminal']) for p in points}
    print(f"端子列表: {sorted(list(terminal_set))}")
    
    device_type = get_device_type(device['Device'])
    print(f"\n设备类型: {device_type}")
    
    # 获取设备规则
    rule = create_device_rule(device['Device'])
    
    if rule:
        # 如果是K类设备，检测特征
        if device_type == 'K':
            device_feature = rule.detect_features(device['Device'], terminal_set)
            print(f"设备特征: {device_feature}")
            
            # 检查安全继电器特征端子对
            has_s11_s12 = {'S11', 'S12'}.issubset(terminal_set)
            has_s21_s22 = {'S21', 'S22'}.issubset(terminal_set)
            has_a11_a12 = {'A11', 'A12'}.issubset(terminal_set)
            
            if device_feature == "KS安全继电器":
                print("识别依据:")
                print("  * 设备名称以K开头")
                if has_a11_a12:
                    print("  * 包含主线圈端子对: A11-A12")
                if has_s11_s12:
                    print("  * 包含安全端子对: S11-S12")
                if has_s21_s22:
                    print("  * 包含安全端子对: S21-S22")
        else:
            print("设备特征: 标准设备")

def process_device(cursor, device: Dict, index: int, total: int, global_conn_id: int) -> Tuple[int, Set[str]]:
    """处理单个设备"""
    print_device_header(index, total, device)
    
    # 获取设备端子点
    belongtoDevice = device['belongtoDevice']
    cursor.execute("""
        SELECT DISTINCT ftid, Terminal
        FROM v_csv_devpoint
        WHERE belongtoDevice = %s
        ORDER BY Terminal
    """, (belongtoDevice,))
    points = cursor.fetchall()
    
    # 显示端子信息
    process_device_points(cursor, device, points)
    
    # 创建连接
    device_name = device['Device']
    device_type = get_device_type(device_name)
    used_points = set()
    
    # 获取设备规则
    rule = create_device_rule(device_name)
    if rule:
        terminal_set = {strip_device_prefix(p['Terminal']) for p in points}
        if rule.match(device_name, terminal_set):
            print("\n开始创建连接...")
            connections = rule.get_connections(points)
            
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
                
                print(f"创建连接: {strip_device_prefix(conn['sourceTerminal'])} -> "
                      f"{strip_device_prefix(conn['targetTerminal'])} "
                      f"({props.get('connType', 'unknown')})")
                      
                used_points.add(conn['source'])
                used_points.add(conn['target'])

    # 显示未使用的端子
    unused_points = get_unused_points(points, used_points)
    if unused_points:
        print("\n未创建连接的端子:")
        for point in unused_points:
            print(f"  * {strip_device_prefix(point['Terminal'])}")
    else:
        print("\n所有端子都已创建连接")

    # 显示处理结果摘要
    print(f"\n处理结果:")
    print(f"  * 总端子数: {len(points)}")
    print(f"  * 已连接端子数: {len(used_points)}")
    print(f"  * 未连接端子数: {len(unused_points)}")
    print(f"  * 创建连接数: {len(used_points) // 2}")  # 每个连接涉及两个端子

    # 等待用户确认
    input("\n按Enter键继续处理下一个设备...")
    return global_conn_id, used_points

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
            total_devices = len(filtered_devices)
            logger.info(f"筛选出 {total_devices} 个符合条件的设备")
            
            # 处理每个设备
            global_conn_id = 0
            total_used_points = 0
            total_unused_points = 0
            
            for i, device in enumerate(filtered_devices, 1):
                try:
                    global_conn_id, used_points = process_device(cursor, device, i, total_devices, global_conn_id)
                    total_used_points += len(used_points)
                    # 获取未使用的端子数
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM v_csv_devpoint
                        WHERE belongtoDevice = %s
                    """, (device['belongtoDevice'],))
                    result = cursor.fetchone()
                    total_points = result['count']
                    total_unused_points += total_points - len(used_points)
                    conn.commit()
                except Exception as e:
                    logger.error(f"处理设备 {device['Device']} 时出错: {str(e)}")
                    continue

            print("\n处理完成!")
            print(f"总设备数: {total_devices}")
            print(f"总连接数: {global_conn_id}")
            print(f"总端子数: {total_used_points + total_unused_points}")
            print(f"已连接端子数: {total_used_points}")
            print(f"未连接端子数: {total_unused_points}")
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