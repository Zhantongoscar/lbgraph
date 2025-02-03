import argparse
from neo4j import GraphDatabase
import mysql.connector
from mysql.connector import Error

class SimulationSyncer:
    def __init__(self, mysql_config, neo4j_uri, neo4j_user, neo4j_password):
        self.mysql_config = mysql_config
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri, 
            auth=(neo4j_user, neo4j_password)
        )

    def connect_mysql(self):
        try:
            self.mysql_conn = mysql.connector.connect(**self.mysql_config)
            return True
        except Error as e:
            print(f"连接MySQL失败: {e}")
            return False

    def fetch_simulation_data(self):
        cursor = self.mysql_conn.cursor(dictionary=True)
        
        # 获取设备类型
        cursor.execute("SELECT * FROM device_types")
        device_types = cursor.fetchall()
        
        # 获取设备
        cursor.execute("SELECT * FROM devices")
        devices = cursor.fetchall()
        
        cursor.close()
        return device_types, devices

    def sync_to_neo4j(self, device_types, devices):
        with self.neo4j_driver.session() as session:
            # 同步设备类型
            session.write_transaction(self._sync_device_types, device_types)
            # 同步设备
            session.write_transaction(self._sync_devices, devices)

    @staticmethod
    def _sync_device_types(tx, device_types):
        # 删除旧数据
        tx.run("MATCH (t:DeviceType) DETACH DELETE t")
        
        # 插入新数据
        for dt in device_types:
            tx.run("""
                CREATE (t:DeviceType {
                    id: $id,
                    type_name: $type_name,
                    point_count: $point_count,
                    description: $description
                })
            """, **dt)

    @staticmethod
    def _sync_devices(tx, devices):
        # 删除旧数据
        tx.run("MATCH (d:Device) DETACH DELETE d")
        
        # 插入新数据
        for d in devices:
            tx.run("""
                CREATE (d:Device {
                    id: $id,
                    project_name: $project_name,
                    module_type: $module_type,
                    serial_number: $serial_number,
                    type_id: $type_id,
                    status: $status,
                    rssi: $rssi
                })
            """, **d)

    def close(self):
        if hasattr(self, 'mysql_conn'):
            self.mysql_conn.close()
        if hasattr(self, 'neo4j_driver'):
            self.neo4j_driver.close()

def main():
    parser = argparse.ArgumentParser(description='同步仿真数据到Neo4j')
    parser.add_argument('--mysql_host', default='192.168.35.10',
                       help='MySQL主机地址')
    parser.add_argument('--mysql_user', default='root',
                       help='MySQL用户名')
    parser.add_argument('--mysql_password', default='13701033228',
                       help='MySQL密码')
    parser.add_argument('--mysql_db', default='lbfat',
                       help='MySQL数据库名')
    parser.add_argument('--neo4j_uri', required=True,
                       help='Neo4j连接URI')
    parser.add_argument('--neo4j_user', required=True,
                       help='Neo4j用户名')
    parser.add_argument('--neo4j_password', required=True,
                       help='Neo4j密码')

    args = parser.parse_args()

    mysql_config = {
        'host': args.mysql_host,
        'user': args.mysql_user,
        'password': args.mysql_password,
        'database': args.mysql_db
    }

    syncer = SimulationSyncer(
        mysql_config,
        args.neo4j_uri,
        args.neo4j_user,
        args.neo4j_password
    )

    try:
        if not syncer.connect_mysql():
            return

        device_types, devices = syncer.fetch_simulation_data()
        syncer.sync_to_neo4j(device_types, devices)
        print("数据同步成功！")
    finally:
        syncer.close()

if __name__ == "__main__":
    main()