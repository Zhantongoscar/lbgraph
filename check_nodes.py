from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import sys

def print_separator(char='-', length=80):
    print(char * length)

def print_section(title):
    print_separator()
    print(title)
    print_separator()

def print_properties(props):
    max_key_length = max([len(str(k)) for k in props.keys()]) if props else 0
    for key, value in sorted(props.items()):
        print(f"    {key:<{max_key_length}}: {value}")

try:
    print_section("连接Neo4j数据库")
    print(f"URI: {NEO4J_URI}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        # 检查V_Device节点示例
        print_section("V_Device节点属性分析")
        result = session.run("""
            MATCH (n:V_Device)
            WITH n, keys(n) as props
            RETURN collect(distinct props) as all_props, 
                   count(n) as total_nodes
            LIMIT 1
        """)
        record = result.single()
        if record:
            all_props = record["all_props"]
            total_nodes = record["total_nodes"]
            print(f"总节点数: {total_nodes}")
            print("\n可能的属性组合:")
            for prop_set in all_props:
                print(f"  属性集: {', '.join(sorted(prop_set))}")

        print("\n示例节点:")
        result = session.run("""
            MATCH (n:V_Device)
            RETURN n LIMIT 3
        """)
        for i, record in enumerate(result, 1):
            node = record["n"]
            print(f"\n节点 {i}:")
            print_properties(node)

        # 检查V_terminal节点示例
        print_section("V_terminal节点属性分析")
        result = session.run("""
            MATCH (n:V_terminal)
            WITH n, keys(n) as props
            RETURN collect(distinct props) as all_props,
                   count(n) as total_nodes
            LIMIT 1
        """)
        record = result.single()
        if record:
            all_props = record["all_props"]
            total_nodes = record["total_nodes"]
            print(f"总节点数: {total_nodes}")
            print("\n可能的属性组合:")
            for prop_set in all_props:
                print(f"  属性集: {', '.join(sorted(prop_set))}")

        print("\n示例节点:")
        result = session.run("""
            MATCH (n:V_terminal)
            RETURN n LIMIT 3
        """)
        for i, record in enumerate(result, 1):
            node = record["n"]
            print(f"\n节点 {i}:")
            print_properties(node)

        # 检查FTID/ftid属性的使用情况
        print_section("FTID/ftid属性检查")
        for label in ['V_Device', 'V_terminal']:
            for prop in ['FTID', 'ftid']:
                result = session.run(f"""
                    MATCH (n:{label})
                    WHERE n.{prop} IS NOT NULL
                    RETURN count(n) as count
                """)
                count = result.single()["count"]
                print(f"{label} 节点中有 {prop} 属性的数量: {count}")

        # 展示一些有FTID/ftid的节点示例
        print("\n有FTID/ftid的节点示例:")
        for label in ['V_Device', 'V_terminal']:
            print(f"\n{label}节点:")
            for prop in ['FTID', 'ftid']:
                result = session.run(f"""
                    MATCH (n:{label})
                    WHERE n.{prop} IS NOT NULL
                    RETURN n LIMIT 1
                """)
                record = result.single()
                if record:
                    node = record["n"]
                    print(f"\n  使用{prop}的节点示例:")
                    print_properties(node)

    print_separator('=')
    print("检查完成")
    driver.close()

except Exception as e:
    print(f"错误: {str(e)}", file=sys.stderr)
    sys.exit(1)
