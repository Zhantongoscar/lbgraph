from neo4j import GraphDatabase
import re
import pymysql
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import sys
import traceback
import time

def initialize_database(mysql_cursor, mysql_conn):
    """
    初始化数据库，创建必要的表
    """
    try:
        print("正在初始化数据库...")
        
        # 创建v_simpoint表
        create_vsimpoint_query = """
        CREATE TABLE IF NOT EXISTS v_simpoint (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ftid VARCHAR(255) NOT NULL,
            project_name VARCHAR(255) NOT NULL,
            moduler VARCHAR(255) NOT NULL,
            device_name VARCHAR(255) NOT NULL,
            point_type VARCHAR(50) NOT NULL,
            point_index INT NOT NULL,
            sim_type VARCHAR(50),
            mode VARCHAR(50),
            hartingbox VARCHAR(50),
            description TEXT,
            target_ftid VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ftid (ftid),
            INDEX idx_target_ftid (target_ftid),
            INDEX idx_moduler (moduler)
        )
        """
        
        print("创建v_simpoint表...")
        mysql_cursor.execute(create_vsimpoint_query)
        
        # 检查数据库连接
        try:
            mysql_cursor.execute("SELECT 1")
            print("MySQL连接正常")
        except Exception as e:
            print(f"MySQL连接测试失败: {str(e)}")
            raise

        # 检查数据库名称
        try:
            mysql_cursor.execute("SELECT DATABASE()")
            db_name = mysql_cursor.fetchone()['DATABASE()']
            print(f"当前数据库: {db_name}")
        except Exception as e:
            print(f"获取数据库名称失败: {str(e)}")
            raise

        # 检查devices表是否存在
        try:
            show_tables_query = "SHOW TABLES LIKE 'devices'"
            mysql_cursor.execute(show_tables_query)
            if not mysql_cursor.fetchone():
                raise Exception("devices表不存在，请确保数据库已正确初始化")

            print("检查devices表结构...")
            # 检查表结构
            check_devices_query = "DESCRIBE devices"
            mysql_cursor.execute(check_devices_query)
            device_fields = mysql_cursor.fetchall()
            if not device_fields:
                raise Exception("devices表结构为空")
            # 使用Field名称来访问字段名
            field_names = [field['Field'] for field in device_fields]
            print(f"devices表字段: {', '.join(field_names)}")

            # 检查现有数据
            count_query = "SELECT COUNT(*) as count FROM devices"
            mysql_cursor.execute(count_query)
            result = mysql_cursor.fetchone()
            print(f"devices表现有记录数: {result['count']}")

        except Exception as e:
            print(f"检查devices表时出错: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
            traceback.print_exc()
            raise
        
        # 同步现有的模板数据到devices表
        templates_query = """
            SELECT DISTINCT moduler, hartingbox
            FROM v_simpoint
            WHERE (moduler LIKE 'EDB%' OR moduler LIKE 'EBD%')
            AND hartingbox IS NOT NULL
        """
        
        try:
            # 使用默认项目lb_test
            project_name = 'lb_test'
            print(f"使用项目名称: {project_name}")
            
            # 验证项目存在并已订阅
            project_query = "SELECT project_name, is_subscribed FROM project_subscriptions WHERE project_name = %s"
            mysql_cursor.execute(project_query, (project_name,))
            project = mysql_cursor.fetchone()
            
            if not project:
                raise Exception(f"项目'{project_name}'不存在")
            if not project['is_subscribed']:
                raise Exception(f"项目'{project_name}'未订阅")

            # 查找模板
            print("查找现有模板...")
            mysql_cursor.execute(templates_query)
            templates = mysql_cursor.fetchall()
            print(f"找到 {len(templates)} 个模板")
            
            if templates:
                print("\n同步模板到devices表...")
                inserted_count = 0
                for template in templates:
                    moduler = template['moduler']
                    # 从moduler (如"EDB1")中提取类型和序号
                    module_type = moduler[:3]  # "EDB"
                    serial_number = moduler[3:] # "1"
                    
                    insert_query = """
                        INSERT IGNORE INTO devices
                        (project_name, module_type, serial_number, type_id, status, rssi, Location)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    params = (
                        project_name,      # 使用找到的有效项目名称
                        module_type,
                        serial_number,
                        1 if module_type == 'EDB' else 2,  # EDB=1, EBD=2
                        'online',
                        0,
                        template['hartingbox']
                    )
                    
                    try:
                        print(f"正在同步模板: {moduler}")
                        mysql_cursor.execute(insert_query, params)
                        mysql_conn.commit()  # 每个插入都立即提交
                        inserted_count += mysql_cursor.rowcount
                        print(f"  - 成功: rowcount={mysql_cursor.rowcount}")
                    except Exception as e:
                        print(f"  - 失败: {str(e)}")
                        mysql_conn.rollback()
                
                mysql_cursor.execute("SELECT COUNT(*) as count FROM devices")
                count = mysql_cursor.fetchone()['count']
                print(f"同步完成，插入{inserted_count}条记录，devices表现有记录数: {count}")
                
        except Exception as e:
            print(f"同步模板时出错: {str(e)}")
            mysql_conn.rollback()
            raise
        
        mysql_conn.commit()
        print("数据库初始化完成")
        
    except Exception as e:
        print(f"初始化数据库失败: {str(e)}")
        mysql_conn.rollback()
        raise

# MySQL数据库连接
# MySQL数据库连接
def get_mysql_connection():
    """
    获取MySQL数据库连接，包含重试机制
    """
    max_retries = 3
    retry_interval = 5  # 秒
    current_try = 1
    
    while current_try <= max_retries:
        try:
            print(f"\n尝试连接MySQL (第{current_try}次尝试)...")
            config = MYSQL_CONFIG.copy()
            config['connect_timeout'] = 30  # 增加连接超时时间
            config['read_timeout'] = 30     # 增加读取超时时间
            config['write_timeout'] = 30    # 增加写入超时时间
            return pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
        except Exception as e:
            print(f"MySQL连接失败: {str(e)}")
            if current_try < max_retries:
                print(f"等待{retry_interval}秒后重试...")
                time.sleep(retry_interval)
                current_try += 1
            else:
                print("已达到最大重试次数，退出程序")
                sys.exit(1)

def extract_sort_key(terminal_id):
    match = re.match(r'(.+?:)(\d+)$', terminal_id)
    if match:
        return (match.group(1), int(match.group(2)))
    return (terminal_id, 0)

def determine_node_type(properties):
    """
    根据节点的属性确定其实际类型
    """
    # 检查属性大小写
    function_key = None
    for key in properties:
        if key.lower() == 'function':
            function_key = key
            break
    
    if function_key and properties[function_key]:
        function = properties[function_key]
        # Q开头通常表示数字输出(DO)
        if function.startswith('Q'):
            return 'DO'
        # I开头通常表示数字输入(DI)
        elif function.startswith('I'):
            return 'DI'
    
    # 尝试从Type属性获取类型
    type_key = None
    for key in properties:
        if key.lower() == 'type':
            type_key = key
            break
            
    return properties.get(type_key, 'Unknown') if type_key else 'Unknown'

def determine_need_type(end_type):
    """
    根据终点类型确定需要的类型
    """
    if end_type == 'DO':
        return 'DI'
    elif end_type == 'DI':
        return 'DO'
    return 'Unknown'

def get_next_template_number(mysql_cursor, template_prefix):
    """
    获取下一个可用的模板序号
    """
    query = """
    SELECT MAX(CAST(SUBSTRING(moduler, %s) AS UNSIGNED))
    FROM v_simpoint
    WHERE moduler LIKE %s
    """
    print(f"    [DEBUG SQL] 执行查询: {query}")
    print(f"    [DEBUG SQL] 参数: {(len(template_prefix) + 1, f'{template_prefix}%')}")
    
    mysql_cursor.execute(query, (len(template_prefix) + 1, f"{template_prefix}%"))
    result = mysql_cursor.fetchone()
    
    # 安全地访问字典结果
    max_key = f"MAX(CAST(SUBSTRING(moduler, {len(template_prefix) + 1}) AS UNSIGNED))"
    next_num = 1
    if result and result[max_key] is not None:
        next_num = result[max_key] + 1
    
    print(f"    [DEBUG] 下一个模板序号: {next_num}")
    return next_num

def check_template_count(mysql_cursor, template_prefix):
    """
    检查模板数量是否达到限制
    """
    query = """
    SELECT COUNT(DISTINCT moduler)
    FROM v_simpoint
    WHERE moduler LIKE %s
    """
    print(f"    [DEBUG SQL] 执行查询: {query}")
    print(f"    [DEBUG SQL] 参数: {(f'{template_prefix}%',)}")
    
    mysql_cursor.execute(query, (f"{template_prefix}%",))
    result = mysql_cursor.fetchone()
    count = result['COUNT(DISTINCT moduler)']
    
    print(f"    [DEBUG] 当前{template_prefix}模板数量: {count}")
    return count

def find_available_template(mysql_cursor, need_type, harting_group):
    """
    查找可用的模板
    """
    template_prefix = 'EDB' if need_type == 'DI' else 'EBD'
    point_type = 'DI' if need_type == 'DI' else 'DO'
    query = """
    SELECT DISTINCT s1.moduler, COUNT(s2.id) as available_points
    FROM v_simpoint s1
    LEFT JOIN v_simpoint s2 ON s1.moduler = s2.moduler
        AND s2.target_ftid IS NULL
        AND s2.point_type = %s
        AND (s2.hartingbox = %s OR s2.hartingbox IS NULL)
    WHERE s1.moduler LIKE %s
    GROUP BY s1.moduler
    HAVING available_points > 0
    ORDER BY s1.moduler ASC, available_points DESC
    LIMIT 1
    """
    
    print(f"    [DEBUG SQL] 执行查询: {query}")
    print(f"    [DEBUG SQL] 参数: {(point_type, harting_group, f'{template_prefix}%')}")
    
    mysql_cursor.execute(query, (point_type, harting_group, f"{template_prefix}%"))
    result = mysql_cursor.fetchone()
    
    if result:
        print(f"    [DEBUG] 找到可用模板: {result['moduler']}，剩余点位数: {result['available_points']}")
        return result['moduler']
    else:
        print(f"    [DEBUG] 未找到可用的{template_prefix}模板")
        return None

def create_new_template(mysql_cursor, mysql_conn, need_type, harting_group, project_id):
    """
    创建新的模板，并同步到devices表
    """
    template_prefix = 'EDB' if need_type == 'DI' else 'EBD'
    print(f"    [DEBUG] 开始创建新的{template_prefix}模板")
    
    # 检查模板数量
    count = check_template_count(mysql_cursor, template_prefix)
    if count >= 10:
        raise Exception(f"{template_prefix}模板数量已达到上限(10个)")
    
    # 获取下一个模板序号
    next_num = get_next_template_number(mysql_cursor, template_prefix)
    template_name = f"{template_prefix}{next_num}"
    
    try:
        # 获取设备类型ID
        query = "SELECT id FROM device_types WHERE type_name = %s"
        print(f"    [DEBUG SQL] 执行查询: {query}")
        print(f"    [DEBUG SQL] 参数: {(template_prefix,)}")
        
        mysql_cursor.execute(query, (template_prefix,))
        result = mysql_cursor.fetchone()
        
        if not result:
            raise Exception(f"未找到{template_prefix}类型的设备配置")
        
        type_id = result['id']
        print(f"    [DEBUG] 找到设备类型ID: {type_id}")
        
        # 首先创建devices表记录
        try:
            # 获取当前devices表中的结构
            desc_query = "DESCRIBE devices"
            mysql_cursor.execute(desc_query)
            device_fields = mysql_cursor.fetchall()
            print(f"    [DEBUG] devices表字段: {[field['Field'] for field in device_fields]}")

            # 构建插入查询
            devices_query = """
                INSERT INTO devices
                (project_name, module_type, serial_number, type_id, status, rssi, Location)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            # 从template_name中提取serial_number（数字部分）
            serial_number = str(next_num)
            
            # 验证项目存在并已订阅
            project_query = "SELECT project_name, is_subscribed FROM project_subscriptions WHERE project_name = 'lb_test'"
            mysql_cursor.execute(project_query)
            project = mysql_cursor.fetchone()
            
            if not project:
                raise Exception("项目'lb_test'不存在")
            if not project['is_subscribed']:
                raise Exception("项目'lb_test'未订阅")

            devices_params = (
                'lb_test',         # 使用固定的项目名称
                template_prefix,    # module_type (EDB或EBD)
                serial_number,      # serial_number（仅数字部分）
                type_id,           # type_id
                'online',          # status
                0,                # rssi 默认值
                harting_group     # Location (X20-X23)
            )
            print(f"    [DEBUG SQL] 创建devices记录: {devices_query}")
            print(f"    [DEBUG SQL] 参数: {devices_params}")
            mysql_cursor.execute(devices_query, devices_params)
            print(f"    [DEBUG] 成功创建devices记录: {template_name}")
        except Exception as e:
            print(f"    [ERROR] 创建devices记录失败: {str(e)}")
            traceback.print_exc()
            raise
        
        # 获取点位配置
        query = """
            SELECT point_index, point_type, sim_type, mode, point_name
            FROM device_type_points
            WHERE device_type_id = %s
        """
        print(f"    [DEBUG SQL] 执行查询: {query}")
        print(f"    [DEBUG SQL] 参数: {(type_id,)}")
        
        mysql_cursor.execute(query, (type_id,))
        points = mysql_cursor.fetchall()
        
        print(f"    [DEBUG] 找到{len(points)}个点位配置")
        
        # 创建新的模板实例
        for point in points:
            query = """
                INSERT INTO v_simpoint
                (ftid, project_name, moduler, device_name,
                 point_type, point_index, sim_type, mode, hartingbox, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 构建新的ftid格式: =<project_name>+Sim-<template_name>_<point_index>
            # 使用冒号替换下划线作为分隔符
            ftid = f"=lb_test+Sim-{template_name}:{point['point_index']}"
            print(f"    [DEBUG] 创建点位ftid: {ftid}")
            params = (
                ftid,
                project_id,
                template_name,
                template_name,
                point['point_type'],
                point['point_index'],
                point['sim_type'],
                point['mode'],
                harting_group,
                point.get('point_name', '')  # 使用点位名称作为描述，如果有的话
            )
            
            print(f"    [DEBUG SQL] 插入点位: {ftid}")
            mysql_cursor.execute(query, params)
        
        mysql_conn.commit()
        print(f"    [DEBUG] 成功创建模板: {template_name}")
        return template_name
        
    except Exception as e:
        mysql_conn.rollback()
        print(f"    [ERROR] 创建新模板失败: {str(e)}")
        traceback.print_exc()
        raise Exception(f"创建新模板失败: {str(e)}")

def assign_point(mysql_cursor, mysql_conn, template_name, target_ftid, need_type, harting_group):
    """
    在模板中分配点位
    """
    try:
        print(f"    [DEBUG] 开始为target_ftid={target_ftid}分配点位")
        print(f"    [DEBUG] 模板={template_name}, 需要类型={need_type}, Harting组={harting_group}")
        
        # 查找合适的点位
        query = """
        SELECT id, ftid, point_type
        FROM v_simpoint
        WHERE moduler = %s
        AND target_ftid IS NULL
        AND point_type = %s
        ORDER BY ftid ASC
        LIMIT 1
        """
        
        point_type = 'DI' if need_type == 'DI' else 'DO'
        
        print(f"    [DEBUG SQL] 执行查询: {query}")
        print(f"    [DEBUG SQL] 参数: {(template_name, point_type)}")
        
        mysql_cursor.execute(query, (template_name, point_type))
        result = mysql_cursor.fetchone()
        
        if not result:
            raise Exception(f"在模板{template_name}中未找到可用的{point_type}点位")
            
        print(f"    [DEBUG] 找到可用点位: id={result['id']}, ftid={result['ftid']}, type={result['point_type']}")
        
        # 检查点位类型是否匹配
        if result['point_type'] != point_type:
            raise Exception(f"点位类型不匹配: 需要{point_type}，但找到{result['point_type']}")
        
        try:
            # 更新点位和hartingbox
            query = """
                UPDATE v_simpoint
                SET target_ftid = %s,
                    hartingbox = %s
                WHERE id = %s
            """
            
            print(f"    [DEBUG SQL] 执行更新: {query}")
            print(f"    [DEBUG SQL] 参数: {(target_ftid, harting_group, result['id'])}")
            
            mysql_cursor.execute(query, (target_ftid, harting_group, result['id']))
            print(f"    [DEBUG] 已更新点位 id={result['id']} 的target_ftid={target_ftid}")
            
            # 更新同一模板下所有点位的hartingbox
            query = """
                UPDATE v_simpoint
                SET hartingbox = %s
                WHERE moduler = %s
                AND hartingbox IS NULL
            """
            
            print(f"    [DEBUG SQL] 执行更新: {query}")
            print(f"    [DEBUG SQL] 参数: {(harting_group, template_name)}")
            
            mysql_cursor.execute(query, (harting_group, template_name))
            
            # 检查更新结果
            query = """
                SELECT COUNT(*)
                FROM v_simpoint
                WHERE moduler = %s AND hartingbox = %s
            """
            
            mysql_cursor.execute(query, (template_name, harting_group))
            result_count = mysql_cursor.fetchone()
            updated_count = result_count['COUNT(*)']
            
            print(f"    [DEBUG] 已更新模板{template_name}下的{updated_count}个点位的hartingbox")
            
            mysql_conn.commit()
            return result['ftid']
            
        except Exception as e:
            mysql_conn.rollback()
            print(f"    [ERROR] 更新点位失败: {str(e)}")
            traceback.print_exc()
            raise Exception(f"更新点位失败: {str(e)}")
            
    except Exception as e:
        mysql_conn.rollback()
        print(f"    [ERROR] 分配点位失败: {str(e)}")
        traceback.print_exc()
        raise Exception(f"分配点位失败: {str(e)}")

def update_terminal_need(driver, terminal_id, need_type):
    """
    更新终端节点的Need属性
    """
    query = """
    MATCH (n)
    WHERE n.ftid = $terminal_id
    SET n.Need = $need_type
    """
    print(f"    [DEBUG NEO4J] 执行查询: {query}")
    print(f"    [DEBUG NEO4J] 参数: terminal_id={terminal_id}, need_type={need_type}")
    
    with driver.session() as session:
        session.run(query, terminal_id=terminal_id, need_type=need_type)

# 全局变量定义
GROUPS = ["20", "21", "22", "23"]

def get_user_group_choice():
    """
    让用户选择要处理的组 (X20-X23)
    """
    print("\n可用的组：")
    print("0. 全部")
    for i, group in enumerate(GROUPS, 1):
        print(f"{i}. X{group}")
    
    print("\n请选择要处理的组（0-4）：")
    print("0: 处理所有组")
    print("1-4: 选择对应的组")
    
    try:
        choice = input("\n请输入选择（0-4，默认0）: ").strip()
        if not choice:
            print("\n[DEBUG] 选择：处理所有组")
            return "all"
        if choice == "0":
            print("\n[DEBUG] 选择：处理所有组")
            return "all"
        elif choice.isdigit() and 1 <= int(choice) <= 4:
            group = GROUPS[int(choice)-1]
            print(f"\n[DEBUG] 选择：处理组 X{group}")
            return group
        else:
            print("\n输入无效，默认处理所有组")
            return "all"
    except KeyboardInterrupt:
        print("\n用户中断，默认处理所有组")
        return "all"

def get_neo4j_driver():
    """
    获取Neo4j数据库连接
    """
    try:
        print(f"    [DEBUG] 连接Neo4j: {NEO4J_URI}")
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        print(f"    [ERROR] Neo4j连接失败: {str(e)}")
        print(f"    [DEBUG] 尝试使用硬编码连接参数...")
        try:
            uri = "bolt://192.168.35.10:7687"
            user = "neo4j"
            password = "13701033228"
            return GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e2:
            print(f"    [ERROR] 备用连接也失败: {str(e2)}")
            raise

def query_neo4j(driver, group_number):
    """
    查询Neo4j数据库并返回终端信息
    """
    # 查询特定组的所有点
    query = """
    MATCH (n)
    WHERE n.ftid STARTS WITH $prefix
    RETURN n.ftid AS terminal_id, labels(n) AS types, properties(n) AS properties
    """
    prefix = f"=A02+K1.B1-X{group_number}"
    
    # 简化路径查询，只返回必要信息
    path_query = """
    MATCH path = (start)-[:conn*1..3]->(end)
    WHERE start.ftid = $terminal_id
    AND end.Function IS NOT NULL
    AND (end.Function STARTS WITH 'Q' OR end.Function STARTS WITH 'I')
    RETURN end.ftid as end_id,
           end.Function as end_function,
           length(path) as path_length
    ORDER BY path_length
    LIMIT 1
    """
    
    print(f"\n正在查询Neo4j数据库:")
    print(f"  - 查找前缀为 {prefix} 的终端节点...")

    with driver.session() as session:
        result = session.run(query, prefix=prefix)
        terminals = [dict(record) for record in result]
        print(f"  - 找到 {len(terminals)} 个终端节点")
        
        print("  - 开始查找终端的连接路径...")
        for terminal in terminals:
            print(f"\n  处理终端: {terminal['terminal_id']}")
            path_result = session.run(path_query, terminal_id=terminal['terminal_id'])
            record = path_result.single()
            if record:
                print(f"    ✓ 找到有效路径")
                # 简化存储的信息
                terminal['path_info'] = {
                    'end_id': record['end_id'],
                    'end_function': record['end_function'],
                    'path_length': record['path_length']
                }
                print(f"      终点: {record['end_id']}")
                print(f"      路径长度: {record['path_length']}")
    
    terminals.sort(key=lambda x: extract_sort_key(x['terminal_id']))
    return terminals

def process_terminals(driver, mysql_conn, mysql_cursor, harting_group, terminals, stats):
    """
    处理一组终端的函数
    """
    # 获取第一个终端的project_id作为默认值
    default_project_id = "HARTING"  # 默认值
    if terminals and terminals[0].get('properties', {}).get('project_id'):
        default_project_id = terminals[0]['properties']['project_id']
    # 更新组内的统计信息
    group_stats = {
        'total': len(terminals),
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # 处理每个终端
    total = len(terminals)
    processed = 0
    for terminal in terminals:
        processed += 1
        start_terminal = terminal['terminal_id']
        start_properties = terminal.get('properties', {})
        current_need = start_properties.get('Need', '未设置')
        print(f"\n[{processed}/{total}] {start_terminal} - {terminal['types']}")
        print(f"  当前Need属性: {current_need}")
        
        if 'path_info' in terminal:
            path = terminal['path_info']
            print(f"  连接路径(长度:{path['path_length']}):")
            print(f"    终点: {path['end_id']}")
            print(f"    终点功能: {path['end_function']}")
            
            need_type = 'DI' if path['end_function'].startswith('Q') else 'DO'
            print(f"    起点({start_terminal})需要的属性: Need={need_type}")

            if need_type == 'Unknown':
                print("    × 跳过处理：无法确定需要的类型")
                group_stats['skipped'] += 1
                continue

            success = False
            try:
                # 更新处理计数
                group_stats['processed'] += 1
                stats['processed'] += 1
                
                # 1. 更新Neo4j的Need属性
                update_terminal_need(driver, start_terminal, need_type)
                print(f"    √ Need属性已更新到Neo4j数据库")
                
                # 2. 处理MySQL数据库更新
                print(f"    正在更新MySQL数据库...")
                
                # 检查是否已存在对应的记录
                query = """
                    SELECT moduler, hartingbox, ftid, target_ftid
                    FROM v_simpoint
                    WHERE target_ftid = %s
                    OR ftid = %s
                """
                
                print(f"    [DEBUG SQL] 执行查询: {query}")
                print(f"    [DEBUG SQL] 参数: {(start_terminal, start_terminal)}")
                
                mysql_cursor.execute(query, (start_terminal, start_terminal))
                existing_record = mysql_cursor.fetchone()
                
                if existing_record:
                    # 如果记录已存在
                    if existing_record['target_ftid'] == start_terminal:
                        mysql_cursor.execute("""
                            UPDATE v_simpoint
                            SET hartingbox = %s
                            WHERE target_ftid = %s
                        """, (harting_group, start_terminal))
                        print(f"    √ 已更新端点对应记录的hartingbox")
                else:
                    # 获取当前终端的project_id
                    current_project_id = start_properties.get('project_id', default_project_id)
                    
                    # 如果记录不存在，尝试在现有模板中分配点位
                    template_name = find_available_template(mysql_cursor, need_type, harting_group)
                    if not template_name:
                        # 如果没有可用模板，创建新模板
                        template_name = create_new_template(mysql_cursor, mysql_conn, need_type, harting_group, current_project_id)
                    
                    if template_name:
                        # 在模板中分配点位，使用之前获取的project_id
                        assigned_ftid = assign_point(mysql_cursor, mysql_conn, template_name, start_terminal, need_type, harting_group)
                        if assigned_ftid:
                            print(f"    √ 已分配点位: {assigned_ftid}")
                            success = True
                    
                # 提交更改
                mysql_conn.commit()
                success = True
                group_stats['success'] += 1
                stats['success'] += 1
                
            except Exception as e:
                mysql_conn.rollback()
                print(f"    × 处理失败: {str(e)}")
                traceback.print_exc()
                group_stats['failed'] += 1
                stats['failed'] += 1
                
        else:
            print("  未找到有效路径")
            group_stats['skipped'] += 1
            stats['skipped'] += 1

        # 显示当前进度
        success_rate = (group_stats['success'] / total * 100) if total > 0 else 0
        print(f"\n当前进度: {processed}/{total} "
              f"(成功: {group_stats['success']}, 失败: {group_stats['failed']}, 跳过: {group_stats['skipped']})")
        print(f"组内成功率: {success_rate:.1f}%")


    # 显示组处理结果
    print(f"\n组 {harting_group} 处理完成:")
    print(f"总数: {group_stats['total']}, 成功: {group_stats['success']}, 失败: {group_stats['failed']}, 跳过: {group_stats['skipped']}")
    print(f"成功率: {(group_stats['success']/group_stats['total']*100 if group_stats['total'] > 0 else 0):.1f}%")

def main():
    """
    主函数 - 自动处理所有节点，无需手动确认
    """
    print("正在连接数据库...")
    driver = None
    mysql_conn = None
    stats = {
        'total': 0,
        'processed': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0
    }
    try:
        # 连接数据库
        driver = get_neo4j_driver()
        mysql_conn = get_mysql_connection()
        mysql_cursor = mysql_conn.cursor()
        
        # 初始化数据库表
        initialize_database(mysql_cursor, mysql_conn)
        
        # 让用户选择要处理的组
        selected_group = get_user_group_choice()
        if selected_group == "all":
            groups_to_process = GROUPS
            print("\n处理所有组: X20, X21, X22, X23")
        else:
            groups_to_process = [selected_group]
            print(f"\n处理组: X{selected_group}")

        # 计算总终端数并显示
        for group in groups_to_process:
            harting_group = f"X{group}"
            group_terminals = query_neo4j(driver, group)
            group_count = len(group_terminals)
            stats['total'] += group_count
            print(f"\n查询结果(组{harting_group}，按前缀和数字顺序排序)：")
            print(f"组{harting_group}发现 {group_count} 个终端需要处理")

        print(f"\n总共找到 {stats['total']} 个终端需要处理")

        # 处理所有组的终端
        for group in groups_to_process:
            harting_group = f"X{group}"
            print(f"\n开始处理组 {harting_group} 中的终端...")
            
            # 查询并处理该组的终端
            group_terminals = query_neo4j(driver, group)
            process_terminals(driver, mysql_conn, mysql_cursor, harting_group, group_terminals, stats)

            # 显示该组处理结果
            print(f"\n组 {harting_group} 处理完成")
    
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        print("建议: 1. 检查数据库连接 2. 减少查询范围 3. 增加数据库内存配置")
    finally:
        # 显示最终统计信息
        
        print("\n处理完成！最终统计:")
        print(f"总计处理: {stats['total']} 个终端")
        print(f"成功: {stats['success']}")
        print(f"失败: {stats['failed']}")
        print(f"跳过: {stats['skipped']}")
        if stats['total'] > 0:
            success_rate = (stats['success'] / stats['total'] * 100)
            print(f"成功率: {success_rate:.1f}%")
        
        # 关闭数据库连接
        if driver:
            driver.close()
        if mysql_conn:
            mysql_conn.close()
        
        # 根据处理结果返回适当的退出码
        if stats['failed'] > 0:
            print("\n警告：部分记录处理失败，请检查日志并重试失败的记录。")
            sys.exit(1)
        elif stats['success'] == 0:
            print("\n警告：没有成功处理任何记录。")
            sys.exit(2)

if __name__ == "__main__":
    main()