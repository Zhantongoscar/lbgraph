import pymysql
from config import MYSQL_CONFIG
from device_mapping import get_plc_device

def create_plc_type_table():
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # 创建表(添加IF NOT EXISTS)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS v_plc_typeitem (
            id INT AUTO_INCREMENT PRIMARY KEY,
            projectid VARCHAR(50) NOT NULL,
            Function VARCHAR(50) NOT NULL,
            Device VARCHAR(50) NOT NULL,
            Type VARCHAR(50) NOT NULL,
            UNIQUE KEY unique_function_device (Function, Device)
        )""")
        
        # 准备插入数据(完整列表)
        plc_data = [
            ('EOS1550', 'A02', 'A1', 'EL2809'),
            # 完整数据列表...
        ]
        
        # 使用REPLACE INTO确保数据更新
        cursor.executemany("""
        REPLACE INTO v_plc_typeitem 
        (projectid, Function, Device, Type)
        VALUES (%s, %s, %s, %s)""", plc_data)
        
        print(f"成功插入/更新 {cursor.rowcount} 条PLC类型数据")
        
        # 强制更新所有设备类型
        print("\n开始强制更新设备类型...")
        force_update_device_types(conn)
        
        conn.commit()
        print("所有更新已提交")
        
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()

def force_update_device_types(conn):
    """强制更新所有匹配的设备类型"""
    cursor = conn.cursor()
    try:
        # 获取所有记录(不限条件)
        cursor.execute("""
            SELECT d.id, d.Function, d.Location
            FROM v_csv_device d
            ORDER BY d.id
        """)
        devices = cursor.fetchall()
        
        updated_count = 0
        
        for device_id, func, location in devices:
            # 提取设备编号并映射
            csv_device = location.split('.')[-1]
            plc_device = get_plc_device(csv_device)
            
            # 查询匹配的PLC类型
            cursor.execute("""
                SELECT Type FROM v_plc_typeitem
                WHERE Function = %s AND Device = %s
                LIMIT 1
            """, (func, plc_device))
            
            result = cursor.fetchone()
            if result:
                new_type = result[0]
                # 直接更新记录
                cursor.execute("""
                    UPDATE v_csv_device
                    SET Type = %s
                    WHERE id = %s
                """, (new_type, device_id))
                updated_count += 1
        
        print(f"强制更新 {updated_count} 条设备的Type字段")
        
    except pymysql.Error as err:
        print(f"更新设备类型时出错: {err}")
        raise

if __name__ == "__main__":
    create_plc_type_table()