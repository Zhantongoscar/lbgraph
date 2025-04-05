import pymysql
from config import MYSQL_CONFIG

def check_matching():
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # 检查v_csv_device表的Function字段格式
        print("检查v_csv_device表的Function字段格式:")
        cursor.execute("SELECT DISTINCT Function FROM v_csv_device LIMIT 10")
        for func in cursor.fetchall():
            print(f"Function: {func[0]}")
        
        # 检查v_plc_typeitem表的Function字段格式
        print("\n检查v_plc_typeitem表的Function字段格式:")
        cursor.execute("SELECT DISTINCT Function FROM v_plc_typeitem LIMIT 10")
        for func in cursor.fetchall():
            print(f"Function: {func[0]}")
        
        # 检查Location字段提取结果
        print("\n检查Location字段提取结果:")
        cursor.execute("""
            SELECT DISTINCT 
                Location,
                SUBSTRING_INDEX(Location, '.', -1) as extracted_device
            FROM v_csv_device 
            LIMIT 10
        """)
        for loc, dev in cursor.fetchall():
            print(f"Location: {loc} -> 提取结果: {dev}")
            
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_matching()