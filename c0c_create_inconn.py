#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
import json
import logging
from datetime import datetime
import re
import os

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

def load_device_rules(rules_file='c0c_inner_rules.json'):
    """加载设备连接规则配置"""
    try:
        if os.path.exists(rules_file):
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.error(f"规则文件 {rules_file} 不存在")
            return None
    except Exception as e:
        logger.error(f"加载规则文件失败: {str(e)}")
        return None

def get_device_type(device_name):
    """获取设备类型（第一个字母）"""
    if device_name and len(device_name) > 0:
        return device_name[0].upper()
    return None

def create_connection(source_point, target_point, properties):
    """创建连接对象"""
    return {
        'source': source_point['ftid'],
        'target': target_point['ftid'],
        'sourceTerminal': source_point['Terminal'],
        'targetTerminal': target_point['Terminal'],
        'properties': properties
    }

def find_point_by_terminal(points, terminal):
    """在点位列表中查找指定端子号的点"""
    # 先尝试完全匹配
    for point in points:
        if point['Terminal'] == terminal:
            return point
    
    # 如果没有完全匹配，尝试后缀匹配
    if terminal.startswith('.'):
        for point in points:
            if point['Terminal'].endswith(terminal):
                return point
    
    return None

def find_pattern_matching_points(points, pattern_pair):
    """查找符合模式的端子点对"""
    matching_pairs = []
    terminals = [point['Terminal'] for point in points]
    
    # 从pattern_pair中获取正则表达式模式
    pattern1, pattern2 = pattern_pair
    
    # 为每个端子尝试匹配第一个模式
    for term in terminals:
        match1 = re.match(pattern1, term)
        if match1:
            # 使用第一个匹配的分组创建第二个端子的期望值
            expected_term2 = re.sub(pattern1, pattern2, term)
            if expected_term2 in terminals:
                point1 = find_point_by_terminal(points, term)
                point2 = find_point_by_terminal(points, expected_term2)
                if point1 and point2:
                    matching_pairs.append((point1, point2))
    
    return matching_pairs

def get_device_subtype_rules(device_name, device_rules):
    """获取设备子类型的规则"""
    if 'subtypes' not in device_rules:
        return device_rules
    
    # 遍历所有子类型规则
    for subtype, rules in device_rules['subtypes'].items():
        if 'pattern' in rules and re.match(rules['pattern'], device_name):
            return rules
    
    # 如果没有匹配的特定规则，使用默认规则
    if 'default' in device_rules['subtypes']:
        return device_rules['subtypes']['default']
    
    return None

def apply_device_rules(points, device_name, device_type, rules):
    """应用设备规则生成连接"""
    connections = []
    
    if not rules or 'deviceRules' not in rules or device_type not in rules['deviceRules']:
        return connections

    device_rules = rules['deviceRules'][device_type]
    device_rules = get_device_subtype_rules(device_name, device_rules)
    
    if not device_rules:
        return connections
    
    default_props = rules.get('defaultConnectionProperties', {})

    for conn_rule in device_rules.get('connections', []):
        # 处理线圈连接
        if conn_rule['type'] == 'coil':
            point1 = find_point_by_terminal(points, conn_rule['points'][0])
            point2 = find_point_by_terminal(points, conn_rule['points'][1])
            
            if point1 and point2:
                props = {**default_props, **conn_rule.get('properties', {})}
                connections.append(create_connection(point1, point2, props))
        
        # 处理触点连接
        elif conn_rule['type'] == 'contacts':
            # 处理固定的端子对
            for pair in conn_rule.get('pairs', []):
                # 处理NC连接
                if 'nc' in pair:
                    point1 = find_point_by_terminal(points, pair['nc'][0])
                    point2 = find_point_by_terminal(points, pair['nc'][1])
                    if point1 and point2:
                        props = {**default_props, **conn_rule.get('properties', {}), 'connType': 'NC'}
                        connections.append(create_connection(point1, point2, props))
                
                # 处理NO连接
                if 'no' in pair:
                    point1 = find_point_by_terminal(points, pair['no'][0])
                    point2 = find_point_by_terminal(points, pair['no'][1])
                    if point1 and point2:
                        props = {**default_props, **conn_rule.get('properties', {}), 'connType': 'NO'}
                        connections.append(create_connection(point1, point2, props))
                
                # 处理SNC连接
                if 'snc' in pair:
                    point1 = find_point_by_terminal(points, pair['snc'][0])
                    point2 = find_point_by_terminal(points, pair['snc'][1])
                    if point1 and point2:
                        props = {**default_props, **conn_rule.get('properties', {}), 'connType': 'SNC'}
                        connections.append(create_connection(point1, point2, props))
                
                # 处理SNO连接
                if 'sno' in pair:
                    point1 = find_point_by_terminal(points, pair['sno'][0])
                    point2 = find_point_by_terminal(points, pair['sno'][1])
                    if point1 and point2:
                        props = {**default_props, **conn_rule.get('properties', {}), 'connType': 'SNO'}
                        connections.append(create_connection(point1, point2, props))
            
            # 处理模式匹配的端子对
            for pattern_pair in conn_rule.get('pattern_pairs', []):
                for conn_type, pattern_info in pattern_pair.items():
                    if isinstance(pattern_info, dict) and 'pattern' in pattern_info:
                        matched_pairs = find_pattern_matching_points(points, pattern_info['pattern'])
                        for point1, point2 in matched_pairs:
                            props = {**default_props, **conn_rule.get('properties', {}), 'connType': conn_type.upper()}
                            connections.append(create_connection(point1, point2, props))
            
            # 处理S设备的变体规则
            if 'variants' in conn_rule:
                variants = conn_rule['variants']
                
                # 检查是否有.1和.2端子（带后缀的变体）
                if 'with_postfix' in variants:
                    has_postfix = any(
                        find_point_by_terminal(points, pair['snc'][0])
                        and find_point_by_terminal(points, pair['snc'][1])
                        for variant in variants['with_postfix']
                        for pair in ([{'snc': variant['snc']}] if 'snc' in variant else [])
                    )
                    if has_postfix:
                        for variant in variants['with_postfix']:
                            if 'snc' in variant:
                                point1 = find_point_by_terminal(points, variant['snc'][0])
                                point2 = find_point_by_terminal(points, variant['snc'][1])
                                if point1 and point2:
                                    props = {**default_props, **conn_rule.get('properties', {}), 'connType': 'SNC'}
                                    connections.append(create_connection(point1, point2, props))
                
                # 检查1-4连接变体
                elif 'has_1_4' in variants:
                    point1 = find_point_by_terminal(points, '1')
                    point4 = find_point_by_terminal(points, '4')
                    if point1 and point4:
                        for variant in variants['1-4_only']:
                            props = {**default_props, **conn_rule.get('properties', {}), 'connType': 'SNC'}
                            connections.append(create_connection(point1, point4, props))

    return connections

def create_internal_connections():
    """创建设备内部连接的主函数"""
    conn = None
    try:
        # 连接数据库
        conn = get_db_connection()
        logger.info("已连接到数据库")

        # 加载连接规则
        rules = load_device_rules()
        if not rules:
            logger.error("无法加载连接规则，程序退出")
            return 1
        
        logger.info(f"成功加载设备规则")
        
        # 获取允许处理的设备类型
        allowed_device_types = rules.get('allowedDeviceTypes', ["K", "Q", "S"])
        logger.info(f"将处理以下设备类型: {', '.join(allowed_device_types)}")

        # 用于记录总连接数和全局连接编号
        total_connections = 0
        global_conn_id = 0

        with conn.cursor() as cursor:
            # 获取所有设备信息
            logger.info("从v_csv_devpoint表获取所有设备信息...")
            cursor.execute("""
                SELECT DISTINCT belongtoDevice, Location, Device
                FROM v_csv_devpoint
                WHERE Location LIKE 'K1.%'
                ORDER BY Location, Device
            """)
            devices = cursor.fetchall()
            logger.info(f"找到 {len(devices)} 个设备")

            # 过滤只处理特定类型的设备
            filtered_devices = [
                device for device in devices
                if device['Device'] and get_device_type(device['Device']) in allowed_device_types
            ]
            
            logger.info(f"筛选出 {len(filtered_devices)} 个符合条件的设备")
            
            # 遍历每个设备并获取其端子点
            for i, device in enumerate(filtered_devices):
                belongtoDevice = device['belongtoDevice']
                device_name = device['Device']
                device_type = get_device_type(device_name)
                
                print(f"\n=== 设备 {i+1}/{len(filtered_devices)}: {device_name}(-{belongtoDevice}) (位置: {device['Location']}) ===")
                
                # 获取当前设备的所有端子点
                cursor.execute("""
                    SELECT DISTINCT ftid, Terminal
                    FROM v_csv_devpoint
                    WHERE belongtoDevice = %s
                    ORDER BY Terminal
                """, (belongtoDevice,))
                points = cursor.fetchall()
                
                print(f"设备 {device_name}({belongtoDevice}) 共有 {len(points)} 个唯一端子点")
                
                # 简单列出所有端子点
                print("端子点列表:")
                for j, point in enumerate(points):
                    print(f"  {j+1}. {point['ftid']} - {point['Terminal']}")
                
                # 应用规则生成连接
                connections = apply_device_rules(points, device_name, device_type, rules)
                print(f"\n根据规则生成了 {len(connections)} 个连接")
                
                # 将连接写入数据库
                device_connections = 0
                for idx, conn_info in enumerate(connections):
                    try:
                        global_conn_id += 1
                        conn_id = f"in{global_conn_id}"
                        
                        # 获取连接属性
                        props = conn_info['properties']
                        
                        print(f"  连接 {conn_info['sourceTerminal']} -> {conn_info['targetTerminal']} ({props.get('connType', 'unknown')})")
                        
                        # 插入数据库
                        cursor.execute("""
                            INSERT INTO v_csv_conn
                            (connNo, source, target, color, isCable, isInPanel, connType)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            conn_id,
                            conn_info['source'],
                            conn_info['target'],
                            None,
                            1 if props.get('isCable', False) else 0,
                            1 if props.get('isInPanel', True) else 0,
                            props.get('connType', 'devInConn')
                        ))
                        device_connections += 1
                        total_connections += 1
                    except Exception as e:
                        print(f"  创建连接失败: {str(e)}")
                
                # 提交当前设备的所有连接
                conn.commit()
                print(f"设备 {device_name}({belongtoDevice}) 共创建了 {device_connections} 个内部连接")
                
                # 添加分隔线
                print("="*50)
                
                # 暂停等待用户确认
                input(f"已处理完设备 {i+1}/{len(filtered_devices)}: {device_name}，按Enter键继续下一个设备...")

            logger.info(f"总共创建了 {total_connections} 个内部连接")
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