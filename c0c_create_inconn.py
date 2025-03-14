
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pymysql
import json
import logging
from datetime import datetime

# 配置日志输出到文件和控制台
log_file = f'create_inconn_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)['mysql']
    return pymysql.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def create_internal_connections():
    conn = None
    try:
        # 加载配置并连接数据库
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)['mysql']
        conn = get_db_connection()
        logger.info(f"已连接到数据库 {config['host']}")

        with conn.cursor() as cursor:
            try:
                # 从v_csv_device表读取设备数据
                logger.info("正在读取设备数据...")
                cursor.execute("""
                    SELECT fdid, Function, Location, Device, Type
                    FROM v_csv_device
                    WHERE isInPanel = 1
                    AND Location LIKE 'K1.%'
                """)
                devices = cursor.fetchall()
                logger.info(f"找到 {len(devices)} 个设备")

                # 获取每个设备的端子
                total_connections = 0
                for device in devices:
                    try:
                        logger.info(f"\n处理设备: {device['Device']} (位置: {device['Location']})")
                        
                        # 获取设备的所有端子
                        cursor.execute("""
                            SELECT ftid, Terminal, Type
                            FROM v_csv_devpoint
                            WHERE belongtoDevice = %s
                            AND Terminal IS NOT NULL
                            ORDER BY Terminal
                        """, (device['fdid'],))
                        terminals = cursor.fetchall()
                        logger.info(f"找到 {len(terminals)} 个端子")

                        if len(terminals) < 2:
                            continue

                        # 根据端子类型分组
                        type_groups = {}
                        for terminal in terminals:
                            term_type = terminal['Terminal'][0] if terminal['Terminal'] else None
                            if term_type in ['A', 'D', 'L', 'K', 'T']:
                                if term_type not in type_groups:
                                    type_groups[term_type] = []
                                type_groups[term_type].append(terminal)

                        # 处理相邻端子的连接
                        for type_name, type_terminals in type_groups.items():
                            # 对同类型的端子按Terminal排序
                            sorted_terminals = sorted(type_terminals, key=lambda x: x['Terminal'])
                            
                            # 连接相邻的端子
                            for i in range(len(sorted_terminals) - 1):
                                t1 = sorted_terminals[i]
                                t2 = sorted_terminals[i + 1]
                                try:
                                    # 插入单个连接
                                    insert_sql = """
                                        INSERT INTO v_csv_conn
                                        (connNo, source, target, color, isCable, isInPanel, connType,
                                         voltage, current, resistance)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """
                                    cursor.execute(insert_sql, (
                                        f"{device['fdid']}-{type_name}CONN{total_connections}",
                                        t1['ftid'],
                                        t2['ftid'],
                                        None,
                                        0,
                                        1,
                                        'internal',
                                        0,
                                        0,
                                        0
                                    ))
                                    total_connections += 1
                                        
                                except Exception as e:
                                    logger.error(f"创建连接时出错 ({t1['ftid']} -> {t2['ftid']}): {str(e)}")
                                    continue
                                    
                        # 提交剩余的连接
                        conn.commit()
                        logger.info(f"设备 {device['Device']} 处理完成，创建了 {total_connections} 个连接")
                            
                    except Exception as e:
                        logger.error(f"处理设备 {device['Device']} 时出错: {str(e)}")
                        continue

                logger.info(f"\n总共创建了 {total_connections} 个内部连接")
                return 0
                
            except Exception as e:
                logger.error(f"处理数据时出错: {str(e)}")
                return 1

    except Exception as e:
        logger.error(f"错误: {str(e)}")
        if conn:
            conn.rollback()
        return 1

    finally:
        if conn:
            try:
                conn.close()
                logger.info("数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭数据库连接时出错: {str(e)}")

if __name__ == "__main__":
    sys.exit(create_internal_connections())