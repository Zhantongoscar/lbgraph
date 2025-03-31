from neo4j import GraphDatabase
import re
import pymysql
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import sys

# MySQL数据库连接
def get_mysql_connection():
    """
    获取MySQL数据库连接
    """
    try:
        return pymysql.connect(**MYSQL_CONFIG)
    except Exception as e:
        print(f"MySQL连接失败: {str(e)}")
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
    if 'Function' in properties:
        function = properties['Function']
        # Q开头通常表示数字输出(DO)
        if function.startswith('Q'):
            return 'DO'
        # I开头通常表示数字输入(DI)
        elif function.startswith('I'):
            return 'DI'
    # 保持原有类型
    return properties.get('Type', 'Unknown')

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
    FROM simpoint
    WHERE moduler LIKE %s
    """
    mysql_cursor.execute(query, (len(template_prefix) + 1, f"{template_prefix}%"))
    result = mysql_cursor.fetchone()[0]
    return 1 if result is None else result + 1

def check_template_count(mysql_cursor, template_prefix):
    """
    检查模板数量是否达到限制
    """
    query = """
    SELECT COUNT(DISTINCT moduler)
    FROM simpoint
    WHERE moduler LIKE %s
    """
    mysql_cursor.execute(query, (f"{template_prefix}%",))
    count = mysql_cursor.fetchone()[0]
    return count

def find_available_template(mysql_cursor, need_type, harting_group):
    """
    查找可用的模板
    """
    template_prefix = 'EDB' if need_type == 'DI' else 'EBD'
    query = """
    SELECT DISTINCT s1.moduler, COUNT(s2.id) as available_points
    FROM simpoint s1
    LEFT JOIN simpoint s2 ON s1.moduler = s2.moduler
        AND s2.target_ftid IS NULL
        AND s2.point_type = %s
    WHERE s1.moduler LIKE %s
    AND (s1.hartingbox = %s OR s1.hartingbox IS NULL)
    GROUP BY s1.moduler
    HAVING available_points > 0
    ORDER BY s1.moduler ASC, available_points DESC
    LIMIT 1
    """
    point_type = 'DI' if need_type == 'DI' else 'DO'
    mysql_cursor.execute(query, (point_type, f"{template_prefix}%", harting_group))
    result = mysql_cursor.fetchone()
    
    if result:
        print(f"    [DEBUG] 找到可用模板: {result[0]}，剩余点位数: {result[1]}")
        return result[0]
    else:
        print(f"    [DEBUG] 未找到可用的{template_prefix}模板")
        return None

def create_new_template(mysql_cursor, mysql_conn, need_type, harting_group):
    """
    创建新的模板
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
        mysql_cursor.execute(
            "SELECT id FROM device_types WHERE type_name = %s",
            (template_prefix,)
        )
        type_id = mysql_cursor.fetchone()
        if not type_id:
            raise Exception(f"未找到{template_prefix}类型的设备配置")
        
        # 获取点位配置
        mysql_cursor.execute("""
            SELECT point_index, point_type, sim_type, mode
            FROM device_type_points
            WHERE device_type_id = %s
        """, (type_id[0],))
        points = mysql_cursor.fetchall()
        
        # 创建新的模板实例
        for point in points:
            mysql_cursor.execute("""
                INSERT INTO simpoint
                (ftid, project_name, moduler, device_name,
                 point_type, point_index, sim_type, mode, hartingbox)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                f"{template_name}_{point[0]}",
                "HARTING",
                template_name,
                template_name,
                point[1],
                point[0],
                point[2],
                point[3],
                harting_group
            ))
        
        mysql_conn.commit()
        return template_name
        
    except Exception as e:
        mysql_conn.rollback()
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
        FROM simpoint
        WHERE moduler = %s
        AND target_ftid IS NULL
        AND point_type = %s
        ORDER BY ftid ASC
        LIMIT 1
        """
        point_type = 'DI' if need_type == 'DI' else 'DO'
        mysql_cursor.execute(query, (template_name, point_type))
        result = mysql_cursor.fetchone()
        
        if not result:
            raise Exception(f"在模板{template_name}中未找到可用的{point_type}点位")
            
        print(f"    [DEBUG] 找到可用点位: id={result[0]}, ftid={result[1]}, type={result[2]}")
        
        # 检查点位类型是否匹配
        if result[2] != point_type:
            raise Exception(f"点位类型不匹配: 需要{point_type}，但找到{result[2]}")
        
        try:
            # 更新点位和hartingbox
            mysql_cursor.execute("""
                UPDATE simpoint
                SET target_ftid = %s,
                    hartingbox = %s
                WHERE id = %s
            """, (target_ftid, harting_group, result[0]))
            print(f"    [DEBUG] 已更新点位 id={result[0]} 的target_ftid={target_ftid}")
            
            # 更新同一模板下所有点位的hartingbox
            mysql_cursor.execute("""
                UPDATE simpoint
                SET hartingbox = %s
                WHERE moduler = %s
                AND hartingbox IS NULL
            """, (harting_group, template_name))
            
            # 检查更新结果
            mysql_cursor.execute("""
                SELECT COUNT(*)
                FROM simpoint
                WHERE moduler = %s AND hartingbox = %s
            """, (template_name, harting_group))
            updated_count = mysql_cursor.fetchone()[0]
            print(f"    [DEBUG] 已更新模板{template_name}下的{updated_count}个点位的hartingbox")
            
            mysql_conn.commit()
            return result[1]
            
        except Exception as e:
            mysql_conn.rollback()
            raise Exception(f"更新点位失败: {str(e)}")
            
    except Exception as e:
        mysql_conn.rollback()
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
    with driver.session() as session:
        session.run(query, terminal_id=terminal_id, need_type=need_type)

def get_user_group_choice():
    """
    让用户选择要处理的组 (X20-X23)
    """
    groups = ["20", "21", "22", "23"]
    print("\n可用的组：")
    for i, group in enumerate(groups, 1):
        print(f"{i}. X{group}")
    
    while True:
        try:
            choice = input("\n请选择要处理的组编号 (1-4): ")
            index = int(choice) - 1
            if 0 <= index < len(groups):
                return groups[index]
            else:
                print("无效的选择，请输入1-4")
        except ValueError:
            print("请输入有效的数字")

def get_neo4j_driver():
    """
    获取Neo4j数据库连接
    """
    uri = "bolt://192.168.35.10:7687"
    user = "neo4j"
    password = "13701033228"
    return GraphDatabase.driver(uri, auth=(user, password))

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
    
    # 修改路径查询，排除回头路径和更准确地处理类型
    path_query = """
    MATCH path = (start)-[:conn*1..5]->(end)
    WHERE start.ftid = $terminal_id
    AND end.ftid IS NOT NULL
    AND start <> end
    AND ALL(n IN nodes(path) WHERE single(m IN nodes(path) WHERE m = n))
    AND NONE(node IN nodes(path) WHERE node.Type = 'PE')
    RETURN path,
           length(path) AS pathLength,
           end,
           properties(end) AS end_properties,
           end.Function as end_function
    ORDER BY pathLength DESC
    LIMIT 1
    """
    
    with driver.session() as session:
        result = session.run(query, prefix=prefix)
        terminals = [dict(record) for record in result]
        
        batch_size = 100
        for i in range(0, len(terminals), batch_size):
            batch = terminals[i:i + batch_size]
            for terminal in batch:
                path_result = session.run(path_query, terminal_id=terminal['terminal_id'])
                record = path_result.single()
                if record:
                    path = record['path']
                    path_nodes = [node for node in path.nodes if node['ftid'] is not None]
                    end_node = record['end']
                    end_props = record['end_properties']
                    terminal['longest_path'] = {
                        'path': [node['ftid'] for node in path_nodes],
                        'path_length': record['pathLength'],
                        'end_node': end_node['ftid'],
                        'end_properties': end_props
                    }
    
    terminals.sort(key=lambda x: extract_sort_key(x['terminal_id']))
    return terminals

def main():
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
        
        # 让用户选择要处理的组
        selected_group = get_user_group_choice()
        harting_group = f"X{selected_group}"
        print(f"\n选择了组: {harting_group}")
        
        # 查询选定组的终端
        terminals = query_neo4j(driver, selected_group)
        print(f"\n查询结果(组{harting_group}，按前缀和数字顺序排序)：")
        total_terminals = len(terminals)
        stats['total'] = total_terminals
        print(f"共找到 {total_terminals} 个终端需要处理")
        
        
        for idx, terminal in enumerate(terminals, 1):
            start_terminal = terminal['terminal_id']
            start_properties = terminal.get('properties', {})
            current_need = start_properties.get('Need', '未设置')
            print(f"\n[{idx}/{total_terminals}] {start_terminal} - {terminal['types']}")
            print(f"  当前Need属性: {current_need}")
            
            if 'longest_path' in terminal:
                path = terminal['longest_path']
                print(f"  最长非回头路径(长度:{path['path_length']}):")
                print(f"    路径: {' -> '.join(path['path'])}")
                print(f"    终点: {path['end_node']}")
                end_type = determine_node_type(path['end_properties'])
                print(f"    终点属性: Type={end_type}")
                print(f"    Function: {path['end_properties'].get('Function', '')}")
                need_type = determine_need_type(end_type)
                print(f"    起点({start_terminal})需要的属性: Need={need_type}")

                if need_type == 'Unknown':
                    print("    × 跳过处理：无法确定需要的类型")
                    stats['skipped'] += 1
                    continue

                stats['processed'] += 1
                success = False
                try:
                    # 1. 更新Neo4j的Need属性
                    update_terminal_need(driver, start_terminal, need_type)
                    print(f"    √ Need属性已更新到Neo4j数据库")
                    
                    # 2. 处理MySQL数据库更新
                    print(f"    正在更新MySQL数据库...")
                    
                    # 检查是否已存在对应的记录
                    mysql_cursor.execute("""
                        SELECT moduler, hartingbox, ftid
                        FROM simpoint
                        WHERE target_ftid = %s
                        OR ftid = %s
                    """, (start_terminal, start_terminal))
                    existing_record = mysql_cursor.fetchone()
                    
                    if existing_record:
                        # 如果记录已存在
                        if existing_record['target_ftid'] == start_terminal:
                            # 如果是作为目标存在，更新hartingbox
                            mysql_cursor.execute("""
                                UPDATE simpoint
                                SET hartingbox = %s
                                WHERE target_ftid = %s
                            """, (harting_group, start_terminal))
                            mysql_conn.commit()
                            print(f"    √ 已更新现有记录的hartingbox为{harting_group}")
                        else:
                            print(f"    × 跳过处理：ftid={start_terminal}已经存在于simpoint表中")
                    else:
                        # 查找可用的模板
                        template_name = find_available_template(mysql_cursor, need_type, harting_group)
                        
                        if template_name:
                            # 使用现有模板
                            try:
                                point_ftid = assign_point(mysql_cursor, mysql_conn,
                                                      template_name, start_terminal, need_type, harting_group)
                                print(f"    √ 已分配到模板{template_name}的点位{point_ftid}")
                            except Exception as e:
                                print(f"    × 点位分配失败: {str(e)}")
                                # 如果分配失败，尝试创建新模板
                                try:
                                    new_template = create_new_template(mysql_cursor, mysql_conn,
                                                                   need_type, harting_group)
                                    point_ftid = assign_point(mysql_cursor, mysql_conn,
                                                          new_template, start_terminal, need_type, harting_group)
                                    print(f"    √ 已创建新模板{new_template}并分配点位{point_ftid}")
                                except Exception as e2:
                                    print(f"    × 创建新模板失败: {str(e2)}")
                        else:
                            # 创建新模板
                            try:
                                new_template = create_new_template(mysql_cursor, mysql_conn,
                                                               need_type, harting_group)
                                point_ftid = assign_point(mysql_cursor, mysql_conn,
                                                      new_template, start_terminal, need_type, harting_group)
                                print(f"    √ 已创建新模板{new_template}并分配点位{point_ftid}")
                            except Exception as e:
                                print(f"    × 创建新模板失败: {str(e)}")
                                stats['failed'] += 1
                
                except Exception as e:
                    print(f"    × 数据库更新失败: {str(e)}")
                    stats['failed'] += 1
                else:
                    stats['success'] += 1
                    success = True
            else:
                print("  未找到有效路径")
                stats['skipped'] += 1
            
            # 显示当前进度
            success_rate = (stats['success'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
            print(f"\n当前进度: {stats['processed']}/{stats['total']} "
                  f"(成功: {stats['success']}, 失败: {stats['failed']}, 跳过: {stats['skipped']})")
            print(f"成功率: {success_rate:.1f}%")
            
            if idx < total_terminals:
                try:
                    input("\n按Enter键继续查看下一个节点...")
                    print()
                except KeyboardInterrupt:
                    print("\n用户中断查询")
                    print("\n最终统计:")
                    print(f"总计处理: {stats['processed']}/{stats['total']}")
                    print(f"成功: {stats['success']}")
                    print(f"失败: {stats['failed']}")
                    print(f"跳过: {stats['skipped']}")
                    print(f"成功率: {success_rate:.1f}%")
                    break
    
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")
        print("建议: 1. 检查数据库连接 2. 减少查询范围 3. 增加数据库内存配置")
    finally:
        # 显示最终统计信息
        if stats['processed'] > 0:
            print("\n处理完成！最终统计:")
            print(f"总计处理: {stats['processed']}/{stats['total']}")
            print(f"成功: {stats['success']}")
            print(f"失败: {stats['failed']}")
            print(f"跳过: {stats['skipped']}")
            success_rate = (stats['success'] / stats['processed'] * 100)
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