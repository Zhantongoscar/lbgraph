@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

python -u d1d_create_innconn_from_device.py

if errorlevel 1 (
    echo 程序执行失败!
    
    exit /b 1
) else (
    echo 程序执行完成!
    
)