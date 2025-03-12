import sys
import pymysql
from neo4j import GraphDatabase
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def print_stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    sys.stderr.flush()

def test_connections():
    print_stderr("开始测试数据库连接...")
    
    # 测试MySQL连接
    try:
        print_stderr("\n=== 测试MySQL连接 ===")
        print_stderr(f"尝试连接到: {MYSQL_CONFIG['host']}")
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM v_csv_raw")
        count = cursor.fetchone()[0]
        print_stderr(f"MySQL连接成功！v_csv_raw表中有 {count} 条记录")
        conn.close()
    except Exception as e:
        print_stderr(f"MySQL连接失败: {str(e)}")
        raise

    # 测试Neo4j连接
    try:
        print_stderr("\n=== 测试Neo4j连接 ===")
        print_stderr(f"尝试连接到: {NEO4J_URI}")
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            if result.single()["test"] == 1:
                print_stderr("Neo4j连接成功！")
        driver.close()
    except Exception as e:
        print_stderr(f"Neo4j连接失败: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        test_connections()
        print_stderr("\n所有测试完成！")
    except Exception as e:
        print_stderr(f"\n测试失败: {str(e)}")
        sys.exit(1)