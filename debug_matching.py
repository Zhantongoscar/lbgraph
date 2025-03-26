import pymysql
from config import MYSQL_CONFIG

def debug_matching():
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # 1. 检查v_csv_device表的Function字段格式
        print("1. v_csv_device表的Function字段格式检查:")
        cursor.execute("""
            SELECT Function, COUNT(*) as count 
            FROM v_csv_device 
            GROUP BY Function
            ORDER BY count DESC
            LIMIT 10
        """)
        print("Function字段值分布:")
        for func, count in cursor.fetchall():
            print(f"  {func}: {count}条记录")

        # 2. 检查v_plc_typeitem表的Function字段格式
        print("\n2. v_plc_typeitem表的Function字段格式检查:")
        cursor.execute("SELECT DISTINCT Function FROM v_plc_typeitem")
        print("Function字段值:", [row[0] for row in cursor.fetchall()])

        # 3. 检查Location字段提取结果
        print("\n3. Location字段提取分析:")
        cursor.execute("""
            SELECT 
                Location,
                SUBSTRING_INDEX(Location, '.', -1) as extracted,
                COUNT(*) as count
            FROM v_csv_device
            GROUP BY Location, extracted
            ORDER BY count DESC
            LIMIT 10
        """)
        print("Location字段提取示例:")
        for loc, ext, count in cursor.fetchall():
            print(f"  {loc} -> 提取结果: {ext} (出现{count}次)")

        # 4. 检查潜在匹配情况
        print("\n4. 潜在匹配分析:")
        cursor.execute("""
            SELECT 
                d.Function as csv_func,
                p.Function as plc_func,
                SUBSTRING_INDEX(d.Location, '.', -1) as csv_device,
                p.Device as plc_device,
                COUNT(*) as count
            FROM v_csv_device d
            CROSS JOIN v_plc_typeitem p
            WHERE d.Function = p.Function
            GROUP BY csv_func, plc_func, csv_device, plc_device
            ORDER BY count DESC
            LIMIT 10
        """)
        matches = cursor.fetchall()
        if matches:
            print("找到潜在匹配:")
            for row in matches:
                print(f"  CSV Function: {row[0]}, PLC Function: {row[1]}, CSV Device: {row[2]}, PLC Device: {row[3]}, 匹配数: {row[4]}")
        else:
            print("未找到任何Function匹配的记录")

    except pymysql.Error as err:
        print(f"数据库错误: {err}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    debug_matching()