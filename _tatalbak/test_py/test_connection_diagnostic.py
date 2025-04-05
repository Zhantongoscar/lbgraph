from neo4j import GraphDatabase
import sys
import socket
import time
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def test_network():
    """测试网络连接"""
    try:
        # 从URI中提取主机名和端口
        uri = NEO4J_URI.replace("bolt://", "")
        host = uri.split(":")[0]
        port = int(uri.split(":")[1])
        
        print(f"\n1. 测试网络连通性:")
        print(f"正在连接 {host}:{port}...")
        
        # 创建socket连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        
        if result == 0:
            print("网络连接成功！✓")
        else:
            print(f"网络连接失败！端口 {port} 不可访问 ✗")
        sock.close()
        
    except Exception as e:
        print(f"网络测试出错: {str(e)} ✗")

def test_db_connection():
    """测试数据库连接"""
    print(f"\n2. 测试数据库连接:")
    print(f"使用URI: {NEO4J_URI}")
    print(f"用户名: {NEO4J_USER}")
    
    try:
        start_time = time.time()
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            result = session.run("RETURN 1 as num")
            value = result.single()[0]
            end_time = time.time()
            
            print(f"数据库连接成功！✓")
            print(f"查询测试成功！结果: {value} ✓")
            print(f"连接耗时: {(end_time - start_time):.2f} 秒")
            
            # 获取数据库信息
            print("\n3. 数据库信息:")
            result = session.run("CALL dbms.components() YIELD name, versions, edition")
            record = result.single()
            print(f"名称: {record['name']}")
            print(f"版本: {record['versions']}")
            print(f"版本类型: {record['edition']}")
            
    except Exception as e:
        print(f"数据库连接失败: {str(e)} ✗")
        print("\n可能的解决方案:")
        print("1. 确认Neo4j服务是否正在运行")
        print("2. 验证连接凭据是否正确")
        print("3. 检查防火墙设置")
        print("4. 确认Neo4j配置允许远程连接")
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    print("===== Neo4j 连接诊断工具 =====")
    test_network()
    test_db_connection()