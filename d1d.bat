@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

REM 创建logs目录（如果不存在）
if not exist "logs" mkdir logs

REM 运行Python脚本并同时输出到控制台和日志文件
python -u d1d_create_innconn_from_device.py > logs\d1d_output.log 2>&1
type logs\d1d_output.log

if errorlevel 1 (
    echo 程序执行出错，请查看日志文件：logs\d1d_output.log
    pause
    exit /b 1
)

echo 程序执行完成，输出已保存到：logs\d1d_output.log
pause