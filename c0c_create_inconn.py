#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
import json
import logging
from datetime import datetime
import pprint
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

def load_connection_rules(rules_file='c0c_inner_rules.json'):
    """加载连接规则配置"""
    try:
        if os.path.exists(rules_file):
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"规则文件 {rules_file} 不存在，将使用默认规则")
            return {
                "defaultConnectionProperties": {
                    "voltage": 0.0,
                    "current": 0.0,
                    "resistance": 0.0,
                    "isCable": False,
                    "isInPanel": True,
                    "connType": "internal"
                },
                "pointTypeRules": []
            }
    except Exception as e:
        logger.error(f"加载规则文件失败: {str(e)}")
        return None

def apply_rules_to_points(points, rules):
    """根据规则创建连接"""
    connections = []
    
    # 按端子类型(第一个字符)分组
    terminal_groups = {}
    for point in points:
        if point['Terminal'] and len(point['Terminal']) > 0:
            term_type = point['Terminal'][0]
            if term_type not in terminal_groups:
                terminal_groups[term_type] = []
            terminal_groups[term_type].append(point)
    
    # 应用规则
    for rule in rules.get('pointTypeRules', []):
        rule_type = rule.get('type')
        
        # 规则1: 相邻序号连接 (A1->A2->A3...)
        if rule_type == 'adjacentSequence':
            for point_type in rule.get('pointTypes', []):
                if point_type in terminal_groups:
                    group_points = terminal_groups[point_type]
                    if len(group_points) >= 2:
                        # 按Terminal排序
                        sorted_points = sorted(group_points, key=lambda x: x['Terminal'])
                        
                        # 连接相邻端子
                        for j in range(len(sorted_points) - 1):
                            p1 = sorted_points[j]
                            p2 = sorted_points[j + 1]
                            
                            # 确保源和目标不是同一个点
                            if p1['ftid'] != p2['ftid']:
                                conn_props = rule.get('connectionProperties', rules.get('defaultConnectionProperties', {}))
                                
                                connections.append({
                                    'source': p1['ftid'],
                                    'target': p2['ftid'],
                                    'sourceTerminal': p1['Terminal'],
                                    'targetTerminal': p2['Terminal'],
                                    'properties': conn_props,
                                    'ruleType': rule_type
                                })
        
        # 规则2: 匹配数字连接 (L1->T1, L2->T2...)
        elif rule_type == 'matchingNumbers':
            for point_group in rule.get('pointGroups', []):
                if len(point_group) == 2:
                    type1, type2 = point_group
                    
                    if type1 in terminal_groups and type2 in terminal_groups:
                        group1 = terminal_groups[type1]
                        group2 = terminal_groups[type2]
                        
                        # 提取数字部分并创建映射
                        points_map1 = {}
                        for p in group1:
                            term = p['Terminal']
                            # 尝试提取数字部分
                            match = re.search(r'(\d+)', term[1:] if len(term) > 1 else '')
                            if match:
                                num = match.group(1)
                                points_map1[num] = p
                        
                        # 查找匹配的端子
                        for p in group2:
                            term = p['Terminal']
                            # 尝试提取数字部分
                            match = re.search(r'(\d+)', term[1:] if len(term) > 1 else '')
                            if match:
                                num = match.group(1)
                                if num in points_map1:
                                    # 确保源和目标不是同一个点
                                    if points_map1[num]['ftid'] != p['ftid']:
                                        conn_props = rule.get('connectionProperties', rules.get('defaultConnectionProperties', {}))
                                        
                                        connections.append({
                                            'source': points_map1[num]['ftid'],
                                            'target': p['ftid'],
                                            'sourceTerminal': points_map1[num]['Terminal'],
                                            'targetTerminal': p['Terminal'],
                                            'properties': conn_props,
                                            'ruleType': rule_type
                                        })
        
        # 规则3: 特定点对连接 (如14-11, 14-12)
        elif rule_type == 'specificPair':
            # 创建端子号到端子的映射
            term_map = {}
            for group in terminal_groups.values():
                for p in group:
                    term_map[p['Terminal']] = p
            
            for pair in rule.get('pairs', []):
                point1 = pair.get('point1')
                point2 = pair.get('point2')
                
                # 检查是否有完全匹配的端子号
                if point1 in term_map and point2 in term_map:
                    p1 = term_map[point1]
                    p2 = term_map[point2]
                    
                    # 确保源和目标不是同一个点
                    if p1['ftid'] != p2['ftid']:
                        conn_props = pair.get('connectionProperties', rule.get('connectionProperties', rules.get('defaultConnectionProperties', {})))
                        
                        connections.append({
                            'source': p1['ftid'],
                            'target': p2['ftid'],
                            'sourceTerminal': p1['Terminal'],
                            'targetTerminal': p2['Terminal'],
                            'properties': conn_props,
                            'ruleType': rule_type
                        })
                # 检查是否有以这些数字结尾的端子
                else:
                    matching_terms1 = [t for t in term_map.keys() if t.endswith(point1)]
                    matching_terms2 = [t for t in term_map.keys() if t.endswith(point2)]
                    
                    for t1 in matching_terms1:
                        for t2 in matching_terms2:
                            # 检查前缀是否匹配
                            prefix1 = t1[:-len(point1)] if len(t1) > len(point1) else ''
                            prefix2 = t2[:-len(point2)] if len(t2) > len(point2) else ''
                            
                            if prefix1 == prefix2:
                                p1 = term_map[t1]
                                p2 = term_map[t2]
                                # 确保源和目标不是同一个点
                                if p1['ftid'] != p2['ftid']:
                                    conn_props = pair.get('connectionProperties', rule.get('connectionProperties', rules.get('defaultConnectionProperties', {})))
                                    
                                    connections.append({
                                        'source': p1['ftid'],
                                        'target': p2['ftid'],
                                        'sourceTerminal': p1['Terminal'],
                                        'targetTerminal': p2['Terminal'],
                                        'properties': conn_props,
                                        'ruleType': rule_type
                                    })
        
        # 规则4: 按钮后缀连接 (.1和.2结尾的端子)
        elif rule_type == 'buttonPostfix':
            postfixes = rule.get('postfixes', [])
            
            if len(postfixes) == 2:
                postfix1, postfix2 = postfixes
                # 创建端子号到端子的映射
                term_map = {}
                for group in terminal_groups.values():
                    for p in group:
                        term_map[p['Terminal']] = p
                
                # 查找带有特定后缀的端子
                suffix1_terms = [t for t in term_map.keys() if t.endswith(postfix1)]
                suffix2_terms = [t for t in term_map.keys() if t.endswith(postfix2)]
                
                # 根据前缀匹配对应的端子
                for t1 in suffix1_terms:
                    prefix1 = t1[:-len(postfix1)]
                    for t2 in suffix2_terms:
                        prefix2 = t2[:-len(postfix2)]
                        if prefix1 == prefix2:
                            p1 = term_map[t1]
                            p2 = term_map[t2]
                            # 确保源和目标不是同一个点
                            if p1['ftid'] != p2['ftid']:
                                conn_props = rule.get('connectionProperties', rules.get('defaultConnectionProperties', {}))
                                
                                connections.append({
                                    'source': p1['ftid'],
                                    'target': p2['ftid'],
                                    'sourceTerminal': p1['Terminal'],
                                    'targetTerminal': p2['Terminal'],
                                    'properties': conn_props,
                                    'ruleType': rule_type
                                })
        
        # 规则5: 特定前后缀配对 (1.13-1.14, 2.13-2.14...)
        elif rule_type == 'buttonPostfix':
            for pair in rule.get('postfixPairs', []):
                prefix = pair.get('prefix', '')
                postfix1 = pair.get('postfix1', '')
                postfix2 = pair.get('postfix2', '')
                
                # 创建端子号到端子的映射
                term_map = {}
                for group in terminal_groups.values():
                    for p in group:
                        term_map[p['Terminal']] = p
                
                # 查找特定模式的端子
                term1 = prefix + postfix1
                term2 = prefix + postfix2
                
                if term1 in term_map and term2 in term_map:
                    p1 = term_map[term1]
                    p2 = term_map[term2]
                    # 确保源和目标不是同一个点
                    if p1['ftid'] != p2['ftid']:
                        conn_props = pair.get('connectionProperties', rule.get('connectionProperties', rules.get('defaultConnectionProperties', {})))
                        
                        connections.append({
                            'source': p1['ftid'],
                            'target': p2['ftid'],
                            'sourceTerminal': p1['Terminal'],
                            'targetTerminal': p2['Terminal'],
                            'properties': conn_props,
                            'ruleType': rule_type
                        })
    
    return connections

def create_internal_connections():
    conn = None
    try:
        # 加载配置并连接数据库
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)['mysql']
        conn = get_db_connection()
        logger.info(f"已连接到数据库 {config['host']}")

        # 加载连接规则
        rules = load_connection_rules()
        if not rules:
            logger.error("无法加载连接规则，程序退出")
            return 1
        
        logger.info(f"成功加载了 {len(rules.get('pointTypeRules', []))} 条连接规则")
        
        # 获取允许处理的设备类型
        allowed_device_types = rules.get('allowedDeviceTypes', ["Q", "K", "D", "S"])
        logger.info(f"将只处理以下设备类型: {', '.join(allowed_device_types)}")

        # 用于记录总连接数和全局连接编号
        total_connections = 0
        global_conn_id = 0  # 添加全局连接ID计数器

        with conn.cursor() as cursor:
            # 直接从v_csv_devpoint表中获取所有不同的belongtoDevice
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
            filtered_devices = []
            for device in devices:
                device_name = device['Device']
                # 检查设备名称是否以允许的前缀开头
                if device_name and any(device_name.startswith(prefix) for prefix in allowed_device_types):
                    filtered_devices.append(device)
            
            logger.info(f"筛选出 {len(filtered_devices)} 个符合条件的设备")
            
            # 遍历每个设备并获取其端子点
            for i, device in enumerate(filtered_devices):
                belongtoDevice = device['belongtoDevice']
                print(f"\n=== 设备 {i+1}/{len(filtered_devices)}: {device['Device']}(-{belongtoDevice}) (位置: {device['Location']}) ===")
                
                # 获取当前设备的所有端子点（使用DISTINCT避免重复）
                cursor.execute("""
                    SELECT DISTINCT ftid, Terminal
                    FROM v_csv_devpoint
                    WHERE belongtoDevice = %s
                    ORDER BY Terminal
                """, (belongtoDevice,))
                points = cursor.fetchall()
                
                print(f"设备 {device['Device']}({belongtoDevice}) 共有 {len(points)} 个唯一端子点")
                
                # 简单列出所有端子点
                print("端子点列表:")
                for j, point in enumerate(points):
                    print(f"  {j+1}. {point['ftid']} - {point['Terminal']}")
                
                # 应用规则生成连接
                connections = apply_rules_to_points(points, rules)
                print(f"\n根据规则生成了 {len(connections)} 个连接")
                
                # 将连接写入数据库
                device_connections = 0
                for idx, conn_info in enumerate(connections):
                    try:
                        # 使用全局连接ID
                        global_conn_id += 1
                        conn_id = f"in{global_conn_id}"
                        print(f"  连接 {conn_info['sourceTerminal']} -> {conn_info['targetTerminal']} ({conn_info['ruleType']})")
                        
                        # 获取连接属性
                        props = conn_info['properties']
                        
                        # 插入数据库，不赋值 voltage, current, resistance
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
                            props.get('connType', 'internal')
                        ))
                        device_connections += 1
                        total_connections += 1
                    except Exception as e:
                        print(f"  创建连接失败: {str(e)}")
                
                # 提交当前设备的所有连接
                conn.commit()
                print(f"设备 {device['Device']}({belongtoDevice}) 共创建了 {device_connections} 个内部连接")
                
                # 添加一个分隔线
                print("="*50)
                
                # 恢复暂停功能，以便查看每个设备的处理结果
                input(f"已处理完设备 {i+1}/{len(filtered_devices)}: {device['Device']}，按Enter键继续下一个设备...")

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