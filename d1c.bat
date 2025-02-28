@echo off
g++ d1c_create_graph_conn.cpp -o d1c_grapu_conn.exe -I"C:/clib/mysql/include" -I"./include" -L"C:/clib/mysql/lib" -lmysql
if %errorlevel% neq 0 (
    echo 编译失败
    pause
    exit /b %errorlevel%
)
.\d1c_grapu_conn.exe
pause