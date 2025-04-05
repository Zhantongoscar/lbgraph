#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
from config import MYSQL_CONFIG
import logging
from datetime import datetime

# 配置日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 设备类型对照表，使用Function和Device的组合作为键
DEVICE_TYPE_MAPPINGS = {
    'A02': {
        'A1': 'EL2809',
        'A2': 'EL2809',
        'A3': 'EL1809',
        'A4': 'EL3204',
        'A5': 'EL3403'
    },
    'O01': {
        'A1': 'EL1859',
        'A2': 'EL5151'
    },
    'O02': {
        'A20-X1': 'GV204_X1',
        'A20-X2': 'GV204_X2',
        'A20-X3': 'GV204_X3',
        'A20-X4': 'GV204_X4'
    },
    'P01': {
        'T1': 'EL9400',
        'T2': 'EL9100',
        'A0': 'EK1101',
        'A0.0': 'EK1101',
        'A0.1': '01005N',
        'A0.2': 'EK1122',
        'A0.10': '1005N'
    },
    'Q01': {
        'A1': 'EL1859',
        'A2': 'EL1551',
        'A3': 'EL3064',
        'A4': 'EL1859',
        'A5': 'EL4132',
        'A6': 'EL8601-8411',
        'A7': 'EL1859',
        'A8': 'EL4132',
        'A9': 'EL8601-8411',
        'A10': 'EL4004',
        'A11': 'EL3064',
        'A12': 'EL3162',
        'A13': 'EL1004'
    },
    'Q15': {
        'A1': 'EL2809',
        'A2': 'EL1809',
        'A3': 'EL4004',
        'A4': 'EL3064',
        'A5': 'EL4004',
        'A6': 'EL3064',
        'A7': 'EL4004',
        'A8': 'EL3064',
        'A9': 'EL1859',
        'A10': 'EL4004',
        'A11': 'EL3064',
        'A12': 'EL3064',
        'A21': 'FLK-D25',
        'A22': 'FLK-D25',
        'A23': 'FLK-D25',
        'A24': 'FLK-D25',
        'A25': 'FLK-D25'
    },
    'S02': {
        'A1': 'EL1859'
    },
    'V01': {
        'A1': 'EL2809',
        'A1.1': 'EL9100',
        'A2': 'EL2809',
        'A2.1': 'EL9100',
        'A3': 'EL1809',
        'A4': 'EL1809',
        'A5': 'EL1809',
        'A5.1': 'EL9100',
        'A6': 'EL3064',
        'A7': 'EL3064',
        'A8': 'EL3314',
        'A13': 'Profib',
        'A13-X1': 'EL6731',
        'A14': 'EL9011'
    }
}

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = pymysql.connect(
            **MYSQL_CONFIG,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info("数据库连接成功")
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        raise

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
            function = (device['Function'] or '').strip()
            device_name = (device['Device'] or '').strip()
            current_type = device['Type']
            
            # 匹配设备类型
            new_type = None
            if function in DEVICE_TYPE_MAPPINGS:
                if device_name in DEVICE_TYPE_MAPPINGS[function]:
                    new_type = DEVICE_TYPE_MAPPINGS[function][device_name]
                    
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
                    logger.info(f"未找到匹配: Function={function}, Device={device_name}")

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

        # 处理GV204的特殊情况
        cursor.execute("""
            UPDATE v_csv_device
            SET Type = 'GV204'
            WHERE Type LIKE 'GV204-X_'
            AND Location LIKE 'K1.%'
        """)
        gv204_count = cursor.rowcount
        logger.info(f"统一更新了 {gv204_count} 个GV204类型设备")

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