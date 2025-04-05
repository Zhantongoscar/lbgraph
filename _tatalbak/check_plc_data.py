import pymysql
from config import MYSQL_CONFIG

def check_data():
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # 检查v_plc_typeitem表记录数
        cursor.execute("SELECT COUNT(*) FROM v_plc_typeitem")
        count = cursor.fetchone()[0]
        print(f"v_plc_typeitem表记录数: {count}")
        
        # 检查v_csv_device表需要更新的记录数
        cursor.execute("""
            SELECT COUNT(*) 
            FROM v_csv_device 
            WHERE Type IS NULL OR Type = '' OR Type = 'DEVICE'
        """)
        update_count = cursor.fetchone()[0]
        print(f"需要更新的v_csv_device记录数: {update_count}")
        
        # 检查示例数据
        print("\n示例数据:")
        cursor.execute("SELECT * FROM v_plc_typeitem LIMIT 5")
        for row in cursor.fetchall():
            print(row)
            
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_data()