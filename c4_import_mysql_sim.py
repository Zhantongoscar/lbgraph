
import argparse
from neo4j import GraphDatabase
import pymysql
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_CONFIG, MYSQL_CONFIG

class SimulationSyncer:
    def __init__(self, mysql_config=None, neo4j_uri=None, neo4j_user=None, neo4j_password=None):
        """初始化同步器,支持使用默认配置或自定义配置"""
        self.mysql_config = mysql_config or MYSQL_CONFIG
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri or NEO4J_URI,
            auth=(neo4j_user or NEO4J_USER, neo4j_password or NEO4J_PASSWORD),
            **NEO4J_CONFIG
        )

    def connect_mysql(self):
        try:
            print(f"尝试连接MySQL,配置信息: {self.mysql_config}")
            self.mysql_conn = pymysql.connect(**self.mysql_config)
            print("MySQL连接成功!")
            return True
        except pymysql.Error as e:
            print(f"连接MySQL失败,错误详情: {e}")
            print(f"错误代码: {e.args[0]}")
            print(f"错误消息: {e.args[1]}")
            return False

    def fetch_simulation_data(self):
        cursor = self.mysql_conn.cursor(pymysql.cursors.DictCursor)
        
        # 获取设备类型
        cursor.execute("SELECT * FROM device_types")
        device_types = cursor.fetchall()
           
        # 获取设备
        cursor.execute("SELECT * FROM devices")
        devices = cursor.fetchall()

        # 获取设备类型点位配置
        cursor.execute("""
            SELECT dtp.*, dt.type_name
            FROM device_type_points dtp
            JOIN device_types dt ON dtp.device_type_id = dt.id
        """)
        points = cursor.fetchall()
        
        cursor.close()
        return device_types, devices, points

    def sync_to_neo4j(self, device_types, devices, points):
        # 首先确保约束存在
        self.ensure_constraints()
        
        with self.neo4j_driver.session() as session:
            # 创建仿真设备节点
            session.execute_write(self._create_simulation_vertices, devices, points)
            
            # 查询并显示节点信息
            print("\n已创建的节点信息:")
            result = session.run("""
                MATCH (v:Vertex)
                RETURN v.name as name, v.UnitType as unit_type, 
                       v.NodeLayer as layer, v.DeviceId as device,
                       v.PointIndex as point, v.type as type
                ORDER BY v.DeviceId, v.PointIndex
            """)
            
            current_layer = None
            for record in result:
                if current_layer != record["layer"]:
                    current_layer = record["layer"]
                    print(f"\n{current_layer}层节点:")
                print(f"  - {record['name']}: {record['unit_type']}类型单元 (设备{record['device']}, 索引: {record['point']}, 类型: {record['type']})")
            
            # 显示节点统计信息
            stats = session.run("""
                MATCH (v:Vertex)
                WITH v.UnitType as unit_type, v.type as type, count(*) as count
                RETURN unit_type, type, count
                ORDER BY unit_type
            """)
            
            print("\n节点统计:")
            for record in stats:
                print(f"- {record['unit_type']}类型节点 ({record['type']}): {record['count']}个")

    def ensure_constraints(self):
        """确保必要的约束存在"""
        with self.neo4j_driver.session() as session:
            session.run("""
                CREATE CONSTRAINT IF NOT EXISTS
                FOR (v:Vertex) REQUIRE v.name IS UNIQUE
            """)

    @staticmethod
    def _create_simulation_vertices(tx, devices, points):
        # 删除旧的仿真节点
        tx.run("MATCH (v:Vertex) DETACH DELETE v")
        
        # 为每个设备的每个单元创建仿真节点
        for device in devices:
            device_points = [p for p in points if p['device_type_id'] == device['type_id']]
            for point in device_points:
                # 确定单元类型(B或D)
                unit_type = 'B' if point['point_type'] == 'DO' else 'D'
                
                # 创建仿真节点
                tx.run("""
                    CREATE (v:Vertex {
                        name: $name,
                        Function: $function,
                        Location: $location,
                        Device: $device,
                        Terminal: $terminal,
                        UnitType: $unit_type,
                        DeviceId: $device_id,
                        PointIndex: $point_index,
                        Voltage: $initial_voltage,
                        NodeLayer: 'Simulation',
                        type: 'sim',
                        IsEnabled: true
                    })
                """, {
                    'name': f"SIM_{device['project_name']}+{device['module_type']}-{device['id']}:{point['point_index']}",
                    'function': unit_type,
                    'location': device['module_type'],
                    'device': str(device['id']),
                    'terminal': str(point['point_index']),
                    'unit_type': unit_type,
                    'device_id': device['id'],
                    'point_index': point['point_index'],
                    'initial_voltage': 0.0
                })

    def close(self):
        if hasattr(self, 'mysql_conn'):
            self.mysql_conn.close()
        if hasattr(self, 'neo4j_driver'):
            self.neo4j_driver.close()

def main():
    parser = argparse.ArgumentParser(description='同步仿真数据到Neo4j图数据库')
    
    # MySQL参数
    parser.add_argument('--mysql_host', default=MYSQL_CONFIG['host'],
                       help='MySQL主机地址')
    parser.add_argument('--mysql_user', default=MYSQL_CONFIG['user'],
                       help='MySQL用户名')
    parser.add_argument('--mysql_password', default=MYSQL_CONFIG['password'],
                       help='MySQL密码')
    parser.add_argument('--mysql_db', default=MYSQL_CONFIG['database'],
                       help='MySQL数据库名')
    
    # Neo4j参数
    parser.add_argument('--neo4j_uri', default=NEO4J_URI,
                       help='Neo4j连接URI')
    parser.add_argument('--neo4j_user', default=NEO4J_USER,
                       help='Neo4j用户名')
    parser.add_argument('--neo4j_password', default=NEO4J_PASSWORD,
                       help='Neo4j密码')

    args = parser.parse_args()

    mysql_config = {
        'host': args.mysql_host,
        'user': args.mysql_user,
        'password': args.mysql_password,
        'database': args.mysql_db
    }

    print("开始同步仿真数据...")
    print(f"MySQL连接: {args.mysql_host}")
    print(f"Neo4j连接: {args.neo4j_uri}")

    syncer = SimulationSyncer(
        mysql_config=mysql_config,
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password
    )

    try:
        if not syncer.connect_mysql():
            return
        print ("1 仿真设备及单元\n")
        device_types, devices, points = syncer.fetch_simulation_data()
        syncer.sync_to_neo4j(device_types, devices, points)
        print("\n提示: 在Neo4j浏览器中可以使用以下查询来分析节点:")
        print("""
1. 查看所有仿真节点:
MATCH (v:Vertex {type: 'sim'})
RETURN v

2. 按类型统计节点:
MATCH (v:Vertex)
WITH v.UnitType as unit_type, v.type as type, count(*) as count
RETURN unit_type, type, count
ORDER BY unit_type

3. 查看启用的仿真节点:
MATCH (v:Vertex {type: 'sim'})
WHERE v.IsEnabled = true
RETURN v
        """)
    finally:
        syncer.close()

if __name__ == "__main__":
    main()