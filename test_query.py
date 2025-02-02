from main import driver

def test_connection():
    try:
        with driver.session() as session:
            # 1. 测试基本连接
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"基本连接测试成功! 数据库中共有 {count} 个节点")

            # 2. 测试简单的MATCH查询
            result = session.run("MATCH (n) RETURN n LIMIT 25")
            nodes = result.data()
            print(f"\n成功获取前25个节点:")
            for i, node in enumerate(nodes, 1):
                print(f"{i}. {node}")

    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    test_connection()