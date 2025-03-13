import pymysql
import json
import sys

def main():
    try:
        print("加载配置...")
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)['mysql']
        
        print("连接数据库...")
        conn = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4'
        )
        
        try:
            with conn.cursor() as cursor:
                print("\n查询表结构...")
                cursor.execute("DESCRIBE v_csv_raw")
                print("\n=== v_csv_raw 表结构 ===")
                for row in cursor.fetchall():
                    print(row)
                
                print("\n查询示例数据...")
                cursor.execute("SELECT * FROM v_csv_raw LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                if row:
                    print("\n=== 列名 ===")
                    print(columns)
                    print("\n=== 数据示例 ===")
                    for i, value in enumerate(row):
                        print(f"{columns[i]}: {value}")
        finally:
            conn.close()
            print("\n数据库连接已关闭")
            
    except Exception as e:
        print(f"错误: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())