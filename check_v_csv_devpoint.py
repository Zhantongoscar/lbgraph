import pymysql
from config import MYSQL_CONFIG

def check_v_csv_devpoint():
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # 查询前10条记录
        cursor.execute("""
            SELECT id, Function, Device, Terminal, Type
            FROM v_csv_devpoint
            LIMIT 10
        """)
        
        print("v_csv_devpoint表前10条记录:")
        print("ID | Function | Device | Terminal | Type")
        print("-" * 50)
        for row in cursor.fetchall():
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
            
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_v_csv_devpoint()