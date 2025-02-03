from neo4j import GraphDatabase

# Neo4j 连接配置
URI = "bolt://192.168.35.10:7687"
AUTH = ("neo4j", "13701033228")  # Neo4j数据库认证信息

def import_csv_data():
    # 初始化 Neo4j 驱动
    driver = GraphDatabase.driver(URI, auth=AUTH)

    # Cypher 查询
    query = """
    LOAD CSV WITH HEADERS FROM 'file:///SmartWiringzta.csv' AS row
    // 处理 source 字段
    WITH row,
        CASE 
            WHEN NOT (row.source CONTAINS '=' OR row.source CONTAINS '+' OR row.source CONTAINS '-' OR row.source CONTAINS ':')
            THEN '=+-:' + row.source
            WHEN row.source CONTAINS '=' AND row.source CONTAINS '+' AND NOT row.source CONTAINS '-'
            THEN SPLIT(row.source, '+')[0] + '+-' + SPLIT(row.source, '+')[1]
            ELSE row.source
        END AS processedSource,
        // 处理 target 字段
        CASE 
            WHEN NOT (row.target CONTAINS '=' OR row.target CONTAINS '+' OR row.target CONTAINS '-' OR row.target CONTAINS ':')
            THEN '=+-:' + row.target
            WHEN row.target CONTAINS '=' AND row.target CONTAINS '+' AND NOT row.target CONTAINS '-'
            THEN SPLIT(row.target, '+')[0] + '+-' + SPLIT(row.target, '+')[1]
            ELSE row.target
        END AS processedTarget
    // 对处理后的 source 进行拆分
    WITH row, processedSource, processedTarget,
        SPLIT(SUBSTRING(processedSource, SIZE(SPLIT(processedSource, '=')[0]) + 1), '+')[0] AS sourceFunction,
        SPLIT(SPLIT(processedSource, '+')[1], '-')[0] AS sourceLocation,
        SPLIT(SPLIT(SPLIT(processedSource, '+')[1], '-')[1], ':')[0] AS sourceDevice,
        SUBSTRING(processedSource, SIZE(SPLIT(SPLIT(SPLIT(processedSource, '+')[1], '-')[1], ':')[0]) + SIZE(SPLIT(SPLIT(processedSource, '+')[1], '-')[1]) + 1) AS sourceTerminal,
        // 对处理后的 target 进行拆分
        SPLIT(SUBSTRING(processedTarget, SIZE(SPLIT(processedTarget, '=')[0]) + 1), '+')[0] AS targetFunction,
        SPLIT(SPLIT(processedTarget, '+')[1], '-')[0] AS targetLocation,
        SPLIT(SPLIT(SPLIT(processedTarget, '+')[1], '-')[1], ':')[0] AS targetDevice,
        SUBSTRING(processedTarget, SIZE(SPLIT(SPLIT(SPLIT(processedTarget, '+')[1], '-')[1], ':')[0]) + SIZE(SPLIT(SPLIT(processedTarget, '+')[1], '-')[1]) + 1) AS targetTerminal
    // 过滤掉 source 或 target 为空的行
    WHERE processedSource IS NOT NULL AND processedTarget IS NOT NULL
    // 若不存在对应属性的 Vertex 节点则创建，若存在则匹配该节点
    MERGE (source:Vertex {
        name: processedSource,
        Function: sourceFunction,
        Location: sourceLocation,
        Device: sourceDevice,
        Terminal: sourceTerminal
    })
    MERGE (target:Vertex {
        name: processedTarget,
        Function: targetFunction,
        Location: targetLocation,
        Device: targetDevice,
        Terminal: targetTerminal
    })
    // 创建从 source 到 target 的 Edge 关系
    CREATE (source)-[r1:Edge {
        // 为关系的 id 属性赋值，将 CSV 中 Consecutive number 列的值转换为整数类型
        id: toInteger(row['Consecutive number']),
        // 为关系的 color 属性赋值，取 CSV 中 Connection: Cross-section / diameter 列的值
        color: row['Connection: Cross-section / diameter']
    }]->(target)
    // 创建从 target 到 source 的 Edge 关系
    CREATE (target)-[r2:Edge {
        id: toInteger(row['Consecutive number']),
        color: row['Connection: Cross-section / diameter']
    }]->(source);
    """

    # 执行查询
    with driver.session() as session:
        session.run(query)
    print("数据导入完成")

if __name__ == "__main__":
    import_csv_data()