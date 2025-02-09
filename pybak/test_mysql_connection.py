import pymysql
import socket
import subprocess
import platform

# MySQL配置
config = {
    "host": "192.168.35.10",
    "user": "root",
    "password": "13701033228",
    "database": "lbfat",
    "connect_timeout": 10
}

def test_network():
    print("\n=== 网络连接测试 ===")
    host = config["host"]
    
    # 测试是否可以ping通
    print(f"\n1. Ping测试 {host}...")
    ping_param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        output = subprocess.check_output(["ping", ping_param, "1", host], universal_newlines=True)
        print("Ping结果:")
        print(output)
    except subprocess.CalledProcessError as e:
        print(f"Ping失败: {e}")
    
    # 测试MySQL端口
    print(f"\n2. 测试MySQL端口(3306)...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        result = sock.connect_ex((host, 3306))
        if result == 0:
            print("端口3306开放")
        else:
            print(f"端口3306未开放 (错误代码: {result})")
    except socket.error as e:
        print(f"连接测试失败: {e}")
    finally:
        sock.close()

def test_mysql_connection():
    print("\n=== MySQL连接测试 ===")
    try:
        print("\n1. 尝试连接到MySQL...")
        print(f"配置信息: {config}")
        
        conn = pymysql.connect(**config)
        print("连接成功!")
        
        # 测试查询
        with conn.cursor() as cursor:
            print("\n2. 执行测试查询...")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("数据库中的表:")
            for table in tables:
                print(f"- {table[0]}")
        
        conn.close()
        print("\n所有测试完成!")
        
    except pymysql.Error as e:
        print("\nMySQL连接失败!")
        print(f"错误类型: {type(e)}")
        print(f"错误代码: {e.args[0]}")
        print(f"错误消息: {e.args[1]}")

if __name__ == "__main__":
    print("开始连接测试...")
    test_network()
    test_mysql_connection()