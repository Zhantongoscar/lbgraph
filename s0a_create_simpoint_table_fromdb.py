#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
from config import MYSQL_CONFIG

def create_simpoint_table(connection):
    """创建v_simpoint表"""
    try:
        with connection.cursor() as cursor:
            # 删除已存在的表
            cursor.execute("DROP TABLE IF EXISTS `v_simpoint`")
            
            # 创建新表
            create_table_sql = """
            CREATE TABLE `v_simpoint` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `raw` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
              `ftid` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
              `belongtoDevice` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
              `Function` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
              `Location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
              `Device` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
              `Terminal` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
              `Type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
              `voltage` double NULL DEFAULT 0,
              `current` double NULL DEFAULT 0,
              `resistance` double NULL DEFAULT 0,
              `isInPanel` tinyint(1) NULL DEFAULT 0,
              `isSocket` tinyint(1) NULL DEFAULT 0,
              `isSetPoint` tinyint(1) NULL DEFAULT 0,
              `isSensePoint` tinyint(1) NULL DEFAULT 0,
              PRIMARY KEY (`id`) USING BTREE,
              INDEX `idx_ftid`(`ftid`) USING BTREE,
              INDEX `idx_location_device`(`Location`, `Device`) USING BTREE
            ) ENGINE = InnoDB AUTO_INCREMENT = 1 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;
            """
            cursor.execute(create_table_sql)
            connection.commit()
            print("Created v_simpoint table successfully")
    except Exception as e:
        print(f"Error creating simpoint table: {e}")
        connection.rollback()

def insert_simpoints(connection):
    """插入模拟点位数据"""
    try:
        with connection.cursor() as cursor:
            # 获取所有设备
            cursor.execute("SELECT id, module_type, serial_number, project_name FROM devices")
            devices = cursor.fetchall()
            
            inserted_count = 0
            for device in devices:
                # 获取设备对应的点位
                cursor.execute("SELECT * FROM device_type_points WHERE device_type_id = %s", (device['id'],))
                points = cursor.fetchall()
                
                for point in points:
                    # 构造设备名称：module_type + serial_number
                    device_name = f"{device['module_type']}{device['serial_number']}"
                    
                    # 构造raw：使用point中的原始数据
                    raw = point.get('raw', '')

                    # 构造belongtoDevice：=Function+Location-device_name
                    belongto_device = f"={device['project_name']}+Sim-{device_name}"
                    
                    # 使用point_index作为Terminal的值
                    terminal = str(point.get('point_index', ''))
                    
                    # 构造ftid：belongtoDevice加上:加上Terminal
                    ftid = f"{belongto_device}:{terminal}"
                    
                    insert_sql = """
                    INSERT INTO v_simpoint 
                    (raw, ftid, belongtoDevice, Function, Location, Device, Terminal, Type,
                    voltage, current, resistance, isInPanel, isSocket, isSetPoint, isSensePoint)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_sql, (
                        raw,
                        ftid,
                        belongto_device,
                        device['project_name'],  # Function 使用 project_name
                        'Sim',  # Location 固定为 Sim
                        device_name,  # Device
                        terminal,  # 使用point_index作为Terminal
                        point.get('sim_type', ''),  # Type使用sim_type
                        point.get('voltage', 0),
                        point.get('current', 0),
                        point.get('resistance', 0),
                        point.get('isInPanel', 0),
                        point.get('isSocket', 0),
                        point.get('isSetPoint', 0),
                        point.get('isSensePoint', 0)
                    ))
                    inserted_count += 1

            connection.commit()
            print(f"Inserted {inserted_count} simulation points successfully")
            
    except Exception as e:
        print(f"Error inserting simulation points: {e}")
        connection.rollback()

def main():
    """主函数"""
    try:
        # 连接到MySQL数据库
        connection = pymysql.connect(
            **MYSQL_CONFIG,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("Connected to MySQL successfully")

        create_simpoint_table(connection)
        insert_simpoints(connection)
        
        connection.close()
        print("Database connection closed")
        
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")

if __name__ == "__main__":
    main()