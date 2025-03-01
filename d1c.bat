@echo off
chcp 65001

if exist "d1c_create_graph_conn.py" (
    echo 使用Python版本运行...
    
    python -m pip install neo4j mysql-connector-python --quiet
    python d1c_create_graph_conn.py

) else (
    echo 错误: 找不到d1c_create_graph_conn.py文件。
    echo 当前目录文件列表:
    dir /b
)

if %errorlevel% neq 0 (
    echo 执行失败!
    pause
)

pause