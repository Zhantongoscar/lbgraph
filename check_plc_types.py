import pymysql
from config import MYSQL_CONFIG

def check_plc_types():
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # 检查v_plc_typeitem表数据
        print("v_plc_typeitem表数据示例:")
        cursor.execute("""
            SELECT Function, Device, Type 
            FROM v_plc_typeitem
            ORDER BY Function, Device
            LIMIT 20
        """)
        for func, dev, typ in cursor.fetchall():
            print(f"{func}.{dev}: {typ}")
            
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_plc_types()