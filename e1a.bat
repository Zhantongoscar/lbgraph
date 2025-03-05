@echo off
chcp 65001 > nul

REM 创建logs目录（如果不存在）
if not exist "logs" mkdir logs

echo 开始运行e1a_create_conn_devT-dev.py...

REM 运行Python脚本并同时输出到控制台和日志文件
python -u e1a_create_conn_devT-dev.py > logs\e1a_output.log 2>&1
type logs\e1a_output.log

if errorlevel 1 (
    echo 程序执行出错，请查看日志文件：logs\e1a_output.log
    pause
    exit /b 1
)

echo 程序执行完成，输出已保存到：logs\e1a_output.log
pause