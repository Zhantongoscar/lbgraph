#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
import json
import logging
from datetime import datetime
import re

# 配置日志输出到文件和控制台
log_file = f'update_type_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# EOS1550设备类型对照表
EOS1550_DEVICE_TYPES = {
    'A02A4': 'EL3204',
    'A02A5': 'EL3403',
    'O01A2': 'EL5151',
    'O02A20-X1': 'GV204-X1',  # 修正GV204的类型名称
    'O02A20-X2': 'GV204-X2',
    'O02A20-X3': 'GV204-X3',
    'O02A20-X4': 'GV204-X4',
    'P01A0': 'EK1101',
    'P01A0.0': 'EK1101',
    'P01A0.1': 'EK1005',
    'P01A0.2': 'EK1122',
    'Q01A10': 'EL4004',
    'Q01A11': 'EL3064',
    'Q01A12': 'EL3162',
    'Q01A13': 'EL1004',
    'Q01A2': 'EL5151',
    'Q01A3': 'EL3064',
    'Q01A5': 'EL4132',
    'Q01A6': 'EL8601-8411',
    'Q01A8': 'EL4132',
    'Q01A9': 'EL8601-8411',
    'Q15A21': 'FLK-D25',
    'Q15A22': 'FLK-D25',
    'Q15A23': 'FLK-D25',
    'Q15A24': 'FLK-D25',
    'Q15A25': 'FLK-D25',
    'Q15A3': 'EL4004',
    'Q15A4': 'EL3064',
    'Q15A5': 'EL4004',
    'Q15A6': 'EL3064',
    'Q15A7': 'EL4004',
    'Q15A8': 'EL3064',
    'V01A1.1': 'EL9100',
    'V01A13-X1': 'EL6731',
    'V01A2.1': 'EL9100',
    'V01A5.1': 'EL9100',
    'V01A6': 'EL3064',
    'V01A7': 'EL3064',
    'V01A8': 'EL3314'
}

def get_db_connection():
    """获取数据库连接"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)['mysql']
        conn = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info("数据库连接成功")
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        raise

def extract_device_key(function, device):
    """从Function和Device提取设备类型匹配键"""
    if not function or not device:
        return None
    
    # 组合完整标识符
    device_id = f"{function}{device}"
    
    # 使用正则表达式提取匹配键
    # 匹配 Function + Device 编号部分
    match = re.match(r'([A-Z][0-9]+[A-Z][0-9]+(?:\.[0-9]+)?(?:-[A-Z][0-9]+)?)', device_id)
    if match:
        return match.group(1)
    return None

def update_device_types(cursor):
    """更新设备类型"""
    try:
        # 获取所有需要更新的设备
        cursor.execute("""
            SELECT id, Function, Device, Type 
            FROM v_csv_device 
            WHERE Location LIKE 'K1.%'
            ORDER BY Function, Device
        """)
        devices = cursor.fetchall()
        logger.info(f"找到 {len(devices)} 个设备需要更新")

        # 打印前10个设备的详细信息
        logger.info("前10个设备的信息:")
        for i, device in enumerate(devices[:10]):
            logger.info(f"设备{i+1}: Function='{device['Function']}', Device='{device['Device']}', "
                      f"Type='{device['Type']}'")

        # 统计更新数量
        update_count = 0
        no_match_count = 0

        # 处理每个设备
        for device in devices:
            device_id = device['id']
            function = device['Function'] or ''
            device_name = device['Device'] or ''
            current_type = device['Type']
            
            # 提取匹配键
            lookup_key = extract_device_key(function, device_name)
            if lookup_key:
                logger.debug(f"处理设备: {function}{device_name}, 提取的匹配键: {lookup_key}")
            
                # 在对照表中查找匹配项
                new_type = None
                for key, type_value in EOS1550_DEVICE_TYPES.items():
                    if lookup_key.startswith(key):
                        new_type = type_value
                        break
                
                # 如果找到匹配的类型并且与当前类型不同，则更新
                if new_type and new_type != current_type:
                    cursor.execute("""
                        UPDATE v_csv_device 
                        SET Type = %s 
                        WHERE id = %s
                    """, (new_type, device_id))
                    
                    logger.info(f"更新设备: {function}{device_name} - Type: {current_type} -> {new_type}")
                    update_count += 1
                else:
                    no_match_count += 1
                    if function:  # 只记录有Function值的设备
                        logger.info(f"未找到匹配: {function}{device_name}")
            else:
                no_match_count += 1
                logger.debug(f"无法提取匹配键: {function}{device_name}")

        logger.info(f"更新完成: 更新 {update_count} 个设备类型, {no_match_count} 个设备未匹配")
        return update_count, no_match_count

    except Exception as e:
        logger.error(f"更新设备类型时出错: {str(e)}")
        raise

def update_devpoint_types(cursor):
    """更新设备端点类型"""
    try:
        # 先清空现有的type值
        cursor.execute("UPDATE v_csv_devpoint SET Type = NULL WHERE Location LIKE 'K1.%'")
        logger.info("已清空现有的type值")

        # 检查v_csv_device表中的Type字段情况
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(Type) as with_type,
                   COUNT(DISTINCT Type) as unique_types
            FROM v_csv_device
            WHERE Location LIKE 'K1.%'
        """)
        type_stats = cursor.fetchone()
        logger.info(f"v_csv_device表统计: 总记录数={type_stats['total']}, "
                   f"有Type值的记录数={type_stats['with_type']}, "
                   f"不同Type值数量={type_stats['unique_types']}")

        # 查看device_types表的情况
        cursor.execute("SELECT COUNT(*) as count, GROUP_CONCAT(type_name) as types FROM device_types")
        dt_stats = cursor.fetchone()
        logger.info(f"device_types表包含 {dt_stats['count']} 个类型: {dt_stats['types']}")

        # 检查类型匹配情况
        cursor.execute("""
            SELECT vd.Type, dt.type_name, COUNT(*) as count
            FROM v_csv_device vd
            LEFT JOIN device_types dt ON vd.Type = dt.type_name
            WHERE vd.Location LIKE 'K1.%'
            GROUP BY vd.Type, dt.type_name
        """)
        matches = cursor.fetchall()
        logger.info("类型匹配情况:")
        for match in matches:
            logger.info(f"设备类型: {match['Type']}, "
                      f"匹配到的类型: {match['type_name']}, "
                      f"数量: {match['count']}")

        # 更新v_csv_devpoint的type字段
        update_sql = """
            UPDATE v_csv_devpoint vdp
            JOIN v_csv_device vd ON vdp.belongtoDevice = vd.fdid
            JOIN device_types dt ON vd.Type = dt.type_name
            JOIN device_type_points dtp ON dt.id = dtp.device_type_id 
                AND vdp.Terminal = dtp.point_index
            SET vdp.Type = dtp.point_type
            WHERE vdp.Location LIKE 'K1.%'
        """
        cursor.execute(update_sql)
        update_count = cursor.rowcount
        logger.info(f"已更新 {update_count} 个设备端点的类型")

        # 查看部分更新成功的记录
        cursor.execute("""
            SELECT vdp.belongtoDevice, vdp.Terminal, vdp.Type,
                   vd.Type as device_type, dtp.point_type
            FROM v_csv_devpoint vdp
            JOIN v_csv_device vd ON vdp.belongtoDevice = vd.fdid
            JOIN device_types dt ON vd.Type = dt.type_name
            JOIN device_type_points dtp ON dt.id = dtp.device_type_id
            WHERE vdp.Location LIKE 'K1.%'
            LIMIT 5
        """)
        samples = cursor.fetchall()
        logger.info("更新成功的示例记录:")
        for sample in samples:
            logger.info(f"设备={sample['belongtoDevice']}, "
                      f"端子={sample['Terminal']}, "
                      f"类型={sample['Type']}, "
                      f"设备类型={sample['device_type']}, "
                      f"点位类型={sample['point_type']}")

        # 获取未更新的端点数量
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM v_csv_devpoint
            WHERE Location LIKE 'K1.%' AND Type IS NULL
        """)
        null_count = cursor.fetchone()['count']
        logger.info(f"仍有 {null_count} 个设备端点未找到匹配的类型")

        # 查看部分未匹配的记录
        cursor.execute("""
            SELECT vdp.belongtoDevice, vdp.Terminal, vd.Type as device_type
            FROM v_csv_devpoint vdp
            LEFT JOIN v_csv_device vd ON vdp.belongtoDevice = vd.fdid
            WHERE vdp.Location LIKE 'K1.%' 
            AND vdp.Type IS NULL
            LIMIT 5
        """)
        unmatched = cursor.fetchall()
        logger.info("未匹配的示例记录:")
        for record in unmatched:
            logger.info(f"设备={record['belongtoDevice']}, "
                      f"端子={record['Terminal']}, "
                      f"设备类型={record['device_type']}")

        return update_count, null_count

    except Exception as e:
        logger.error(f"更新设备端点类型时出错: {str(e)}")
        raise

def main():
    """主函数"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. 更新设备类型
            logger.info("开始更新设备类型...")
            update_count, no_match_count = update_device_types(cursor)
            conn.commit()
            logger.info("设备类型更新已提交到数据库")
            
            # 显示设备类型更新统计
            print("\n设备类型更新结果统计:")
            print(f"总共处理的设备数: {update_count + no_match_count}")
            print(f"成功更新的设备数: {update_count}")
            print(f"未找到匹配的设备数: {no_match_count}")

            # 2. 更新设备端点类型
            logger.info("\n开始更新设备端点类型...")
            point_update_count, point_null_count = update_devpoint_types(cursor)
            conn.commit()
            logger.info("设备端点类型更新已提交到数据库")

            # 显示端点类型更新统计
            print("\n设备端点类型更新结果统计:")
            print(f"已更新的端点数: {point_update_count}")
            print(f"未匹配类型的端点数: {point_null_count}")
            
        return 0

    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        if conn:
            conn.rollback()
        return 1

    finally:
        if conn:
            conn.close()
            logger.info("数据库连接已关闭")

if __name__ == "__main__":
    sys.exit(main())