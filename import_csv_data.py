import argparse
import os
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_CONFIG

class CsvDataImporter:
    def __init__(self, uri=None, user=None, password=None):
        """初始化数据导入器"""
        self.driver = GraphDatabase.driver(
            uri or NEO4J_URI,
            auth=(user or NEO4J_USER, password or NEO4J_PASSWORD),
            **NEO4J_CONFIG
        )

    def import_csv(self, csv_path):
        """导入CSV数据到Neo4j"""
        # 确保文件存在
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV文件不存在: {csv_path}")

        # 使用Neo4j服务器的导入路径格式
        # Neo4j服务器会在/import目录下查找文件
        file_url = f"file:///{os.path.basename(csv_path)}"
        
        with self.driver.session() as session:
            try:
                # 1. 清理现有数据
                print("清理现有数据...")
                session.run("MATCH (n) DETACH DELETE n")
                
                # 2. 导入CSV数据
                print(f"从 {csv_path} 导入数据...")
                
                query = """
                LOAD CSV WITH HEADERS FROM $file_url AS row
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
                // 若不存在对应属性的 Vertex 节点则创建,若存在则匹配该节点
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
                    id: toInteger(row['Consecutive number']),
                    color: row['Connection: Cross-section / diameter']
                }]->(target)
                // 创建从 target 到 source 的 Edge 关系
                CREATE (target)-[r2:Edge {
                    id: toInteger(row['Consecutive number']),
                    color: row['Connection: Cross-section / diameter']
                }]->(source)
                """
                
                session.run(query, file_url=file_url)
                
                # 3. 验证导入结果
                print("\n验证导入结果...")
                stats = session.run("""
                    MATCH (n:Vertex)
                    RETURN count(n) as nodes
                """).single()
                
                edges = session.run("""
                    MATCH ()-[r:Edge]->()
                    RETURN count(r) as edges
                """).single()
                
                print(f"导入完成:")
                print(f"- 创建了 {stats['nodes']} 个节点")
                print(f"- 创建了 {edges['edges']} 个关系")
                
            except ServiceUnavailable as e:
                print(f"Neo4j连接失败: {e}")
                raise
            except Exception as e:
                print(f"导入过程中出错: {e}")
                raise
            finally:
                print("\n提示: 可以使用以下查询分析导入的数据:")
                print("""
1. 查看所有节点:
MATCH (v:Vertex)
RETURN v LIMIT 10

2. 查看所有关系:
MATCH ()-[r:Edge]->()
RETURN r LIMIT 10

3. 按Function分组统计节点:
MATCH (v:Vertex)
RETURN v.Function as function, count(*) as count
ORDER BY count DESC
                """)

    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()

def main():
    """
    CSV数据导入工具入口
    
    用法:
    1. 使用默认配置:
       python import_csv_data.py --csv_path data/SmartWiringzta.csv
       
    2. 自定义Neo4j连接:
       python import_csv_data.py --csv_path data/SmartWiringzta.csv --neo4j_uri bolt://localhost:7687
    """
    parser = argparse.ArgumentParser(description='从CSV文件导入数据到Neo4j图数据库')
    
    # CSV文件路径
    parser.add_argument('--csv_path', required=True,
                       help='CSV文件路径')
    
    # Neo4j参数
    parser.add_argument('--neo4j_uri', default=NEO4J_URI,
                       help='Neo4j连接URI')
    parser.add_argument('--neo4j_user', default=NEO4J_USER,
                       help='Neo4j用户名')
    parser.add_argument('--neo4j_password', default=NEO4J_PASSWORD,
                       help='Neo4j密码')

    args = parser.parse_args()

    importer = CsvDataImporter(
        uri=args.neo4j_uri,
        user=args.neo4j_user,
        password=args.neo4j_password
    )

    try:
        importer.import_csv(args.csv_path)
    finally:
        importer.close()

if __name__ == "__main__":
    main()