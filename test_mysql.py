import pymysql
import sys
import time

mysql_config = {
    "host": "192.168.35.10",
    "user": "root",
    "password": "13701033228",
    "database": "lbfat",
    "connect_timeout": 10,
    "charset": 'utf8mb4'
}

print("MySQL连接测试 (使用pymysql)")
print("配置信息:")
for key, value in mysql_config.items():
    if key != "password":
        print(f"  {key}: {value}")
    else:
        print(f"  {key}: ***")

try:
    print("\n尝试连接到MySQL...")
    start_time = time.time()
    
    conn = pymysql.connect(**mysql_config)
    
    connect_time = time.time() - start_time
    print(f"MySQL连接成功! (耗时: {connect_time:.2f}秒)")

    # 测试数据库是否可用
    with conn.cursor() as cursor:
        # 获取服务器信息
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"\nMySQL版本: {version}")
        
        # 测试是否可以执行查询
        print("\n测试查询...")
        cursor.execute("SELECT COUNT(*) FROM conn_graph")
        count = cursor.fetchone()[0]
        print(f"conn_graph表中有 {count} 条记录")

        # 获取前几条数据
        print("\n获取示例数据:")
        cursor.execute("""
            SELECT source, target, connNo
            FROM conn_graph
            WHERE isInPanel=1
            LIMIT 3
        """)
        for row in cursor.fetchall():
            print(f"source={row[0]}, target={row[1]}, connNo={row[2]}")

    conn.close()
    print("\n测试完成")
    sys.exit(0)

except pymysql.Error as err:
    print(f"\nMySQL错误: {err}")
    if hasattr(err, 'errno'):
        print(f"错误代码: {err.errno}")
    sys.exit(1)
except Exception as e:
    print(f"\n其他错误: {str(e)}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)