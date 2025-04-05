import pymysql
from config import MYSQL_CONFIG

def main():
    conn = pymysql.connect(**MYSQL_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 获取表中的列信息
            sql = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'v_csv_raw'
            """
            cursor.execute(sql)
            print("=== 表结构信息 ===")
            for row in cursor.fetchall():
                print(row)

            # 获取一条示例数据
            cursor.execute("SELECT * FROM v_csv_raw LIMIT 1")
            print("\n=== 示例数据 ===")
            columns = [d[0] for d in cursor.description]
            print("列名:", columns)
            data = cursor.fetchone()
            print("数据:", data)
            
    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()