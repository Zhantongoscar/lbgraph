# -*- coding: utf-8 -*-
import sys
import traceback
import os
from datetime import datetime
import logging

# 设置日志记录
def setup_logger():
    logger = logging.getLogger('InnerConnLogger')
    logger.setLevel(logging.INFO)
    
    # 只使用控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 设置格式
    formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

logger.info("脚本开始执行...")
logger.info(f"当前工作目录: {os.getcwd()}")
logger.info(f"Python路径: {sys.executable}")
logger.info("正在导入模块...")

try:
    from neo4j import GraphDatabase
    logger.info("成功导入neo4j")
    import pymysql
    logger.info("成功导入pymysql")
    import json
    from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    logger.info(f"MySQL配置: {MYSQL_CONFIG}")
    logger.info(f"Neo4j URI: {NEO4J_URI}")
except Exception as e:
    logger.error(f"导入时发生错误: {str(e)}")
    logger.error("详细错误信息:")
    logger.error(traceback.format_exc())
    sys.exit(1)

# 添加MySQL的字符集和超时设置
MYSQL_CONFIG.update({
    "connect_timeout": 10,
    "charset": 'utf8mb4'
})

class InnerConnCreator:
    def __init__(self):
        try:
            # 连接MySQL数据库
            logger.info(f"尝试连接MySQL数据库，配置: {MYSQL_CONFIG}")
            try:
                self.mysql_conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
                # 测试连接
                with self.mysql_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    logger.info(f"MySQL连接测试成功: {result}")
            except pymysql.Error as e:
                logger.error(f"MySQL连接错误: {str(e)}")
                logger.error(f"错误代码: {e.args[0]}, 错误信息: {e.args[1]}")
                raise
            
            # 连接Neo4j数据库
            logger.info("正在连接Neo4j数据库...")
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_timeout=30
            )
            # 测试连接
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                test_value = result.single()["test"]
                logger.info(f"成功连接到Neo4j数据库，测试值: {test_value}")

        except pymysql.Error as err:
            logger.error(f"MySQL连接错误: {err}")
            raise
        except Exception as e:
            logger.error(f"连接数据库时发生错误: {e}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise

    def close(self):
        if hasattr(self, 'driver'):
            self.driver.close()
        if hasattr(self, 'mysql_conn'):
            self.mysql_conn.close()
        logger.info("数据库连接已关闭")

    def create_inner_connections(self):
        try:
            with self.driver.session() as session:
                # 删除现有的内部连接
                session.run("MATCH ()-[r:INNER_CONN]->() DELETE r")
                logger.info("已删除现有的内部连接")
                
                # 创建内部连接
                self._create_device_inner_connections(session)
                logger.info("完成创建设备内部连接")

        except Exception as e:
            logger.error(f"创建内部连接时发生错误: {e}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise

    def _create_device_inner_connections(self, session):
        """创建设备内部连接关系"""
        # 创建继电器内部连接
        self._create_relay_inner_connections(session)
        # 创建按钮内部连接
        self._create_button_inner_connections(session)
        # 创建接触器内部连接
        self._create_contactor_inner_connections(session)

    def _create_relay_inner_connections(self, session):
        """创建继电器内部连接"""
        # 创建公共连接属性
        conn_props = {
            "voltage": 24.0,  # 继电器一般使用24V
            "current": 0.1,   # 典型值
            "resistance": 240.0,
            "isCable": False,
            "isInPanel": True,
            "connType": "devInner"  # 添加connType属性
        }
        props_str = ', '.join(f'{k}: ${k}' for k in conn_props.keys())

        # 继电器线圈到常开触点的双向连接
        query = f"""
        MATCH (coil:DevicePoint {{Type: 'coil'}})
        WHERE coil.Device STARTS WITH 'K'
        MATCH (no:DevicePoint)
        WHERE no.Device = coil.Device 
        AND no.Type STARTS WITH 'AX_NO'
        MERGE (coil)-[r1:INNER_CONN {{{props_str}}}]->(no)
        MERGE (no)-[r2:INNER_CONN {{{props_str}}}]->(coil)
        """
        session.run(query, **conn_props)
        logger.info("创建了继电器线圈到常开触点的双向连接")

        # 继电器线圈到常闭触点的双向连接
        query = f"""
        MATCH (coil:DevicePoint {{Type: 'coil'}})
        WHERE coil.Device STARTS WITH 'K'
        MATCH (nc:DevicePoint)
        WHERE nc.Device = coil.Device 
        AND nc.Type STARTS WITH 'AX_NC'
        MERGE (coil)-[r1:INNER_CONN {{{props_str}}}]->(nc)
        MERGE (nc)-[r2:INNER_CONN {{{props_str}}}]->(coil)
        """
        session.run(query, **conn_props)
        logger.info("创建了继电器线圈到常闭触点的双向连接")

        # 继电器公共端到常开/常闭触点的双向连接
        query = f"""
        MATCH (com:DevicePoint)
        WHERE com.Device STARTS WITH 'K' AND com.Type CONTAINS 'COM'
        MATCH (contact:DevicePoint)
        WHERE contact.Device = com.Device 
        AND (contact.Type STARTS WITH 'AX_NO' OR contact.Type STARTS WITH 'AX_NC')
        MERGE (com)-[r1:INNER_CONN {{{props_str}}}]->(contact)
        MERGE (contact)-[r2:INNER_CONN {{{props_str}}}]->(com)
        """
        session.run(query, **conn_props)
        logger.info("创建了继电器公共端到触点的双向连接")

    def _create_button_inner_connections(self, session):
        """创建按钮内部连接"""
        # 按钮连接属性
        conn_props = {
            "voltage": 24.0,
            "current": 0.1,
            "resistance": 240.0,
            "isCable": False,
            "isInPanel": True,
            "connType": "devInner"  # 添加connType属性
        }
        props_str = ', '.join(f'{k}: ${k}' for k in conn_props.keys())

        # 按钮常开触点双向连接
        query = f"""
        MATCH (b1:DevicePoint)
        WHERE b1.Device STARTS WITH 'S' AND b1.Type = 'S_NO_1'
        MATCH (b2:DevicePoint)
        WHERE b2.Device = b1.Device AND b2.Type = 'S_NO_1'
        AND b1.description < b2.description
        MERGE (b1)-[r1:INNER_CONN {{{props_str}}}]->(b2)
        MERGE (b2)-[r2:INNER_CONN {{{props_str}}}]->(b1)
        """
        session.run(query, **conn_props)
        logger.info("创建了按钮常开触点的双向连接")

        # 按钮常闭触点双向连接
        query = f"""
        MATCH (b1:DevicePoint)
        WHERE b1.Device STARTS WITH 'S' AND b1.Type = 'S_NC_1'
        MATCH (b2:DevicePoint)
        WHERE b2.Device = b1.Device AND b2.Type = 'S_NC_1'
        AND b1.description < b2.description
        MERGE (b1)-[r1:INNER_CONN {{{props_str}}}]->(b2)
        MERGE (b2)-[r2:INNER_CONN {{{props_str}}}]->(b1)
        """
        session.run(query, **conn_props)
        logger.info("创建了按钮常闭触点的双向连接")

    def _create_contactor_inner_connections(self, session):
        """创建接触器内部连接"""
        # 接触器连接属性
        main_conn_props = {
            "voltage": 380.0,  # 主触点电压
            "current": 16.0,   # 主触点电流
            "resistance": 23.75,
            "isCable": False,
            "isInPanel": True,
            "connType": "devInner"  # 添加connType属性
        }
        aux_conn_props = {
            "voltage": 24.0,   # 辅助触点电压
            "current": 0.1,    # 辅助触点电流
            "resistance": 240.0,
            "isCable": False,
            "isInPanel": True,
            "connType": "devInner"  # 添加connType属性
        }

        # 接触器线圈到主触点的双向连接
        props_str = ', '.join(f'{k}: ${k}' for k in main_conn_props.keys())
        query = f"""
        MATCH (coil:DevicePoint {{Type: 'coil'}})
        WHERE coil.Device STARTS WITH 'Q'
        MATCH (mc:DevicePoint)
        WHERE mc.Device = coil.Device 
        AND mc.Type STARTS WITH 'MC_NO'
        MERGE (coil)-[r1:INNER_CONN {{{props_str}}}]->(mc)
        MERGE (mc)-[r2:INNER_CONN {{{props_str}}}]->(coil)
        """
        session.run(query, **main_conn_props)
        logger.info("创建了接触器线圈到主触点的双向连接")

        # 接触器线圈到辅助触点的双向连接
        props_str = ', '.join(f'{k}: ${k}' for k in aux_conn_props.keys())
        query = f"""
        MATCH (coil:DevicePoint {{Type: 'coil'}})
        WHERE coil.Device STARTS WITH 'Q'
        MATCH (aux:DevicePoint)
        WHERE aux.Device = coil.Device 
        AND aux.Type STARTS WITH 'AC_NO'
        MERGE (coil)-[r1:INNER_CONN {{{props_str}}}]->(aux)
        MERGE (aux)-[r2:INNER_CONN {{{props_str}}}]->(coil)
        """
        session.run(query, **aux_conn_props)
        logger.info("创建了接触器线圈到辅助触点的双向连接")

def main():
    try:
        creator = InnerConnCreator()
        creator.create_inner_connections()
        logger.info("成功完成所有内部连接的创建")
    except Exception as e:
        logger.error(f"程序执行过程中发生错误: {e}")
        return 1
    finally:
        if 'creator' in locals():
            creator.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())