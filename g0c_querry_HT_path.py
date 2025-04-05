# -*- coding: utf-8 -*-
from neo4j import GraphDatabase
import sys
import traceback
import msvcrt
import time
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 可用的Harting盒组
GROUPS = ["20", "21", "22", "23"]

def pause_with_prompt():
    """暂停执行并等待用户按键"""
    print("\n按任意键继续...")
    msvcrt.getch()

def get_neo4j_driver():
    """获取Neo4j数据库连接"""
    try:
        print(f"    [DEBUG] 连接Neo4j: {NEO4J_URI}")
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        print(f"    [ERROR] Neo4j连接失败: {str(e)}")
        raise

def wait_for_input(timeout=5):
    """等待用户输入，超时返回默认值"""
    print(f"\n请在{timeout}秒内输入选择（0-4）...")
    print("（超时将默认选择0，查询所有组）")
    
    start_time = time.time()
    input_str = ''
    while True:
        if msvcrt.kbhit():
            char = msvcrt.getch().decode()
            if char == '\r':
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
    """让用户选择要查询的组 (X20-X23)"""
    print("\n可用的组：")
    print("0. 全部")
    for i, group in enumerate(GROUPS, 1):
        print(f"{i}. X{group}")
    
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

def query_paths_for_group(driver, group_number):
    """遍历查询指定组的所有路径"""
    harting_box = f"X{group_number}"
    print(f"\n开始查询 {harting_box} 组的路径...")

    # 查询路径的Cypher语句
    path_query = """
    MATCH path = (s:Sim_terminal)-[:Sim_conn]->(v:V_terminal)-[:conn*0..5]->(end)
    WHERE s.hartingbox = $harting_box
    RETURN
        s.ftid as start_id,
        s.point_type as start_type,
        v.ftid as v_terminal_id,
        v.Function as v_function,
        [node in nodes(path) | node.ftid] as path_nodes,
        [rel in relationships(path) | type(rel)] as relationships
    ORDER BY s.ftid
    """

    try:
        with driver.session() as session:
            result = session.run(path_query, harting_box=harting_box)
            paths = list(result)
            
            if not paths:
                print(f"  未找到 {harting_box} 组的路径")
                return

            unique_starts = set()
            current_start = None

            for record in paths:
                if record["start_id"] not in unique_starts:
                    # 如果不是第一个起点，暂停
                    if current_start is not None:
                        pause_with_prompt()
                    
                    current_start = record["start_id"]
                    unique_starts.add(current_start)
                    
                    print(f"\n{'-'*80}")
                    print(f"正在处理 {harting_box} 组的第 {len(unique_starts)}/{len(unique_starts)} 个端点")
                    print(f"{'-'*80}")
                    print(f"起点: {current_start}")
                    print(f"类型: {record['start_type']}\n")

                # 打印路径信息
                print(f"  路径:")
                print(f"  - V端子: {record['v_terminal_id']} (功能: {record['v_function'] or '无'})")

                # 打印路径序列
                print("\n  路径序列:")
                for i, (node_id, rel_type) in enumerate(zip(record["path_nodes"], 
                                                          record["relationships"] + ["(终点)"])):
                    print(f"    {i+1}. {node_id}")
                    if rel_type != "(终点)":
                        print(f"       ↓ [{rel_type}]")
                print()

            # 在最后一个端点处理完后暂停
            pause_with_prompt()

    except Exception as e:
        print(f"查询过程中发生错误: {str(e)}")
        traceback.print_exc()

def verify_data(driver, group_number):
    """验证数据存在性"""
    harting_box = f"X{group_number}"
    verify_queries = [
        ("""
        MATCH (s:Sim_terminal)
        WHERE s.hartingbox = $harting_box
        RETURN count(s) as count
        """, "Sim_terminal节点"),
        
        ("""
        MATCH (s:Sim_terminal)-[r:Sim_conn]->()
        WHERE s.hartingbox = $harting_box
        RETURN count(r) as count
        """, "Sim_conn关系"),
        
        ("""
        MATCH ()-[r:conn]->()
        RETURN count(r) as count
        """, "conn关系")
    ]
    
    print(f"\n验证 {harting_box} 组的节点和关系...")
    try:
        with driver.session() as session:
            for query, description in verify_queries:
                result = session.run(query, harting_box=harting_box)
                count = result.single()["count"]
                print(f"找到 {count} 个{description}")
    except Exception as e:
        print(f"验证过程中发生错误: {str(e)}")
        traceback.print_exc()

def main():
    """主函数"""
    print("开始Neo4j路径查询...")
    driver = None
    
    try:
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
            verify_data(driver, group)
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