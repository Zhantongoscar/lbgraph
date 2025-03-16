# Plan for Creating Neo4j Nodes and Relationships from MySQL Data

This document outlines the plan for creating `c0d_create_neo.py` and `c0d.bat`.

## c0d\_create\_neo.py

This Python script will perform the following actions:

1.  **Connect to MySQL:** Establish a connection to the MySQL database using the credentials from `config.py`.
2.  **Connect to Neo4j:** Establish a connection to the Neo4j database using the URI, username, and password from `config.py`.
3.  **Create Device Nodes:**
    *   Read all columns from the `v_csv_device` table in MySQL.
    *   Create nodes with the label `V_device` in Neo4j.
    *   Add all columns from the `v_csv_device` table as properties to the `V_device` nodes.
4.  **Create Terminal Nodes:**
    *   Read all columns from the `v_csv_devpoint` table in MySQL.
    *   Create nodes with the label `V_terminal` in Neo4j.
    *   Add all columns from the `v_csv_devpoint` table as properties to the `V_terminal` nodes.
    *   Create `belongto` relationships from `V_device` nodes to `V_terminal` nodes.
    *   Create `haveterminal` relationships from `V_device` nodes to `V_terminal` nodes.
5.  **Create Connections:**
    *   Read all columns from the `v_csv_conn` table in MySQL.
    *   Create `conn` relationships between `V_terminal` nodes in Neo4j.
    *   Add all columns from the `v_csv_conn` table as properties to the `conn` relationships.
    *   Create bidirectional `conn` relationships, meaning if A `conn` B, then B `conn` A.

## c0d.bat

This batch file will simply execute the Python script:

```batch
@echo off
python ./c0d_create_neo.py
pause
```

This will run the Python script and then pause, allowing you to see any output in the command window.

## Database and Graph Structure

The following Mermaid diagram illustrates the database structure and the resulting Neo4j graph structure:

```mermaid
graph LR
    subgraph MySQL
        v_csv_device((v_csv_device))
        v_csv_devpoint((v_csv_devpoint))
        v_csv_conn((v_csv_conn))
    end

    subgraph Neo4j
        V_device(V_device)
        V_terminal(V_terminal)
    end

    V_device -- belongto --> V_terminal
    V_device -- haveterminal --> V_terminal
    V_terminal -- conn --> V_terminal
    V_terminal -- conn --> V_terminal