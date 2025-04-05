import argparse
import json
import logging
from neo4j import GraphDatabase
import pymysql
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_CONFIG, MYSQL_CONFIG
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_sim.log'),
        logging.StreamHandler()
    ]
)

class SimulationSyncer:
    def __init__(self, mysql_config=None, neo4j_uri=None, neo4j_user=None, neo4j_password=None):
        """初始化同步器,支持使用默认配置或自定义配置"""
        self.mysql_config = mysql_config or MYSQL_CONFIG
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri or NEO4J_URI,
            auth=(neo4j_user or NEO4J_USER, neo4j_password or NEO4J_PASSWORD),
            **NEO4J_CONFIG
        )
        self.logger = logging.getLogger(__name__)

    def connect_mysql(self):
        try:
            self.logger.info(f"尝试连接MySQL,配置信息: {self.mysql_config}")
            self.mysql_conn = pymysql.connect(**self.mysql_config)
            self.logger.info("MySQL连接成功!")
            return True
        except pymysql.Error as e:
            self.logger.error(f"连接MySQL失败,错误详情: {e}")
            self.logger.error(f"错误代码: {e.args[0]}")
            self.logger.error(f"错误消息: {e.args[1]}")
            return False

    def fetch_simulation_data(self):
        cursor = self.mysql_conn.cursor(pymysql.cursors.DictCursor)
        
        try:
            # 获取设备类型
            self.logger.info("正在获取设备类型数据...")
            cursor.execute("SELECT * FROM device_types")
            device_types = cursor.fetchall()
            self.logger.info(f"获取到{len(device_types)}个设备类型")
                
            # 获取设备
            self.logger.info("正在获取设备数据...")
            cursor.execute("SELECT * FROM devices")
            devices = cursor.fetchall()
            self.logger.info(f"获取到{len(devices)}个设备")

            # 获取设备类型点位配置
            self.logger.info("正在获取点位配置数据...")
            cursor.execute("""
                SELECT dtp.*, dt.type_name
                FROM device_type_points dtp
                JOIN device_types dt ON dtp.device_type_id = dt.id
            """)
            points = cursor.fetchall()
            self.logger.info(f"获取到{len(points)}个点位配置")

            # 获取面板设备内部连接数据
            self.logger.info("正在获取面板设备内部连接数据...")
            cursor.execute("SELECT * FROM panel_device_inner")
            panel_connections = cursor.fetchall()
            self.logger.info(f"获取到{len(panel_connections)}个面板连接配置")

            # 数据验证
            self._validate_data(device_types, devices, points)
            
            cursor.close()
            return device_types, devices, points, panel_connections
            
        except pymysql.Error as e:
            self.logger.error(f"获取数据时发生错误: {e}")
            if cursor:
                cursor.close()
            raise

    def process_panel_connections(self, panel_connections):
        """处理面板设备内部连接数据"""
        processed_connections = []
        for conn in panel_connections:
            try:
                # 解析JSON数据
                connections = json.loads(conn['connections']) if isinstance(conn['connections'], str) else conn['connections']
                for connection in connections:
                    if not isinstance(connection, dict):
                        self.logger.warning(f"跳过无效的连接数据: {connection}")
                        continue
                        
                    if 'from' not in connection or 'to' not in connection or 'type' not in connection:
                        self.logger.warning(f"连接数据缺少必要字段: {connection}")
                        continue
                        
                    processed_connections.append({
                        'from_terminal': connection['from'],
                        'to_terminal': connection['to'],
                        'connection_type': connection['type'],
                        'device_id': conn.get('device_id'),
                        'panel_id': conn.get('panel_id')
                    })
            except json.JSONDecodeError as e:
                self.logger.error(f"解析连接数据时发生错误: {e}")
                self.logger.error(f"原始数据: {conn['connections']}")
                continue
            except Exception as e:
                self.logger.error(f"处理连接数据时发生未知错误: {e}")
                continue
                
        return processed_connections

    def _validate_data(self, device_types, devices, points):
        """验证数据的完整性和有效性"""
        self.logger.info("开始验证数据...")
        
        # 验证设备类型引用
        type_ids = {dt['id'] for dt in device_types}
        invalid_devices = [d for d in devices if d['type_id'] not in type_ids]
        if invalid_devices:
            self.logger.warning(f"发现{len(invalid_devices)}个设备引用了不存在的设备类型")
            for dev in invalid_devices:
                self.logger.warning(f"设备ID {dev['id']} 引用了不存在的类型ID {dev['type_id']}")

        # 验证点位配置
        invalid_points = [p for p in points if p['device_type_id'] not in type_ids]
        if invalid_points:
            self.logger.warning(f"发现{len(invalid_points)}个点位配置引用了不存在的设备类型")

        self.logger.info("数据验证完成")

    def sync_to_neo4j(self, device_types, devices, points, panel_connections):
        # 首先确保约束存在
        self.ensure_constraints()
        
        with self.neo4j_driver.session() as session:
            # 创建仿真设备节点
            self.logger.info("开始创建仿真节点...")
            session.execute_write(self._create_simulation_vertices, devices, points)
            
            # 创建节点间的连接关系
            self.logger.info("开始创建节点间连接关系...")
            session.execute_write(self._create_connections, devices, points)
            
            # 处理并创建面板设备内部连接
            self.logger.info("开始处理面板设备内部连接...")
            processed_connections = self.process_panel_connections(panel_connections)
            if processed_connections:
                self.logger.info(f"创建{len(processed_connections)}个面板内部连接...")
                session.execute_write(self._create_panel_connections, processed_connections)
            
            # 查询并显示节点信息
            self.logger.info("\n已创建的节点信息:")
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
                    self.logger.info(f"\n{current_layer}层节点:")
                self.logger.info(f"  - {record['name']}: {record['unit_type']}类型单元 (设备{record['device']}, 索引: {record['point']}, 类型: {record['type']})")
            
            # 显示节点统计信息
            stats = session.run("""
                MATCH (v:Vertex)
                WITH v.UnitType as unit_type, v.type as type, count(*) as count
                RETURN unit_type, type, count
                ORDER BY unit_type
            """)
            
            self.logger.info("\n节点统计:")
            for record in stats:
                self.logger.info(f"- {record['unit_type']}类型节点 ({record['type']}): {record['count']}个")

            # 显示连接关系统计（包括面板内部连接）
            conn_stats = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as count
            """)
            
            self.logger.info("\n连接关系统计:")
            for record in conn_stats:
                self.logger.info(f"- {record['rel_type']}类型关系: {record['count']}个")

    @staticmethod
    def _create_panel_connections(tx, connections):
        """创建面板设备内部连接"""
        for conn in connections:
            # 创建面板内部连接关系
            tx.run("""
                MATCH (v1:Vertex {DeviceId: $device_id, Terminal: $from_terminal}),
                      (v2:Vertex {DeviceId: $device_id, Terminal: $to_terminal})
                CREATE (v1)-[r:PANEL_CONNECTION {
                    type: $connection_type,
                    created_at: $timestamp,
                    panel_id: $panel_id
                }]->(v2)
            """, {
                'device_id': conn['device_id'],
                'from_terminal': conn['from_terminal'],
                'to_terminal': conn['to_terminal'],
                'connection_type': conn['connection_type'],
                'panel_id': conn['panel_id'],
                'timestamp': datetime.now().isoformat()
            })

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
                        IsEnabled: true,
                        LastUpdate: $last_update
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
                    'initial_voltage': 0.0,
                    'last_update': datetime.now().isoformat()
                })

    @staticmethod
    def _create_connections(tx, devices, points):
        """创建节点间的连接关系"""
        # 创建同一设备内部点位之间的连接（优化后的查询）
        tx.run("""
            MATCH (v1:Vertex {type: 'sim'})
            MATCH (v2:Vertex {type: 'sim'})
            WHERE v1.DeviceId = v2.DeviceId 
              AND v1.PointIndex < v2.PointIndex
              AND id(v1) < id(v2)
            CREATE (v1)-[:INTERNAL_CONNECTION {
                type: 'internal',
                created_at: $timestamp
            }]->(v2)
        """, {'timestamp': datetime.now().isoformat()})

        # 创建相邻设备之间的连接（优化后的查询）
        tx.run("""
            MATCH (v1:Vertex {type: 'sim'})
            MATCH (v2:Vertex {type: 'sim'})
            WHERE v1.DeviceId < v2.DeviceId 
              AND abs(v1.DeviceId - v2.DeviceId) = 1
              AND id(v1) < id(v2)
            CREATE (v1)-[:ADJACENT_CONNECTION {
                type: 'adjacent',
                created_at: $timestamp
            }]->(v2)
        """, {'timestamp': datetime.now().isoformat()})

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
                       help='MySQL密码')
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

    logger = logging.getLogger(__name__)
    logger.info("开始同步仿真数据...")
    logger.info(f"MySQL连接: {args.mysql_host}")
    logger.info(f"Neo4j连接: {args.neo4j_uri}")

    syncer = SimulationSyncer(
        mysql_config=mysql_config,
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password
    )

    try:
        if not syncer.connect_mysql():
            return
        logger.info("1. 仿真设备及单元\n")
        device_types, devices, points, panel_connections = syncer.fetch_simulation_data()
        syncer.sync_to_neo4j(device_types, devices, points, panel_connections)
        logger.info("\n提示: 在Neo4j浏览器中可以使用以下查询来分析节点:")
        logger.info("""
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

4. 查看节点间的连接关系:
MATCH p=()-[r:INTERNAL_CONNECTION|ADJACENT_CONNECTION|PANEL_CONNECTION]->()
RETURN p LIMIT 100

5. 按设备分组查看连接关系:
MATCH (v1:Vertex)-[r]->(v2:Vertex)
RETURN v1.DeviceId as device, type(r) as rel_type, count(r) as count
ORDER BY device

6. 查找孤立节点(没有任何连接的节点):
MATCH (v:Vertex)
WHERE NOT (v)-[]-()
RETURN v

7. 查看面板内部连接:
MATCH (v1:Vertex)-[r:PANEL_CONNECTION]->(v2:Vertex)
RETURN v1.name, type(r), r.type, v2.name
ORDER BY r.type

8. 按连接类型统计面板连接:
MATCH ()-[r:PANEL_CONNECTION]->()
RETURN r.type as connection_type, count(r) as count
ORDER BY count DESC
        """)
    finally:
        syncer.close()

if __name__ == "__main__":
    main()