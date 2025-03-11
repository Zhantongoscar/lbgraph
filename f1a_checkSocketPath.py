# -*- coding: utf-8 -*-
import sys
import os
import logging
import json
import traceback
from neo4j import GraphDatabase
import pymysql
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 设置日志记录
def setup_logger():
    logger = logging.getLogger('SocketPathAnalyzer')
    logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 创建文件处理器
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(log_dir, 'socket_path_analysis.log'),
        mode='w',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

class SocketPathAnalyzer:
    def __init__(self, max_depth=9, path_limit=20):
        try:
            logger.info("\n=== 初始化数据库连接 ===")
            
            # 连接数据库
            self.mysql_conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            
            # 分析参数
            self.max_depth = max_depth
            self.path_limit = path_limit
            
            # 测试连接
            self._test_connections()
            logger.info("数据库连接测试成功")
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            logger.error(traceback.format_exc())
            raise

    def _test_connections(self):
        """测试数据库连接"""
        with self.mysql_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            if not cursor.fetchone():
                raise Exception("MySQL连接测试失败")
                
        with self.driver.session() as session:
            result = session.run("RETURN 1 AS test")
            if result.single()["test"] != 1:
                raise Exception("Neo4j连接测试失败")

    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'driver'):
            self.driver.close()
        if hasattr(self, 'mysql_conn'):
            self.mysql_conn.close()
        logger.info("数据库连接已关闭")

    def get_socket_terminals(self, session):
        """获取特定编号的Socket终端节点(X20-X23)"""
        query = """
        MATCH (terminal:V_Terminal)
        WHERE (
            terminal.FTID CONTAINS '-X20'
            OR terminal.FTID CONTAINS '-X21'
            OR terminal.FTID CONTAINS '-X22'
            OR terminal.FTID CONTAINS '-X23'
        )
        SET terminal.isSocket = true
        RETURN 
            terminal.FTID AS ftid, 
            terminal.description AS description, 
            terminal.belongtoDevice as belongtoDevice,
            terminal.Location as location,
            terminal.isSocket as isSocket
        ORDER BY terminal.belongtoDevice, terminal.description
        """
        
        result = session.run(query)
        terminals = [
            {
                "ftid": record["ftid"], 
                "description": record["description"],
                "belongtoDevice": record["belongtoDevice"],
                "location": record.get("location", ""),  
                "isSocket": record.get("isSocket", True)  
            } 
            for record in result
        ]
        
        return terminals

    def find_paths_for_socket(self, session, socket_ftid, socket_desc):
        """查找指定Socket终端的所有可能路径"""
        logger.info(f"\n\n{'='*80}")
        logger.info(f"分析Socket终端: {socket_desc} (FTID: {socket_ftid})")
        logger.info(f"{'='*80}")
        
        # 简化查询，移除额外的过滤条件
        query = f"""
        MATCH path = (p1:V_Terminal {{FTID: $socket_ftid}})-[:CONN*1..{self.max_depth}]->(p2:V_Terminal)
        WITH path, length(path) AS pathLength,
             [node IN nodes(path) | node.FTID] AS nodeIds,
             [node IN nodes(path) | node.description] AS nodeDescriptions,
             [rel IN relationships(path) | rel.connType] AS relTypes
        RETURN 
            pathLength,
            nodeDescriptions,
            relTypes,
            nodeIds
        ORDER BY pathLength DESC
        LIMIT {self.path_limit}
        """
        
        result = session.run(query, socket_ftid=socket_ftid)
        paths = list(result)
        
        if not paths:
            logger.info("未找到任何连接路径")
            return
            
        logger.info(f"找到 {len(paths)} 条连接路径:")
        
        for idx, record in enumerate(paths):
            path_length = record["pathLength"]
            node_descriptions = record["nodeDescriptions"]
            rel_types = record["relTypes"]
            node_ids = record["nodeIds"]
            
            # 记录路径信息
            logger.info(f"\n路径 #{idx+1} (长度: {path_length}):")
            
            # 输出节点和连接类型，包含完整的FTID
            path_str = ""
            ftid_str = "\nFTID顺序: "
            
            for i in range(len(node_descriptions)):
                node_desc = node_descriptions[i]
                node_id = node_ids[i]
                
                # 添加节点信息到路径字符串
                path_str += f"{node_desc}"
                
                # 添加连接信息（如果不是最后一个节点）
                if i < len(rel_types):
                    conn_type = rel_types[i]
                    path_str += f" -[{conn_type}]-> "
                    
                # 收集FTID信息
                ftid_str += f"\n  {i+1}. {node_id}"
            
            logger.info(path_str)
            logger.info(ftid_str)
            
        # 输出总结信息
        if paths:
            longest_path = max(record["pathLength"] for record in paths)
            logger.info(f"\n最长路径长度: {longest_path}")

    def analyze_all_sockets(self):
        """分析所有Socket终端的路径"""
        try:
            with self.driver.session() as session:
                logger.info("\n=== 开始分析Socket端子连接路径 ===")
                
                # 获取所有Socket终端
                logger.info("\n正在获取所有Socket终端...")
                sockets = self.get_socket_terminals(session)
                logger.info(f"找到 {len(sockets)} 个Socket终端")
                
                if not sockets:
                    logger.info("没有找到任何Socket终端，分析结束")
                    return

                # 输出Socket终端清单
                logger.info("\n=== Socket终端清单 ===")
                logger.info("\n{:<5} {:<20} {:<12} {:<30} {:<8}".format(
                    "序号", "描述", "位置", "FTID", "IsSocket"))
                logger.info("-" * 77)
                for idx, socket in enumerate(sockets, 1):
                    desc = socket['description']
                    ftid = socket['ftid']
                    location = socket['location']
                    is_socket = "是" if socket['isSocket'] else "否"
                    
                    # 如果描述太长，截断它
                    if len(desc) > 18:
                        desc = desc[:15] + "..."
                    if len(ftid) > 28:
                        ftid = "..." + ftid[-25:]
                    if len(location) > 10:
                        location = location[:7] + "..."
                        
                    logger.info("{:<5} {:<20} {:<12} {:<30} {:<8}".format(
                        idx, desc, location, ftid, is_socket))
                logger.info("-" * 77)
                logger.info("\n")
                
                # 对每个Socket终端进行路径分析
                for idx, socket in enumerate(sockets, 1):
                    logger.info(f"\n[{idx}/{len(sockets)}] 分析Socket: {socket['description']}")
                    self.find_paths_for_socket(session, socket["ftid"], socket["description"])
                
                logger.info("\n=== Socket端子路径分析完成 ===")
                
        except Exception as e:
            logger.error(f"分析Socket路径时发生错误: {e}")
            logger.error(traceback.format_exc())
            raise

def main():
    try:
        analyzer = SocketPathAnalyzer()
        analyzer.analyze_all_sockets()
        return 0
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return 1
    finally:
        if 'analyzer' in locals():
            analyzer.close()

if __name__ == "__main__":
    sys.exit(main())