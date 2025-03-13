#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    try:
        # 加载配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)['mysql']

        # 连接数据库
        conn = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

        try:
            with conn.cursor() as cursor:
                # 检查源端重复的FTID
                logger.info("检查源端重复的FTID:")
                cursor.execute("""
                    SELECT s_ftid, COUNT(*) as count
                    FROM v_csv_raw
                    WHERE s_ftid IS NOT NULL
                    GROUP BY s_ftid
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 5
                """)
                duplicates = cursor.fetchall()
                for dup in duplicates:
                    logger.info(f"FTID: {dup['s_ftid']}, 出现次数: {dup['count']}")
                    
                    # 显示重复项的详细信息
                    cursor.execute("""
                        SELECT cnumber, s_raw, s_ftid, s_function, s_location, s_device, s_terminal,
                               t_raw, t_ftid, t_function, t_location, t_device, t_terminal
                        FROM v_csv_raw
                        WHERE s_ftid = %s
                    """, (dup['s_ftid'],))
                    details = cursor.fetchall()
                    logger.info("详细信息:")
                    for detail in details:
                        logger.info(f"  行号: {detail['cnumber']}")
                        logger.info(f"  源端: {detail['s_raw']} -> {detail['s_ftid']}")
                        logger.info(f"  目标端: {detail['t_raw']} -> {detail['t_ftid']}")
                        logger.info("---")

                # 检查目标端重复的FTID
                logger.info("\n检查目标端重复的FTID:")
                cursor.execute("""
                    SELECT t_ftid, COUNT(*) as count
                    FROM v_csv_raw
                    WHERE t_ftid IS NOT NULL
                    GROUP BY t_ftid
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 5
                """)
                duplicates = cursor.fetchall()
                for dup in duplicates:
                    logger.info(f"FTID: {dup['t_ftid']}, 出现次数: {dup['count']}")
                    
                    # 显示重复项的详细信息
                    cursor.execute("""
                        SELECT cnumber, s_raw, s_ftid, s_function, s_location, s_device, s_terminal,
                               t_raw, t_ftid, t_function, t_location, t_device, t_terminal
                        FROM v_csv_raw
                        WHERE t_ftid = %s
                    """, (dup['t_ftid'],))
                    details = cursor.fetchall()
                    logger.info("详细信息:")
                    for detail in details:
                        logger.info(f"  行号: {detail['cnumber']}")
                        logger.info(f"  源端: {detail['s_raw']} -> {detail['s_ftid']}")
                        logger.info(f"  目标端: {detail['t_raw']} -> {detail['t_ftid']}")
                        logger.info("---")

        finally:
            conn.close()
            logger.info("数据库连接已关闭")

    except Exception as e:
        logger.error(f"错误: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    main()