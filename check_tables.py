#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import json

def main():
    # 加载配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)['mysql']

    # 连接数据库
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
            # 检查表是否存在
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name IN ('v_csv_device', 'v_csv_devpoint', 'v_csv_conn')
            """, (config['database'],))
            
            tables = cursor.fetchall()
            print("\n=== 存在的表 ===")
            for table in tables:
                print(f"表名: {table['table_name']}")
                
                # 获取记录数
                cursor.execute(f"SELECT COUNT(*) as count FROM {table['table_name']}")
                count = cursor.fetchone()['count']
                print(f"记录数: {count}")
                
                # 显示示例数据
                cursor.execute(f"SELECT * FROM {table['table_name']} LIMIT 3")
                rows = cursor.fetchall()
                if rows:
                    print("数据示例:")
                    for row in rows:
                        print(f"  {row}")
                print()

    finally:
        conn.close()

if __name__ == "__main__":
    main()