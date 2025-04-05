from neo4j import GraphDatabase
import os

uri = "bolt://192.168.35.10:7687"
username = "neo4j"
password = "13701033228"

def test_connection():
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"Successfully connected. Node count: {count}")
        driver.close()
    except Exception as e:
        print(f"Error connecting to Neo4j: {str(e)}")

if __name__ == "__main__":
    test_connection()
