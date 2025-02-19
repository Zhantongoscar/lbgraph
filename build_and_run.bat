@echo off
chcp 65001
echo 正在编译...
g++ c1_create_devicetype_table.cpp -o devicetype.exe -fexec-charset=utf-8
if %errorlevel% equ 0 (
    echo 编译成功！正在运行程序...
    devicetype.exe
    echo.
    echo 程序运行完成！
) else (
    echo 编译失败！
)
pause