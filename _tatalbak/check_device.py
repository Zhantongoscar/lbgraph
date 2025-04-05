#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import json

def check_raw_data():
    # 加载数据库配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)['mysql']

    # 连接到数据库
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
            # 检查所有包含A4的设备
            print("\n=== 检查A4相关设备 ===")
            cursor.execute("""
                SELECT fdid, Function, Location, Device, Type
                FROM v_csv_device
                WHERE fdid LIKE '%A4%'
                AND Location LIKE 'K1.%'
                ORDER BY fdid
            """)
            results = cursor.fetchall()
            print(f"\n找到 {len(results)} 条A4相关设备记录:")
            for row in results:
                print(f"\nFDID: {row['fdid']}")
                print(f"Function: {row['Function']}")
                print(f"Location: {row['Location']}")
                print(f"Device: {row['Device']}")
                print(f"Type: {row['Type']}")

            # 检查所有包含A4的端子
            print("\n=== 检查A4相关端子 ===")
            cursor.execute("""
                SELECT ftid, raw, belongtoDevice, Terminal, Type
                FROM v_csv_devpoint
                WHERE ftid LIKE '%A4%'
                AND Location LIKE 'K1.%'
                ORDER BY ftid
                LIMIT 5
            """)
            results = cursor.fetchall()
            print(f"\n显示前5条A4相关端子记录:")
            for row in results:
                print(f"\nFTID: {row['ftid']}")
                print(f"RAW: {row['raw']}")
                print(f"belongtoDevice: {row['belongtoDevice']}")
                print(f"Terminal: {row['Terminal']}")
                print(f"Type: {row['Type']}")

    finally:
        conn.close()

if __name__ == "__main__":
    check_raw_data()