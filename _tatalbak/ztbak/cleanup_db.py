from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def cleanup_database():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        with driver.session() as session:
            session.run('MATCH (n) DETACH DELETE n')
            print("数据库清理完成")
    finally:
        driver.close()

if __name__ == "__main__":
    cleanup_database()