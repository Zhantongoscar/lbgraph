@echo off
chcp 65001 > nul

python -u d1c_create_graph_conn.py

if errorlevel 1 (
    echo 程序执行失败!
    exit /b 1
)