# -*- coding: utf-8 -*-
from neo4j import GraphDatabase
import sys
import traceback
import msvcrt
import time
import re
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 可用的Harting盒组
GROUPS = ["20", "21", "22", "23"]

def extract_number(ftid):
    """
    从ftid中提取数字部分用于排序
    例如从'=lb_test+Sim-EDB2:1'提取出'2.1'
    """
    match = re.search(r'EDB(\d+):(\d+)', ftid)
    if match:
        board, point = match.groups()
        return float(f"{board}.{point}")
    return 0

def pause_with_prompt():
    """
    暂停执行并等待用户按键
    """
    print("\n按任意键继续...")
    msvcrt.getch()

def get_neo4j_driver():
    """
    获取Neo4j数据库连接
    """
    try:
        print(f"    [DEBUG] 连接Neo4j: {NEO4J_URI}")
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        print(f"    [ERROR] Neo4j连接失败: {str(e)}")
        raise

def wait_for_input(timeout=5):
    """
    等待用户输入，超时返回默认值
    """
    print(f"\n请在{timeout}秒内输入选择（0-4）...")
    print("（超时将默认选择0，查询所有组）")
    
    start_time = time.time()
    input_str = ''
    while True:
        if msvcrt.kbhit():
            char = msvcrt.getch().decode()
            if char == '\r':  # Enter key
                break
            if char.isdigit():
                input_str = char
                print(char, end='', flush=True)
        
        if time.time() - start_time > timeout:
            print("\n等待输入超时，默认选择0")
            return "0"
        
        time.sleep(0.1)
    
    return input_str

def get_user_group_choice():
    """
    让用户选择要查询的组 (X20-X23)
    """
    print("\n可用的组：")
    print("0. 全部")
    for i, group in enumerate(GROUPS, 1):
        print(f"{i}. X{group}")
    
    print("\n请选择要查询的组（0-4）：")
    print("0: 查询所有组")
    print("1-4: 选择对应的组")
    
    try:
        choice = wait_for_input(5).strip()
        if not choice or choice == "0":
            print("\n[DEBUG] 选择：查询所有组")
            return "all"
        elif choice.isdigit() and 1 <= int(choice) <= 4:
            group = GROUPS[int(choice)-1]
            print(f"\n[DEBUG] 选择：查询组 X{group}")
            return group
        else:
            print("\n输入无效，默认查询所有组")
            return "all"
    except Exception as e:
        print(f"\n输入处理出错: {str(e)}")
        print("默认查询所有组")
        return "all"

def verify_nodes_and_relationships(driver, group_number):
    """
    验证节点和关系的存在性
    """
    verify_queries = [
        ("""
        MATCH (s:Sim_terminal)
        WHERE s.hartingbox = $harting_box
        RETURN count(s) as count
        """, "Sim_terminal节点"),
        
        ("""
        MATCH (v:V_terminal)
        WHERE v.ftid CONTAINS $group_prefix
        RETURN count(v) as count
        """, "V_terminal节点"),
        
        ("""
        MATCH (s:Sim_terminal)-[r:Sim_conn]->()
        WHERE s.hartingbox = $harting_box
        RETURN count(r) as count
        """, "Sim_conn关系"),
        
        ("""
        MATCH (s:Sim_terminal)-[:Sim_conn]->(v:V_terminal)
        WHERE s.hartingbox = $harting_box
        AND v.ftid CONTAINS $group_prefix
        RETURN COUNT(*) as count
        """, "Sim_terminal到V_terminal连接")
    ]
    
    harting_box = f"X{group_number}"
    group_prefix = f"X{group_number}"
    
    print(f"\n验证 {harting_box} 组的节点和关系...")
    
    try:
        with driver.session() as session:
            for query, description in verify_queries:
                result = session.run(query, 
                                   harting_box=harting_box,
                                   group_prefix=group_prefix)
                count = result.single()["count"]
                print(f"找到 {count} 个{description}")
    except Exception as e:
        print(f"验证过程中发生错误: {str(e)}")
        traceback.print_exc()

def query_direct_connections(driver, harting_box, group_prefix):
    """
    查询直连的V端子
    """
    query = """
    MATCH (start:Sim_terminal)-[r:Sim_conn]->(v:V_terminal)
    WHERE start.hartingbox = $harting_box
    AND v.ftid CONTAINS $group_prefix
    RETURN 
        start.ftid as start_id,
        start.point_type as start_type,
        v.ftid as v_terminal_id,
        v.Function as v_function,
        1 as path_length,
        [start.ftid, v.ftid] as path_nodes,
        true as is_direct
    """
    with driver.session() as session:
        result = session.run(query, harting_box=harting_box, group_prefix=group_prefix)
        return [dict(record) for record in result]

def query_paths_for_group(driver, group_number):
    """
    查询指定组的所有路径
    """
    # 首先验证节点和关系
    verify_nodes_and_relationships(driver, group_number)
    
    harting_box = f"X{group_number}"
    group_prefix = f"X{group_number}"
    
    print(f"\n开始查询 {harting_box} 组的路径...")
    print("  - 从Sim_terminal开始")
    print("  - 查找直连和路由连接")
    
    try:
        # 获取所有直连
        paths = query_direct_connections(driver, harting_box, group_prefix)
        
        if not paths:
            print(f"  未找到 {harting_box} 组的路径")
            return
        
        # 对路径按起点的自然顺序排序
        paths.sort(key=lambda x: extract_number(x['start_id']))
        
        # 计算当前组中唯一起点的数量
        unique_starts = len(set(path['start_id'] for path in paths))
        print(f"\n在 {harting_box} 组找到 {unique_starts} 个起点")
        
        # 用于跟踪当前处理的起点
        current_start = None
        current_start_count = 0
        
        # 遍历所有路径
        for path in paths:
            # 如果是新的起点
            if current_start != path['start_id']:
                # 如果不是第一个起点，在新起点前暂停
                if current_start is not None:
                    pause_with_prompt()
                
                current_start = path['start_id']
                current_start_count += 1
                print(f"\n{'-'*80}")
                print(f"正在处理 {harting_box} 组的第 {current_start_count}/{unique_starts} 个端点")
                print(f"{'-'*80}")
                print(f"起点: {current_start}")
                print(f"类型: {path['start_type']}\n")
            
            # 打印路径信息
            print(f"  路径 (单步直连):")
            print(f"  - V端子: {path['v_terminal_id']} (功能: {path['v_function'] or '无'})")
            
            # 打印完整路径序列
            print("\n  路径序列:")
            for i, node_id in enumerate(path['path_nodes']):
                print(f"    {i+1}. {node_id}")
                if i < len(path['path_nodes']) - 1:
                    print(f"       ↓ [Sim_conn]")
            print()
        
        # 在最后一个端点处理完后也暂停
        pause_with_prompt()
        
    except Exception as e:
        print(f"查询过程中发生错误: {str(e)}")
        traceback.print_exc()

def main():
    """
    主函数 - 查询所有节点的路径
    """
    print("开始Neo4j路径查询...")
    driver = None
    
    try:
        # 连接数据库
        driver = get_neo4j_driver()
        print("Neo4j连接成功")
        
        # 让用户选择要查询的组
        selected_group = get_user_group_choice()
        if selected_group == "all":
            groups_to_process = GROUPS
            print("\n将查询所有组: X20, X21, X22, X23")
        else:
            groups_to_process = [selected_group]
            print(f"\n将查询组: X{selected_group}")
        
        # 查询每个组的路径
        for group in groups_to_process:
            print(f"\n{'#'*80}")
            print(f"开始查询组 X{group} 的路径...")
            query_paths_for_group(driver, group)
            print(f"\n完成组 X{group} 的查询")
            print('#'*80)
    
    except Exception as e:
        print(f"程序执行过程中发生错误: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        if driver:
            driver.close()
            print("\n已关闭Neo4j连接")

if __name__ == "__main__":
    main()