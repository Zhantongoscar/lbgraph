@echo off
chcp 65001

set MYSQL_INC=C:\clib\mysql\include
set MYSQL_LIB=C:\clib\mysql\lib
set PROJ_DIR=%~dp0
set INCLUDE_DIR=%PROJ_DIR%include

echo 当前目录: %PROJ_DIR%
echo Include目录: %INCLUDE_DIR%
echo MySQL Include目录: %MYSQL_INC%

set COMPILE_CMD=g++ c2_init_type_conn.cpp -o type_conn.exe -I"%MYSQL_INC%" -I. -I"%INCLUDE_DIR%" -L"%MYSQL_LIB%" -g -Wall "%MYSQL_LIB%\libmysql.lib" -lwsock32 -lws2_32

echo 编译命令:
echo %COMPILE_CMD%

%COMPILE_CMD%

if %ERRORLEVEL% NEQ 0 (
    echo 编译失败！错误代码：%ERRORLEVEL%
    exit /b 1
)

echo 编译成功！
copy "%MYSQL_LIB%\libmysql.dll" . /Y
echo 正在运行程序...
.\type_conn.exe
pause