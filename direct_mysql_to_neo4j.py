#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
直接从MySQL导入设备数据到Neo4j的脚本
避免使用CSV文件作为中间环节，提高数据导入的可靠性
"""

import sys
import json
import traceback
import mysql.connector
from neo4j import GraphDatabase
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mysql_to_neo4j_import.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """加载配置文件"""
    try:
        with open("config.json", "r", encoding="utf-8") as config_file:
            config = json.load(config_file)
            # 打印配置信息以便调试
            logger.info(f"MySQL配置: 主机={config['mysql']['host']}, 用户={config['mysql']['user']}, 数据库={config['mysql']['database']}")
            logger.info(f"Neo4j配置: URI={config['neo4j']['uri']}, 用户={config['neo4j']['username']}")
            return config
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        sys.exit(1)

def connect_to_mysql(config):
    """连接到MySQL数据库"""
    try:
        logger.info(f"尝试连接到MySQL: {config['mysql']['host']}...")
        conn = mysql.connector.connect(
            host=config["mysql"]["host"],
            user=config["mysql"]["user"],
            password=config["mysql"]["password"],
            database=config["mysql"]["database"]
        )
        logger.info(f"成功连接到MySQL数据库: {config['mysql']['host']}")
        return conn
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            logger.error("MySQL连接失败: 用户名或密码不正确")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            logger.error(f"数据库 {config['mysql']['database']} 不存在")
        else:
            logger.error(f"MySQL连接错误: {err}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"连接MySQL失败: {e}")
        logger.error(f"详细错误: {traceback.format_exc()}")
        sys.exit(1)

def convert_http_to_bolt_uri(http_uri):
    """转换HTTP URI为Bolt URI"""
    if http_uri.startswith("http://"):
        # 简单替换，实际环境可能需要更复杂的逻辑
        return http_uri.replace("http://", "bolt://").replace(":7474", ":7687")
    elif not http_uri.startswith("bolt://") and not http_uri.startswith("neo4j://"):
        return f"bolt://{http_uri}"
    return http_uri

def connect_to_neo4j(config):
    """连接到Neo4j数据库"""
    try:
        # 转换URI格式
        uri = convert_http_to_bolt_uri(config["neo4j"]["uri"])
        username = config["neo4j"]["username"]
        password = config["neo4j"]["password"]
        
        driver = GraphDatabase.driver(uri, auth=(username, password))
        # 测试连接
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            test_value = result.single()["test"]
            logger.info(f"成功连接到Neo4j数据库: {uri}, 测试值: {test_value}")
        return driver
    except Exception as e:
        logger.error(f"连接Neo4j失败: {e}")
        sys.exit(1)

def clear_existing_devices(neo4j_driver):
    """清除Neo4j中现有的设备节点"""
    try:
        with neo4j_driver.session() as session:
            result = session.run("MATCH (d:V_Device) DELETE d")
            logger.info("已清除所有现有设备节点")
    except Exception as e:
        logger.error(f"清除节点失败: {e}")
        sys.exit(1)

def import_devices(mysql_conn, neo4j_driver):
    """从MySQL导入设备数据到Neo4j"""
    try:
        cursor = mysql_conn.cursor(dictionary=True)
        # 执行查询，只选择isInPanel=1的设备
        cursor.execute("SELECT id, fdid, function, location, device, Type, isSim, isPLC, isTerminal FROM v_devices WHERE isInPanel=1")
        
        # 获取所有记录
        records = cursor.fetchall()
        total_records = len(records)
        logger.info(f"从MySQL查询到 {total_records} 条设备记录")
        
        # 导入到Neo4j
        success_count = 0
        with neo4j_driver.session() as session:
            for idx, record in enumerate(records, 1):
                try:
                    # 检查数据完整性
                    for key in record:
                        if record[key] is None:
                            record[key] = ""  # 将None值转换为空字符串，避免Neo4j创建节点时出错
                    
                    # 创建节点
                    session.run(
                        """
                        CREATE (d:V_Device {
                            id: $id,
                            fdid: $fdid,
                            function: $function,
                            location: $location,
                            device: $device,
                            Type: $Type,
                            isSim: $isSim,
                            isPLC: $isPLC,
                            isTerminal: $isTerminal
                        })
                        """,
                        **record
                    )
                    success_count += 1
                    
                    # 每导入100条记录输出一次进度
                    if idx % 100 == 0 or idx == total_records:
                        logger.info(f"已导入 {idx}/{total_records} 条记录")
                        
                except Exception as e:
                    logger.error(f"导入第 {idx} 条记录失败: {e}, 记录内容: {record}")
        
        logger.info(f"导入完成! 成功导入 {success_count}/{total_records} 条记录")
        return success_count, total_records
    
    except Exception as e:
        logger.error(f"导入过程中发生错误: {e}")
        sys.exit(1)
    finally:
        cursor.close()

def verify_import(neo4j_driver):
    """验证导入的数据数量"""
    try:
        with neo4j_driver.session() as session:
            result = session.run("MATCH (n:V_Device) RETURN COUNT(n) as count")
            count = result.single()["count"]
            logger.info(f"Neo4j中V_Device节点数量: {count}")
            return count
    except Exception as e:
        logger.error(f"验证导入数据失败: {e}")
        return -1

def main():
    """主函数"""
    logger.info("开始导入设备数据从MySQL到Neo4j...")
    
    try:
        # 加载配置
        config = load_config()
        
        # 连接数据库
        mysql_conn = connect_to_mysql(config)
        neo4j_driver = connect_to_neo4j(config)
        
        try:
            # 清除现有节点
            clear_existing_devices(neo4j_driver)
            
            # 导入数据
            success_count, total_records = import_devices(mysql_conn, neo4j_driver)
            
            # 验证导入结果
            actual_count = verify_import(neo4j_driver)
            
            # 检查是否所有记录都成功导入
            if success_count == total_records and success_count == actual_count:
                logger.info("所有记录成功导入!")
            else:
                logger.warning(f"导入结果不一致: 应处理 {total_records} 条记录，"
                            f"报告成功 {success_count} 条，"
                            f"Neo4j实际有 {actual_count} 条")
        
        finally:
            # 关闭连接
            if 'mysql_conn' in locals() and mysql_conn:
                mysql_conn.close()
            if 'neo4j_driver' in locals() and neo4j_driver:
                neo4j_driver.close()
    except Exception as e:
        logger.error(f"程序执行过程中发生未处理的异常: {e}")
        logger.error(f"详细错误堆栈: {traceback.format_exc()}")
    
    logger.info("导入过程完成")

if __name__ == "__main__":
    main()