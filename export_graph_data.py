import os
from neo4j import GraphDatabase, exceptions
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_CONFIG
import csv
import sys

def export_graph_data():
    try:
        print("STEP 1: 获取当前工作路径", flush=True)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"[DEBUG] 当前目录: {current_dir}", flush=True)
        
        print("\nSTEP 2: 创建输出目录", flush=True)
        output_dir = os.path.join(current_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        print(f"[DEBUG] 输出目录创建或已存在: {output_dir}", flush=True)
        
        print("\nSTEP 3: 设置输出文件路径", flush=True)
        output_file = os.path.join(output_dir, 'graph_data.csv')
        print(f"[DEBUG] 输出文件将写入: {output_file}", flush=True)
        
        print("\nSTEP 4: 连接 Neo4j 数据库...", flush=True)
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), **NEO4J_CONFIG)
        print("[DEBUG] 驱动创建成功", flush=True)
        
        print("\nSTEP 5: 测试数据库连接", flush=True)
        with driver.session(database="neo4j") as session:
            test_result = session.run("MATCH (n) RETURN count(n) as count")
            count = test_result.single()['count']
            print(f"[DEBUG] 连接测试成功，总节点数: {count}", flush=True)
        
        print("\nSTEP 6: 执行数据查询", flush=True)
        with driver.session(database="neo4j") as session:
            query = """
                MATCH (v:Vertex)-[r:conn]->(w:Vertex) 
                RETURN v.name as source_name, 
                       v.Location as source_location,
                       v.type as source_type,
                       w.name as target_name,
                       w.Location as target_location,
                       w.type as target_type,
                       r.wire_number as connection_number,
                       r.color as wire_color
                ORDER BY r.wire_number ASC
            """
            print(f"[DEBUG] 查询语句:\n{query}", flush=True)
            result = session.run(query)
            
            print("STEP 7: 获取并转换查询结果", flush=True)
            records = list(result)
            print(f"[DEBUG] 查询返回记录数: {len(records)}", flush=True)
            if not records:
                print("警告: 查询结果为空，未找到任何连接关系", flush=True)
                return
        
        print("\nSTEP 8: 写入 CSV 文件", flush=True)
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 调整表头：将 connection_number 放在第一列
            headers = ['connection_number', 'source_name', 'source_location', 'source_type',
                       'target_name', 'target_location', 'target_type', 'wire_color']
            writer.writerow(headers)
            print(f"[DEBUG] 表头写入成功: {headers}", flush=True)
            
            records_written = 0
            for record in records:
                row = [
                    str(record['connection_number'] or ''),
                    str(record['source_name'] or ''),
                    str(record['source_location'] or ''),
                    str(record['source_type'] or ''),
                    str(record['target_name'] or ''),
                    str(record['target_location'] or ''),
                    str(record['target_type'] or ''),
                    str(record['wire_color'] or '')
                ]
                writer.writerow(row)
                records_written += 1
                if records_written % 100 == 0:
                    print(f"[DEBUG] 已写入 {records_written} 条记录", flush=True)
                    
        print("\nSTEP 9*: 验证 CSV 文件是否创建成功", flush=True)
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"[DEBUG] 导出成功!", flush=True)
            print(f"- 文件位置: {output_file}", flush=True)
            print(f"- 文件大小: {file_size} 字节", flush=True)
            print(f"- 记录数量: {records_written} 条", flush=True)
            print(f"[DEBUG] 输出目录内容: {os.listdir(output_dir)}", flush=True)
        else:
            print("错误: 文件未能成功创建!", flush=True)
            
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
    finally:
        if 'driver' in locals():
            driver.close()
            print("\nSTEP 10: 数据库连接已关闭", flush=True)

def test_connection():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), **NEO4J_CONFIG)
        with driver.session(database="neo4j") as session:
            result = session.run("RETURN 'Connected' as message")
            message = result.single()['message']
            print(f"连接成功：{message}")
    except Exception as e:
        print(f"连接失败: {e}")
    finally:
        if 'driver' in locals():
            driver.close()
            print("数据库连接已关闭")

if __name__ == "__main__":
    test_connection()
    export_graph_data()  # 确保调用export_graph_data以显示输出
