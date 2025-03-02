@echo off
chcp 65001

echo 创建终端点和设备之间的关系...
python e1a_create_conn_devT-dev.py

if %ERRORLEVEL% NEQ 0 (
    echo 执行失败！
    pause
    exit /b 1
)

echo 执行完成！
pause