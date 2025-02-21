@echo off
chcp 65001
echo 正在编译...

g++ c2_init_type_conn.cpp -o type_conn.exe -I"C:/clib/mysql/include" -I. -L"C:/clib/mysql/lib" -g -Wall "C:/clib/mysql/lib/libmysql.lib" -lwsock32 -lws2_32

if %ERRORLEVEL% NEQ 0 (
    echo 编译失败！
    exit /b 1
)

echo 编译成功！
copy "C:\clib\mysql\lib\libmysql.dll" . /Y
echo 正在运行程序...
.\type_conn.exe
pause