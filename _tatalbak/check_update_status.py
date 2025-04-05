import pymysql
from config import MYSQL_CONFIG

def check_update_status():
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # 检查未更新的记录
        cursor.execute("""
            SELECT COUNT(*) 
            FROM v_csv_device 
            WHERE Type IS NULL OR Type = ''
        """)
        empty_count = cursor.fetchone()[0]
        print(f"未更新的记录数: {empty_count}")
        
        # 检查已更新的记录
        cursor.execute("""
            SELECT Function, Location, Type, COUNT(*) as count
            FROM v_csv_device
            WHERE Type IS NOT NULL AND Type != ''
            GROUP BY Function, Location, Type
            ORDER BY count DESC
            LIMIT 10
        """)
        print("\n已更新的记录示例:")
        for func, loc, typ, count in cursor.fetchall():
            print(f"{func}.{loc}: {typ} (共{count}条)")
            
    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_update_status()