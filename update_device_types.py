import pymysql
from config import MYSQL_CONFIG
from device_mapping import get_plc_device

def update_device_types():
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # 获取所有需要更新的记录
        cursor.execute("""
            SELECT d.id, d.Function, d.Location
            FROM v_csv_device d
            WHERE d.Type IS NULL OR d.Type = '' OR d.Type = 'DEVICE'
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
                # 更新记录
                cursor.execute("""
                    UPDATE v_csv_device
                    SET Type = %s
                    WHERE id = %s
                """, (new_type, device_id))
                updated_count += 1
                print(f"更新记录 {device_id}: {func}.{csv_device} -> {new_type}")
        
        conn.commit()
        print(f"\n成功更新了 {updated_count} 条设备的Type字段")
        
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    update_device_types()