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

def strip_device_prefix(terminal):
    """从端子号中去除设备前缀，只保留实际的端子号部分"""
    if ':' in terminal:
        return terminal.split(':')[-1]
    return terminal

def find_point_by_terminal(points, terminal):
    """在点位列表中查找指定端子号的点"""
    stripped_target = strip_device_prefix(terminal)
    # 先尝试完全匹配
    for point in points:
        if strip_device_prefix(point['Terminal']) == stripped_target:
            return point
    
    # 如果没有完全匹配，尝试后缀匹配
    if terminal.startswith('.'):
        for point in points:
            if strip_device_prefix(point['Terminal']).endswith(terminal):
                return point
    
    return None

def find_pattern_matching_points(points, pattern):
    """查找符合模式的端子点对"""
    matching_pairs = []
    # 创建一个字典，键是去除前缀后的端子号，值是原始点位
    terminals_dict = {strip_device_prefix(p['Terminal']): p for p in points}
    pattern1, pattern2 = pattern
    
    logger.info(f"尝试匹配模式 {pattern1} -> {pattern2}")
    logger.info(f"可用端子点: {list(terminals_dict.keys())}")
    
    # 定义常见的端子对模式
    simple_pairs = {
        '1': '2', '3': '4', '5': '6', '13': '14', '23': '24', 
        '33': '34', '43': '44', '53': '54', '21': '22',
        '3.13': '3.14'
    }
    
    # 对每个端子号（不带前缀）尝试匹配
    for terminal, point in terminals_dict.items():
        # 先处理简单的端子对匹配
        if terminal in simple_pairs and simple_pairs[terminal] in terminals_dict:
            target_terminal = simple_pairs[terminal]
            point2 = terminals_dict[target_terminal]
            if point['ftid'] != point2['ftid']:
                logger.info(f"找到匹配的端子对: {terminal}-{target_terminal}")
                matching_pairs.append((point, point2))
                continue  # 如果找到简单匹配，跳过正则匹配
        
        # 然后处理正则表达式匹配
        match = re.match(pattern1, terminal)
        if match:
            # 使用反向引用替换，需要保存捕获的组
            groups = match.groups()
            if groups:
                # 第一个分组（通常是数字部分）
                base = groups[0]
                # 根据模式创建目标端子号
                if pattern2 == "\\12":  # 对于 *1->*2 模式
                    target_terminal = f"{base}2"
                elif pattern2 == "\\14":  # 对于 *1->*4 模式
                    target_terminal = f"{base}4"
                elif pattern2.isdigit():  # 对于简单数字替换模式，如 1->2, 3->4
                    target_terminal = pattern2
                else:
                    target_terminal = re.sub(pattern1, pattern2, terminal)

                if target_terminal in terminals_dict:
                    point1 = point
                    point2 = terminals_dict[target_terminal]
                    if point1 and point2 and point1['ftid'] != point2['ftid']:
                        logger.info(f"找到匹配的端子对: {terminal}-{target_terminal}")
                        matching_pairs.append((point1, point2))

    return matching_pairs

def detect_device_subtype(points, device_rules):
    """检测设备子类型，基于端子点模式和优先级"""
    terminal_set = {strip_device_prefix(p['Terminal']) for p in points}
    matching_subtypes = []
    
    logger.info("可用端子点: %s", terminal_set)
    
    # 检查每个子类型的检测规则
    for subtype, rule in device_rules['subtypes'].items():
        matches = False
        if 'detection' in rule:
            detection = rule['detection']
            detection_results = []
            
            # 检查端子点模式
            if 'patterns' in detection:
                pattern_found = False
                for pattern in detection['patterns']:
                    for terminal in terminal_set:
                        if re.match(pattern, terminal):
                            pattern_found = True
                            logger.info(f"子类型 {subtype} 匹配模式 {pattern}: {terminal}")
                            break
                    if pattern_found:
                        break
                detection_results.append(('pattern', pattern_found))
            
            # 检查可选端子组（任一匹配即可）
            if 'or_terminals' in detection:
                required_terminals = set(detection['or_terminals'])
                terminals_match = bool(required_terminals.intersection(terminal_set))
                detection_results.append(('or_terminals', terminals_match))
                if terminals_match:
                    logger.info(f"子类型 {subtype} 匹配可选端子: 找到 {required_terminals.intersection(terminal_set)}")

            # 检查必需的端子点
            if 'terminals' in detection:
                required_terminals = set(detection['terminals'])
                terminals_match = required_terminals.issubset(terminal_set)
                detection_results.append(('terminals', terminals_match))
                if terminals_match:
                    logger.info(f"子类型 {subtype} 匹配必需端子: {required_terminals}")
            
            # 决定是否匹配：对于每种类型的检测，只要有一个匹配就算成功
            if detection_results:
                matches = any(result[1] for result in detection_results)
                matches_str = ', '.join(f"{result[0]}:{result[1]}" for result in detection_results)
                logger.info(f"子类型 {subtype} 检测结果: {matches_str} -> {'匹配' if matches else '不匹配'}")
        
        elif 'pattern' in rule:
            matches = True  # 默认模式匹配，具体匹配在get_device_subtype_rules中处理
        
        if matches:
            priority = rule.get('priority', 999)  # 没有优先级的规则优先级最低
            friendly_name = rule.get('friendly_name', subtype)
            matching_subtypes.append((subtype, priority, friendly_name))
    
    if matching_subtypes:
        # 按优先级排序，返回优先级最高的子类型
        matching_subtypes.sort(key=lambda x: x[1])
        logger.info(f"匹配的子类型: {[f'{name}(优先级:{pri})' for _, pri, name in matching_subtypes]}")
        return matching_subtypes[0][0], matching_subtypes[0][2]
    
    logger.info("没有匹配的子类型")
    return None, None

def get_device_subtype_rules(device_name, device_rules, points):
    """获取设备子类型的规则"""
    if 'subtypes' not in device_rules:
        friendly_name = device_rules.get('friendly_name', '默认规则')
        logger.info(f"使用设备类型默认规则: {friendly_name}")
        return device_rules, friendly_name
    
    # 获取匹配的子类型
    subtype, friendly_name = detect_device_subtype(points, device_rules)
    if subtype:
        rules = device_rules['subtypes'][subtype]
        # 如果规则有pattern，验证设备名称是否匹配
        if 'pattern' in rules:
            pattern = rules['pattern']
            if not re.match(pattern, device_name):
                logger.info(f"设备名 {device_name} 不匹配规则模式 {pattern}")
                # 如果不匹配且不是基于端子检测的规则，继续尝试其他规则
                if 'detection' not in rules:
                    subtype = None
                    friendly_name = None
            else:
                logger.info(f"设备名 {device_name} 匹配规则模式 {pattern}")
    
    # 如果没有匹配的特定规则，使用默认规则
    if not subtype and 'default' in device_rules['subtypes']:
        default_rules = device_rules['subtypes']['default']
        friendly_name = default_rules.get('friendly_name', '默认规则')
        logger.info(f"使用默认规则：{friendly_name}")
        return default_rules, friendly_name
    elif subtype:
        logger.info(f"使用规则：{friendly_name}")
        return device_rules['subtypes'][subtype], friendly_name
    
    logger.info("没有找到匹配的规则")
    return None, None

def apply_device_rules(points, device_name, device_type, rules):
    """应用设备规则生成连接"""
    connections = []
    used_points = set()  # 用于跟踪已使用的端子点
    rule_name = None  # 用于存储使用的规则名称

    if not rules or 'deviceRules' not in rules or device_type not in rules['deviceRules']:
        return connections, used_points, rule_name

    device_rules = rules['deviceRules'][device_type]
    device_rules, rule_name = get_device_subtype_rules(device_name, device_rules, points)
    
    if not device_rules:
        return connections, used_points, rule_name
    
    default_props = rules.get('defaultConnectionProperties', {})

    for conn_rule in device_rules.get('connections', []):
        # 处理线圈连接
        if conn_rule['type'] == 'coil':
            point1 = find_point_by_terminal(points, conn_rule['points'][0])
            point2 = find_point_by_terminal(points, conn_rule['points'][1])
            
            if point1 and point2:
                props = {**default_props, **conn_rule.get('properties', {})}
                connections.append(create_connection(point1, point2, props))
                used_points.add(point1['ftid'])
                used_points.add(point2['ftid'])
        
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
                        used_points.add(point1['ftid'])
                        used_points.add(point2['ftid'])
                
                # 处理NO连接
                if 'no' in pair:
                    point1 = find_point_by_terminal(points, pair['no'][0])
                    point2 = find_point_by_terminal(points, pair['no'][1])
                    if point1 and point2:
                        props = {**default_props, **conn_rule.get('properties', {}), 'connType': 'NO'}
                        connections.append(create_connection(point1, point2, props))
                        used_points.add(point1['ftid'])
                        used_points.add(point2['ftid'])
            
            # 处理模式匹配的端子对
            for pattern_pair in conn_rule.get('pattern_pairs', []):
                # 处理单个类型的模式
                for conn_type, pattern_info in pattern_pair.items():
                    if conn_type == 'combined':
                        # 处理组合模式
                        for pattern_set in pattern_info.get('patterns', []):
                            for type_name, pattern in pattern_set.items():
                                matched_pairs = find_pattern_matching_points(points, pattern)
                                for point1, point2 in matched_pairs:
                                    props = {**default_props, **conn_rule.get('properties', {}), 'connType': type_name.upper()}
                                    connections.append(create_connection(point1, point2, props))
                                    used_points.add(point1['ftid'])
                                    used_points.add(point2['ftid'])
                    elif isinstance(pattern_info, dict) and 'pattern' in pattern_info:
                        # 处理普通模式
                        matched_pairs = find_pattern_matching_points(points, pattern_info['pattern'])
                        for point1, point2 in matched_pairs:
                            props = {**default_props, **conn_rule.get('properties', {}), 'connType': conn_type.upper()}
                            connections.append(create_connection(point1, point2, props))
                            used_points.add(point1['ftid'])
                            used_points.add(point2['ftid'])

    return connections, used_points, rule_name

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
                device_index = f"设备 {i+1}/{len(filtered_devices)}"
                
                print(f"\n{'='*20} {device_index}: {device_name} {'='*20}")
                print(f"位置: {device['Location']}")
                print(f"设备ID: {belongtoDevice}")
                
                # 获取当前设备的所有端子点
                cursor.execute("""
                    SELECT DISTINCT ftid, Terminal
                    FROM v_csv_devpoint
                    WHERE belongtoDevice = %s
                    ORDER BY Terminal
                """, (belongtoDevice,))
                points = cursor.fetchall()
                
                print(f"\n总端子数: {len(points)} 个")
                
                # 简单列出所有端子点
                print("端子点列表:")
                for j, point in enumerate(points):
                    print(f"  {j+1}. {point['ftid']} - {point['Terminal']}")
                
                # 应用规则生成连接
                connections, used_points, rule_name = apply_device_rules(points, device_name, device_type, rules)
                
                # 生成摘要信息
                summary = []
                summary.append(f"应用规则: {rule_name or '无匹配规则'}")
                summary.append(f"生成连接: {len(connections)} 个")
                
                # 处理连接
                print("\n" + "\n".join(summary))
                if connections:
                    print("\n连接详情:")
                    device_connections = 0
                    for idx, conn_info in enumerate(connections):
                        try:
                            global_conn_id += 1
                            conn_id = f"in{global_conn_id}"
                            props = conn_info['properties']
                            desc = props.get('description', '')
                            desc_str = f" ({desc})" if desc else "" 
                            print(f"  {strip_device_prefix(conn_info['sourceTerminal'])} -> "
                                  f"{strip_device_prefix(conn_info['targetTerminal'])} "
                                  f"({props.get('connType', 'unknown')}{desc_str})")
                            
                            cursor.execute("""
                                INSERT INTO v_csv_innerconn
                                (connNo, source, target, color, isCable, isInPanel, connType, voltage, current, resistance)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                conn_id,
                                conn_info['source'],
                                conn_info['target'],
                                None,
                                1 if props.get('isCable', False) else 0,
                                1 if props.get('isInPanel', True) else 0,
                                props.get('connType', 'devInConn'),
                                props.get('voltage', 0.0),
                                props.get('current', 0.0),
                                props.get('resistance', 0.0)
                            ))
                            device_connections += 1
                            total_connections += 1
                        except Exception as e:
                            print(f"  创建连接失败: {str(e)}")
                
                # 列出未使用的端子点
                unused_points = get_unused_points(points, used_points)
                if unused_points:
                    print("\n未连接端子:")
                    for point in unused_points:
                        print(f"  * {point['ftid']} - {strip_device_prefix(point['Terminal'])}")
                
                # 提交当前设备的所有连接
                conn.commit()
                
                # 显示处理结果摘要
                print(f"\n{device_index} 处理完成:")
                print(f"  * 总端子数: {len(points)}")
                print(f"  * 已连接: {len(used_points)} 个端子")
                print(f"  * 未连接: {len(unused_points)} 个端子")
                print(f"  * 创建连接: {device_connections} 个")
                
                # 添加分隔线
                print("="*60)
                
                # 暂停等待用户确认
                #input(f"按Enter键继续处理下一个设备...")

            # 显示总体处理结果
            print("\n处理完成！")
            print(f"总设备数: {len(filtered_devices)}")
            print(f"总连接数: {total_connections}")
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