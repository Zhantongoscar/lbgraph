"""
数据库连接配置
"""

# Neo4j配置
NEO4J_URI = "bolt://192.168.35.10:7687"  # 使用bolt协议而不是http
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "13701033228"
NEO4J_CONFIG = {
    "max_connection_pool_size": 10,
    "connection_timeout": 5
}

# MySQL配置
MYSQL_CONFIG = {
    "host": "192.168.35.10",
    "user": "root",
    "password": "13701033228",
    "database": "lbfat"
}