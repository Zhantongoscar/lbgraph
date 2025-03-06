@echo off
REM 设置UTF-8编码
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

REM 创建logs目录（如果不存在）
if not exist "logs" mkdir logs

echo 开始运行e1a_create_conn_devT-dev.py...

REM 运行Python脚本
python -u e1a_create_conn_devT-dev.py 2>&1 | findstr /v /c:"Defaulting to user installation"

if errorlevel 1 (
    echo 程序执行出错，请查看输出信息
    pause
    exit /b 1
)
