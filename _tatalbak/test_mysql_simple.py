import os
import sys
import time
import traceback

# 设置日志文件
log_file = "mysql_test.log"

def log(message):
    """写入日志文件并尝试打印到控制台"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    
    # 写入文件
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')
    
    # 尝试打印到控制台
    print(log_message, flush=True)

log("开始MySQL连接测试...")

try:
    import pymysql
    log("成功导入pymysql模块")
except Exception as e:
    log(f"导入pymysql失败: {e}")
    log(traceback.format_exc())
    sys.exit(1)

config = {
    "host": "192.168.35.10",
    "user": "root",
    "password": "13701033228",
    "database": "lbfat",
    "connect_timeout": 5
}

log("\n使用以下配置:")
for key, val in config.items():
    if key != 'password':
        log(f"  {key}: {val}")
    else:
        log(f"  {key}: ****")

try:
    # 测试连接
    log("\n尝试连接MySQL...")
    start_time = time.time()
    conn = pymysql.connect(**config)
    connect_time = time.time() - start_time
    log(f"连接成功! 耗时: {connect_time:.2f}秒")

    # 测试基本查询
    log("\n执行测试查询...")
    with conn.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        log(f"MySQL版本: {version}")

        cursor.execute("SELECT COUNT(*) FROM conn_graph")
        count = cursor.fetchone()[0]
        log(f"conn_graph表中有 {count} 条记录")

        log("\n获取示例数据...")
        cursor.execute("""
            SELECT source, target, connNo 
            FROM conn_graph 
            WHERE isInPanel=1 
            LIMIT 3
        """)
        for row in cursor.fetchall():
            log(f"  - source={row[0]}, target={row[1]}, connNo={row[2]}")

    conn.close()
    log("\n测试完成")

except Exception as e:
    log(f"\n发生错误: {str(e)}")
    log(traceback.format_exc())
    sys.exit(1)

log("脚本执行完毕")