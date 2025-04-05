# -*- coding: utf-8 -*-
from neo4j import GraphDatabase
import pymysql
from config import MYSQL_CONFIG, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import sys
import traceback
import time

def get_mysql_connection():
    print('\nTrying to connect to MySQL...')
    try:
        conn = pymysql.connect(**MYSQL_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        print('MySQL connection successful')
        return conn
    except Exception as e:
        print(f'MySQL connection failed: {str(e)}')
        traceback.print_exc()
        sys.exit(1)

def create_sim_terminals(driver, mysql_cursor):
    print('\nCreating Sim_terminal nodes...')
    mysql_cursor.execute("""
        SELECT ftid, project_name, moduler, device_name, 
               point_type, point_index, sim_type, mode, 
               hartingbox, description, target_ftid
        FROM v_simpoint
    """)
    records = mysql_cursor.fetchall()
    print(f'Found {len(records)} records')
    
    created = 0
    for record in records:
        query = "MERGE (n:Sim_terminal {ftid: $ftid}) SET n += $props"
        params = {k: v for k, v in record.items() if k != 'target_ftid' and v is not None}
        
        try:
            with driver.session() as session:
                session.run(query, ftid=record['ftid'], props=params)
                created += 1
                if created % 100 == 0:
                    print(f'Created {created} nodes')
        except Exception as e:
            print(f'Failed to create node {record["ftid"]}: {str(e)}')
    print(f'Created {created} Sim_terminal nodes')
    return created

def create_sim_connections(driver, mysql_cursor):
    print('\nCreating Sim_conn relationships...')
    mysql_cursor.execute("SELECT ftid, target_ftid FROM v_simpoint WHERE target_ftid IS NOT NULL")
    records = mysql_cursor.fetchall()
    print(f'Found {len(records)} records')
    
    created = 0
    for record in records:
        query = """
        MATCH (s:Sim_terminal {ftid: $sim_ftid})
        MATCH (v:V_terminal {ftid: $target_ftid})
        MERGE (s)-[r1:Sim_conn]->(v)
        MERGE (v)-[r2:Sim_conn]->(s)
        """
        try:
            with driver.session() as session:
                session.run(query, sim_ftid=record['ftid'], target_ftid=record['target_ftid'])
                created += 1
                if created % 100 == 0:
                    print(f'Created {created} relationship pairs')
        except Exception as e:
            print(f'Failed to create relationship {record["ftid"]} -> {record["target_ftid"]}: {str(e)}')
    print(f'Created {created} Sim_conn relationship pairs')
    return created

def main():
    print('Starting Neo4j data synchronization...')
    try:
        mysql_conn = get_mysql_connection()
        mysql_cursor = mysql_conn.cursor()
        
        print('\nTrying to connect to Neo4j...')
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        print('Neo4j connection successful')
        
        nodes = create_sim_terminals(driver, mysql_cursor)
        connections = create_sim_connections(driver, mysql_cursor)
        
        print(f'\nProcess completed!')
        print(f'Created {nodes} Sim_terminal nodes')
        print(f'Created {connections} Sim_conn relationship pairs')
        
    except Exception as e:
        print(f'Error: {str(e)}')
        traceback.print_exc()
    finally:
        print('\nClosing database connections...')
        mysql_cursor.close()
        mysql_conn.close()
        driver.close()

if __name__ == "__main__":
    main()
