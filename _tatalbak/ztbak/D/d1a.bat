@echo off
chcp 65001
echo Compiling d1a_create_grapu_device.cpp...

set MYSQL_INC="C:/clib/mysql/include"
set MYSQL_LIB="C:/clib/mysql/lib"

echo Include path: %MYSQL_INC%
echo Library path: %MYSQL_LIB%

g++ d1a_create_grapu_device.cpp -o d1a_grapu_device.exe -I%MYSQL_INC% -L%MYSQL_LIB% -g -Wall "C:/clib/mysql/lib/libmysql.lib" -lwsock32 -lws2_32 -I"./include"

if %errorlevel% neq 0 (
    echo Compilation failed!
    pause
    exit /b %errorlevel%
)

echo Copying MySQL library...
copy "C:\clib\mysql\lib\libmysql.dll" . /Y

echo Running d1a_grapu_device.exe...
d1a_grapu_device.exe

if %errorlevel% neq 0 (
    echo Execution failed!
    pause
)

pause