from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import sys
import os

# 创建logs目录
if not os.path.exists('logs'):
    os.makedirs('logs')

# 设置输出文件
log_file = 'logs/neo4j_test.log'
with open(log_file, 'w', encoding='utf-8') as f:
    def log(message):
        print(message)
        f.write(message + '\n')
        f.flush()

    try:
        log("开始测试Neo4j连接...")
        log(f"URI: {NEO4J_URI}")

        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session() as session:
            # 测试连接
            log("测试基本连接...")
            result = session.run("RETURN 1 AS test")
            test_value = result.single()["test"]
            log(f"连接测试结果: {test_value}")

            # 检查节点标签
            log("\n检查节点标签...")
            result = session.run("""
                CALL db.labels() YIELD label 
                RETURN collect(label) AS labels
            """)
            labels = result.single()["labels"]
            log("可用的标签:")
            for label in sorted(labels):
                log(f"  - {label}")

            # 检查节点数量
            log("\n检查节点数量...")
            for label in ["V_Device", "V_Terminal"]:
                result = session.run(f"""
                    MATCH (n:{label})
                    RETURN count(n) as count
                """)
                count = result.single()["count"]
                log(f"{label}: {count}个节点")

            # 显示一些示例节点
            log("\n节点示例:")
            result = session.run("""
                MATCH (n) 
                WHERE n:V_Device OR n:V_Terminal
                RETURN n, labels(n) as labels LIMIT 3
            """)
            for record in result:
                node = record["n"]
                labels = record["labels"]
                log(f"\n节点类型: {labels}")
                log("节点属性:")
                for key, value in sorted(node.items()):
                    log(f"  {key}: {value}")

        driver.close()
        log("\n测试完成。详细日志已保存到: " + log_file)

    except Exception as e:
        log(f"错误: {str(e)}")
        log(f"错误类型: {type(e).__name__}")
        sys.exit(1)