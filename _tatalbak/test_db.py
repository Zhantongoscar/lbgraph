import pymysql
import json

def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)['mysql']

def main():
    config = load_config()
    conn = pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    try:
        with conn.cursor() as cursor:
            # 获取表结构
            cursor.execute("SHOW COLUMNS FROM v_csv_raw")
            columns = cursor.fetchall()
            print("\n=== 表结构 ===")
            for col in columns:
                print(col['Field'])
            
            # 获取一行数据示例
            cursor.execute("SELECT * FROM v_csv_raw LIMIT 1")
            row = cursor.fetchone()
            print("\n=== 数据示例 ===")
            for key, value in row.items():
                print(f"{key}: {value}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()