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
        # 如果文件已存在，尝试删除，避免权限问题
        if os.path.exists(output_file):
            try:
                # 尝试修改文件权限后删除
                os.chmod(output_file, 0o666)
                os.remove(output_file)
                print(f"[DEBUG] 已删除存在的文件: {output_file}", flush=True)
            except Exception as e:
                print(f"[DEBUG] 无法删除文件 {output_file}, 错误: {e}", flush=True)
                # 这里可以选择退出或继续，当前选择退出
                raise
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            # 调整表头：将 connection_number 放在第一列
            headers = ['connection_number', 'source_name', 'source_location', 'source_type',
                       'target_name', 'target_location', 'target_type', 'wire_color']
            writer.writerow(headers)
            print(f"[DEBUG] 表头写入成功: {headers}", flush=True)
            
            # 构建字典过滤重复 connection_number
            unique_records = {}
            for record in records:
                try:
                    conn_num = int(record['connection_number'])
                except Exception as e:
                    print(f"[DEBUG] 无法转换 connection_number: {record['connection_number']}, 跳过", flush=True)
                    continue
                
                if conn_num not in unique_records:
                    unique_records[conn_num] = record

            def fix_string_for_csv(value):
                # Always prefix with a single quote
                val = str(value)
                return val if val.startswith("'") else "'" + val

            records_written = 0
            for conn_num, record in sorted(unique_records.items()):
                row = [
                    conn_num,
                    fix_string_for_csv(record['source_name'] or ''),
                    str(record['source_location'] or ''),
                    str(record['source_type'] or ''),
                    fix_string_for_csv(record['target_name'] or ''),
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

        # 新增Excel导出处理：将生成的CSV转换为Excel格式，并确保source_name和target_name为文本格式
        try:
            import pandas as pd
            excel_output = os.path.join(output_dir, 'graph_data.xlsx')
            df = pd.read_csv(output_file)
            df['connection_number'] = df['connection_number'].astype(int)
            
            with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
                workbook = writer.book
                worksheet = writer.sheets['Sheet1'] = workbook.add_worksheet()
                
                text_format = workbook.add_format({'num_format': '@'})
                
                # 步骤1：先整列设置文本格式，并写空值
                worksheet.set_column('B:B', 30, text_format)  # source_name列
                worksheet.set_column('E:E', 30, text_format)  # target_name列
                for row_idx in range(1, len(df) + 1):
                    worksheet.write_string(row_idx, 1, '', text_format)  # 先空写source_name
                    worksheet.write_string(row_idx, 4, '', text_format)  # 先空写target_name
                
                # 写表头
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value)
                
                # 步骤2：再写入真实值，加一个空格
                for row_num, row in enumerate(df.values):
                    for col_num, value in enumerate(row):
                        if col_num in [1, 4]:  # source_name / target_name
                            val_str = str(value)
                            # 如果没有以单引号开头，就加单引号+空格
                            if not val_str.startswith("'"):
                                val_str = "' " + val_str
                            worksheet.write_string(row_num + 1, col_num, val_str, text_format)
                        else:
                            worksheet.write(row_num + 1, col_num, value)
                            
            process_excel_content(excel_output)

        except ImportError:
            print("[DEBUG] pandas模块未安装，跳过生成Excel文件", flush=True)

        finally:
            # 删除临时文件
            try:
                os.remove(temp_csv_path)
                print(f"[DEBUG] 临时文件已删除: {temp_csv_path}", flush=True)
            except Exception as e:
                print(f"[DEBUG] 无法删除临时文件 {temp_csv_path}, 错误: {e}", flush=True)
            
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
    finally:
        if 'driver' in locals():
            driver.close()
            print("\nSTEP 10: 数据库连接已关闭", flush=True)

def process_excel_content(excel_path):
    # 使用 openpyxl 处理Excel内容，对source_name和target_name列去除多余空格
    try:
        import openpyxl
    except ImportError:
        print("[DEBUG] openpyxl模块未安装，无法处理Excel内容", flush=True)
        return
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active
    # 假设第一行为表头，source_name 为第2列，target_name 为第5列
    for row in ws.iter_rows(min_row=2):
        for cell in (row[1], row[4]):
            if isinstance(cell.value, str):
                cell.value = cell.value.strip()
    wb.save(excel_path)
    print(f"[DEBUG] 处理Excel内容完成: {excel_path}", flush=True)

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