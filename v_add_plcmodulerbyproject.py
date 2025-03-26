import pymysql
from config import MYSQL_CONFIG
from device_mapping import get_plc_device

def create_plc_type_table(conn):
    """创建并初始化PLC类型表"""
    try:
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
        
        # 强制更新设备点位类型
        print("\n开始强制更新设备点位类型...")
        force_update_device_point(conn)
        
        conn.commit()
        print("所有更新已提交")
        
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
        raise

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
def force_update_device_point(conn):
    """根据Function,Device和Terminal更新v_csv_devpoint的Type字段"""
    cursor = conn.cursor()
    try:
        # 先查看Device以A开头的记录(不限制Type值)
        cursor.execute("""
            SELECT id, Function, Device, Terminal, Type
            FROM v_csv_devpoint
            WHERE Device LIKE 'A%'
            AND Function NOT IN ('A01', 'A02')
            LIMIT 100
        """)
        plc_points = cursor.fetchall()
        
        print("PLC设备前100条记录(Device以A开头):")
        print("ID | Function | Device | Terminal | Type")
        print("-" * 50)
        for row in plc_points:
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
            
        # 获取需要更新的记录(只处理PLC设备且Type为NULL或空)
        cursor.execute("""
            SELECT id, Function, Device, Terminal
            FROM v_csv_devpoint
            WHERE Device LIKE 'A%'
        """)
        points = cursor.fetchall()
        print(f"\n找到 {len(points)} 条需要更新的记录")
        
        updated_count = 0
        count = 1  # 初始化计数器
        
        for point_id, func, device, terminal in points:
            count += 1  # 递增计数器
            try:
                print(f"\n[处理记录 #{count}]")
                print(f"1. 当前记录信息:")
                print(f"   - ID: {point_id}")
                print(f"   - Function: {func}")
                print(f"   - Device: {device}")
                print(f"   - Terminal: {terminal}")
                
                # 1. 检查v_plc_typeitem表中是否有匹配的类型
                print(f"\n2. 查询 v_plc_typeitem 表:")
                print(f"   - 条件: Function='{func}' AND Device='{device}'")
                cursor.execute("""
                    SELECT Type FROM v_plc_typeitem
                    WHERE Function = %s AND Device = %s
                    LIMIT 1
                """, (func, device))
                
                type_result = cursor.fetchone()
                if not type_result:
                    print(f"   - 结果: 未找到匹配记录")
                    continue
                
                plc_type = type_result[0]
                print(f"   - 结果: 找到Type='{plc_type}'")
                
                print(f"\n3. 查询 device_types 表:")
                print(f"   - 条件: type_name='{plc_type}'")
                cursor.execute("""
                    SELECT id FROM device_types
                    WHERE type_name = %s
                    LIMIT 1
                """, (plc_type,))
                
                type_id_result = cursor.fetchone()
                if not type_id_result:
                    print(f"   - 结果: 未找到匹配记录")
                    continue
                
                type_id = type_id_result[0]
                print(f"   - 结果: 找到id='{type_id}'")
                
                print(f"\n4. 转换Terminal值:")
                print(f"   - 输入: {terminal}")
                try:
                    point_index = int(terminal.replace('T', ''))
                    print(f"   - 结果: point_index={point_index}")
                except ValueError as e:
                    print(f"   - 错误: 转换失败 - {e}")
                    continue
                
                print(f"\n5. 查询 device_type_points 表:")
                print(f"   - 条件: device_type_id='{type_id}', point_index='{point_index}'")
                cursor.execute("""
                    SELECT point_type FROM device_type_points
                    WHERE device_type_id = %s AND point_index = %s
                    LIMIT 1
                """, (type_id, point_index))
                
                point_type_result = cursor.fetchone()
                if point_type_result:
                    print(f"   - 结果: 找到point_type='{point_type_result[0]}'")
                    
                    print(f"\n6. 更新记录:")
                    print(f"   - ID: {point_id}")
                    print(f"   - 新Type值: {point_type_result[0]}")
                    cursor.execute("""
                        UPDATE v_csv_devpoint
                        SET Type = %s
                        WHERE id = %s
                    """, (point_type_result[0], point_id))
                    updated_count += 1
                    print(f"   - 状态: 更新成功")
                else:
                    print(f"   - 结果: 未找到匹配记录")
                    
            except (ValueError, pymysql.Error) as e:
                print(f"处理记录{point_id}时出错: {e}")
                continue
        
        print(f"成功更新 {updated_count} 条记录的Type字段")
        
    except pymysql.Error as err:
        print(f"更新设备点位时出错: {err}")
        raise

if __name__ == "__main__":
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        
        # 可以单独注释不需要执行的方法
        create_plc_type_table(conn)  # 方法1: 创建PLC类型表并插入数据
        pause = input("1 方法1: 创建PLC类型表并插入数据 按Enter键继续...")
        force_update_device_types(conn)  # 方法2: 更新设备类型
        pause = input("2 方法2: 更新设备类型 按Enter键继续...")
        force_update_device_point(conn)  # 方法3: 更新设备点位类型
        pause = input("3 方法3: 更新设备点位类型按Enter键继续...")
        
        conn.commit()
        print("所有操作已完成")
        
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()