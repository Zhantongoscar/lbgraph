from main import driver

def analyze_cabinet_topology():
    try:
        with driver.session() as session:
            print("========== 电柜拓扑分析 ==========\n")
            
            # 1. 检查Location属性分布
            print("1. Location属性分布:")
            result = session.run("""
                MATCH (n:Vertex)
                WITH n.Location as location, count(*) as count
                WHERE location IS NOT NULL
                RETURN location, count
                ORDER BY count DESC
            """)
            for record in result:
                print(f"位置: {record['location']}, 设备数量: {record['count']}")
            
            print("\n2. Neo4j Browser查询语句:")
            print("""
// 查看电柜内设备(假设电柜位置以K1开头)
MATCH (n:Vertex)
WHERE n.Location STARTS WITH 'K1'
RETURN n

// 查看电柜外设备
MATCH (n:Vertex)
WHERE NOT n.Location STARTS WITH 'K1' OR n.Location IS NULL
RETURN n

// 查看电柜内外连接关系
MATCH (n:Vertex)-[r:Edge]->(m:Vertex)
WHERE (n.Location STARTS WITH 'K1' AND NOT m.Location STARTS WITH 'K1')
   OR (NOT n.Location STARTS WITH 'K1' AND m.Location STARTS WITH 'K1')
RETURN n, r, m
            """)
            
            # 3. 分析电柜内外设备连接
            print("\n3. 电柜内外设备连接分析:")
            result = session.run("""
                MATCH (n:Vertex)-[r:Edge]->(m:Vertex)
                WHERE (n.Location STARTS WITH 'K1' AND NOT m.Location STARTS WITH 'K1')
                   OR (NOT n.Location STARTS WITH 'K1' AND m.Location STARTS WITH 'K1')
                RETURN n.Device as source_device, n.Location as source_location,
                       m.Device as target_device, m.Location as target_location,
                       count(*) as connection_count
                ORDER BY connection_count DESC
                LIMIT 10
            """)
            print("前10个电柜内外连接:")
            for record in result:
                print(f"{record['source_device']}({record['source_location']}) -> "
                      f"{record['target_device']}({record['target_location']}): "
                      f"{record['connection_count']}次")
            
            # 4. 建议的属性补充
            print("\n4. 建议补充的属性:")
            print("""
为支持仿真测试,建议添加以下属性:
1. isExternal: Boolean - 标识是否为外部设备
2. simulationReplace: String - 对应的仿真设备ID
3. deviceType: String - 设备类型(实物设备/仿真设备)
4. testUnit: String - 所属测试单元
5. testMode: String - 测试模式(正常/仿真)

示例Cypher语句:
// 添加新属性
MATCH (n:Vertex)
WHERE NOT n.Location STARTS WITH 'K1'
SET n.isExternal = true,
    n.deviceType = 'physical'

// 添加仿真设备
CREATE (sim:Vertex {
    name: 'SIM001',
    Device: 'SimDevice',
    Function: 'Test',
    deviceType: 'simulation',
    testUnit: 'Unit1',
    testMode: 'simulation'
})

// 替换外部设备连接
MATCH (n:Vertex {isExternal: true})-[r:Edge]->(m:Vertex)
MATCH (sim:Vertex {deviceType: 'simulation'})
WHERE sim.simulationReplace = n.name
CREATE (sim)-[:Edge]->(m)
DELETE r
            """)

            # 5. 终端查询命令
            print("\n5. 终端查询命令:")
            print("""
# 查看电柜内设备:
python -c "
from main import driver
with driver.session() as session:
    result = session.run('''
        MATCH (n:Vertex)
        WHERE n.Location STARTS WITH 'K1'
        RETURN n.name, n.Device, n.Location
    ''')
    for record in result:
        print(record)
"

# 查看电柜外设备:
python -c "
from main import driver
with driver.session() as session:
    result = session.run('''
        MATCH (n:Vertex)
        WHERE NOT n.Location STARTS WITH 'K1' OR n.Location IS NULL
        RETURN n.name, n.Device, n.Location
    ''')
    for record in result:
        print(record)
"
            """)

    except Exception as e:
        print(f"错误: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    analyze_cabinet_topology()