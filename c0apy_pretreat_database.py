import os
import csv
import mysql.connector
import tkinter as tk
from tkinter import filedialog
from config import MYSQL_CONFIG

class CSVRow:
    """CSV行数据结构"""
    def __init__(self):
        self.cnumber = ""     # 连续编号
        self.color = ""       # 颜色信息
        
        # 源端数据
        self.s_raw = ""       # 原始源数据
        self.s_ftid = ""      # 源完整标识符
        self.s_function = ""  # 源功能
        self.s_location = ""  # 源位置
        self.s_device = ""    # 源设备
        self.s_terminal = ""  # 源端子

        # 目标端数据
        self.t_raw = ""       # 原始目标数据
        self.t_ftid = ""      # 目标完整标识符
        self.t_function = ""  # 目标功能
        self.t_location = ""  # 目标位置
        self.t_device = ""    # 目标设备
        self.t_terminal = ""  # 目标端子

def parse_ftid(raw):
    """解析FTID并提取各个部分"""
    result = {
        'ftid': raw,
        'function': "",
        'location': "",
        'device': "",
        'terminal': ""
    }
    
    # 如果字符串包含 "-W" 并且有两个冒号
    if "-W" in raw:
        parts = raw.split(":")
        if len(parts) >= 2:
            result['ftid'] = ":".join(parts[:2])
    
    # 查找等号位置（功能分隔符）
    equal_pos = result['ftid'].find("=")
    if equal_pos != -1:
        # 提取功能部分
        plus_pos = result['ftid'].find("+", equal_pos)
        if plus_pos != -1:
            result['function'] = result['ftid'][equal_pos+1:plus_pos]
            
            # 提取位置和设备部分
            minus_pos = result['ftid'].find("-", plus_pos)
            if minus_pos != -1:
                result['location'] = result['ftid'][plus_pos+1:minus_pos]
                
                # 处理设备和端子部分
                device_part = result['ftid'][minus_pos+1:]
                colon_pos = device_part.find(":")
                if colon_pos != -1:
                    result['device'] = device_part[:colon_pos]
                    result['terminal'] = device_part[colon_pos+1:]
                else:
                    result['device'] = device_part
    
    return result

class CSVImporter:
    def __init__(self, table_name):
        """初始化导入器"""
        self.table_name = table_name
        self.conn = None
        self.cursor = None
        self.csv_path = None
        
        try:
            self.conn = mysql.connector.connect(**MYSQL_CONFIG)
            self.cursor = self.conn.cursor()
            print("数据库连接成功!")
        except mysql.connector.Error as err:
            print(f"数据库连接失败: {err}")
            raise

    def __del__(self):
        """析构函数，确保关闭连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("关闭数据库连接")

    def select_csv_file(self):
        """选择CSV文件"""
        print("打开文件选择对话框...")
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        
        # 设置初始目录为当前目录下的data文件夹
        initial_dir = os.path.join(os.getcwd(), "data")
        
        file_path = filedialog.askopenfilename(
            title="选择CSV文件",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialdir=initial_dir
        )
        
        if file_path:
            self.csv_path = file_path
            print(f"已选择文件: {self.csv_path}")
            return True
        
        print("未选择文件或取消选择")
        return False

    def create_csv_table(self):
        """创建CSV表"""
        print(f"正在创建数据表 {self.table_name}...")
        
        # 删除现有表
        drop_table = f"DROP TABLE IF EXISTS {self.table_name}"
        try:
            self.cursor.execute(drop_table)
        except mysql.connector.Error as err:
            print(f"删除旧表失败: {err}")
            return False

        # 创建新表
        create_table = f"""
        CREATE TABLE {self.table_name} (
            id INT PRIMARY KEY AUTO_INCREMENT,
            cnumber VARCHAR(50),
            s_raw VARCHAR(255) NOT NULL,
            s_ftid VARCHAR(255),
            s_function VARCHAR(255),
            s_location VARCHAR(255),
            s_device VARCHAR(255),
            s_terminal VARCHAR(255),
            t_raw VARCHAR(255) NOT NULL,
            t_ftid VARCHAR(255),
            t_function VARCHAR(255),
            t_location VARCHAR(255),
            t_device VARCHAR(255),
            t_terminal VARCHAR(255),
            color VARCHAR(50)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
        
        try:
            self.cursor.execute(create_table)
            print("数据表创建成功")
            return True
        except mysql.connector.Error as err:
            print(f"创建表失败: {err}")
            return False

    def format_data(self):
        """执行数据格式处理"""
        print("执行数据格式化...")
        
        try:
            # 开始事务
            self.conn.start_transaction()

            # 1. 处理括号和冒号的情况
            query_bracket = """
                UPDATE v_csv_raw
                SET s_ftid = CONCAT(
                    SUBSTRING(s_raw, 1, LOCATE(':', s_raw) - 1),
                    ':',
                    TRIM(LEADING '-' FROM SUBSTRING(
                        s_raw,
                        LOCATE('(', s_raw) + 1,
                        LOCATE(')', s_raw) - LOCATE('(', s_raw) - 1
                    ))
                )
                WHERE s_raw LIKE '%(%):%'
            """
            self.cursor.execute(query_bracket)
            
            # 对目标端执行相同操作
            query_t_bracket = query_bracket.replace('s_raw', 't_raw').replace('s_ftid', 't_ftid')
            self.cursor.execute(query_t_bracket)

            # 2. 处理包含 "-A" 的情况
            query_A = """
                UPDATE v_csv_raw
                SET s_ftid = SUBSTRING(s_raw, LOCATE(':', s_raw) + 1)
                WHERE s_raw LIKE '%:%-A%' 
                AND s_raw NOT LIKE '%(%:%'
                AND s_raw NOT LIKE '%:-%:%'
            """
            self.cursor.execute(query_A)
            
            # 对目标端执行相同操作
            query_t_A = query_A.replace('s_raw', 't_raw').replace('s_ftid', 't_ftid')
            self.cursor.execute(query_t_A)

            # 3. 处理包含 "-X" 和多个冒号的情况
            query_X = """
                UPDATE v_csv_raw
                SET s_ftid = SUBSTRING_INDEX(s_raw, ':', 2)
                WHERE s_raw LIKE '%-X%:%:%'
            """
            self.cursor.execute(query_X)
            
            # 对目标端执行相同操作
            query_t_X = query_X.replace('s_raw', 't_raw').replace('s_ftid', 't_ftid')
            self.cursor.execute(query_t_X)

            # 4. 处理 "-D/-E/-G/-M/-U" 的情况
            query_DEGMU = """
                UPDATE v_csv_raw
                SET s_ftid = SUBSTRING(s_raw, LOCATE(':', s_raw) + 1)
                WHERE (s_raw LIKE '%:%-D%' OR s_raw LIKE '%:%-E%' 
                       OR s_raw LIKE '%:%-G%' OR s_raw LIKE '%:%-M%' 
                       OR s_raw LIKE '%:%-U%')
                AND s_raw NOT LIKE '%(%:%'
                AND s_raw NOT LIKE '%:-%:%'
                AND s_raw NOT LIKE '%:%-A%'
            """
            self.cursor.execute(query_DEGMU)
            
            # 对目标端执行相同操作
            query_t_DEGMU = query_DEGMU.replace('s_raw', 't_raw').replace('s_ftid', 't_ftid')
            self.cursor.execute(query_t_DEGMU)

            # 5. 处理 ":-" 的情况
            query_colon_dash = """
                UPDATE v_csv_raw
                SET s_ftid = REPLACE(s_raw, ':-', '-')
                WHERE s_raw LIKE '%:-%:%'
                AND s_raw NOT LIKE '%(%:%'
                AND s_raw NOT LIKE '%:%-A%'
                AND (s_raw NOT LIKE '%:%-D%' AND s_raw NOT LIKE '%:%-E%'
                     AND s_raw NOT LIKE '%:%-G%' AND s_raw NOT LIKE '%:%-M%'
                     AND s_raw NOT LIKE '%:%-U%')
            """
            self.cursor.execute(query_colon_dash)
            
            # 对目标端执行相同操作
            query_t_colon_dash = query_colon_dash.replace('s_raw', 't_raw').replace('s_ftid', 't_ftid')
            self.cursor.execute(query_t_colon_dash)

            # 6. 提取设备和终端字段
            query_device = """
                UPDATE v_csv_raw
                SET s_device = SUBSTRING(
                    s_ftid,
                    LOCATE('-', s_ftid) + 1,
                    LOCATE(':', s_ftid, LOCATE('-', s_ftid)) - LOCATE('-', s_ftid) - 1
                )
                WHERE s_ftid LIKE '%-%:%'
            """
            self.cursor.execute(query_device)
            
            query_t_device = query_device.replace('s_ftid', 't_ftid').replace('s_device', 't_device')
            self.cursor.execute(query_t_device)

            # 提取终端信息
            query_terminal = """
                UPDATE v_csv_raw
                SET t_terminal = SUBSTRING(t_ftid, LOCATE(':', t_ftid) + 1)
                WHERE t_ftid LIKE '%:%'
            """
            self.cursor.execute(query_terminal)

            # 提交事务
            self.conn.commit()
            print("数据格式化完成")
            return True

        except mysql.connector.Error as err:
            print(f"数据格式化失败: {err}")
            self.conn.rollback()
            return False

    def import_from_csv(self):
        """从CSV文件导入数据"""
        if not self.create_csv_table():
            print("创建表失败")
            return False

        print(f"打开CSV文件: {self.csv_path}")
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                
                # 跳过前4行(标题行和非设备数据)
                for _ in range(4):
                    next(csv_reader)
                
                rows = []
                for line_num, fields in enumerate(csv_reader, start=1):
                    if not fields:  # 跳过空行
                        continue
                        
                    if len(fields) >= 9:
                        row = CSVRow()
                        row.cnumber = fields[0]
                        row.color = fields[4]
                        
                        # 处理源数据
                        row.s_raw = fields[7]
                        if row.s_raw:
                            result = parse_ftid(row.s_raw)
                            row.s_ftid = result['ftid']
                            row.s_function = result['function']
                            row.s_location = result['location']
                            row.s_device = result['device']
                            row.s_terminal = result['terminal']
                        
                        # 处理目标数据
                        row.t_raw = fields[8]
                        if row.t_raw:
                            result = parse_ftid(row.t_raw)
                            row.t_ftid = result['ftid']
                            row.t_function = result['function']
                            row.t_location = result['location']
                            row.t_device = result['device']
                            row.t_terminal = result['terminal']
                            
                        rows.append(row)
                
                print("CSV文件解析完成，开始导入数据...")
                return self._batch_insert_rows(rows)
                
        except Exception as e:
            print(f"无法打开或处理CSV文件: {e}")
            return False

    def _batch_insert_rows(self, rows):
        """批量插入数据"""
        print("开始批量插入数据...")
        
        try:
            self.conn.start_transaction()
            insert_count = 0
            
            for row in rows:
                if row.s_raw and row.t_raw:
                    query = f"""
                    INSERT INTO {self.table_name} (
                        cnumber, s_raw, s_ftid, s_function, s_location, s_device, s_terminal,
                        t_raw, t_ftid, t_function, t_location, t_device, t_terminal, color
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s
                    )
                    """
                    
                    values = (
                        row.cnumber, row.s_raw, row.s_ftid, row.s_function, row.s_location,
                        row.s_device, row.s_terminal, row.t_raw, row.t_ftid, row.t_function,
                        row.t_location, row.t_device, row.t_terminal, row.color
                    )
                    
                    self.cursor.execute(query, values)
                    insert_count += 1
                    
                    if insert_count % 100 == 0:
                        print(f"已插入 {insert_count} 条记录...")
            
            self.conn.commit()
            print(f"成功插入 {insert_count} 条记录")
            return True
            
        except mysql.connector.Error as err:
            print(f"插入失败: {err}")
            self.conn.rollback()
            return False

def main():
    print("程序开始运行...")
    
    try:
        print("创建 CSVImporter 实例...")
        importer = CSVImporter("v_csv_raw")
        
        print("请选择要导入的CSV文件...")
        if not importer.select_csv_file():
            print("文件选择失败，程序退出")
            return 1
            
        print("开始导入数据...")
        if importer.import_from_csv():
            print("数据导入成功")
            
            if not importer.format_data():
                print("数据格式化失败")
                return 1
        else:
            print("数据导入失败")
            return 1
            
    except Exception as e:
        print(f"错误: {e}")
        return 1
        
    print("程序正常结束")
    return 0

if __name__ == "__main__":
    main()