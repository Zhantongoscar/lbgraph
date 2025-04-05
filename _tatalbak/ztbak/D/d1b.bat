@echo off
g++ d1b_create_graph_devterminal.cpp -o d1b_grapu_terminal.exe -I"C:/clib/mysql/include" -I"./include" -L"C:/clib/mysql/lib" -lmysql
if %errorlevel% neq 0 (
    echo 编译失败
    pause
    exit /b %errorlevel%
)
.\d1b_grapu_terminal.exe
pause