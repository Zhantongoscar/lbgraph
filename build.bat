@echo off
chcp 65001
echo 正在编译...

@echo off
chcp 65001

set MYSQL_INC="C:/clib/mysql/include"
set MYSQL_LIB="C:/clib/mysql/lib"

echo Include path: %MYSQL_INC%
echo Library path: %MYSQL_LIB%

g++ -v c1_create_devicetype_table.cpp -o devicetype.exe -I%MYSQL_INC% -L%MYSQL_LIB% -g -Wall "C:/clib/mysql/lib/libmysql.lib" -lwsock32 -lws2_32 > build_log.txt 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo Compilation failed. See build_log.txt for details.
    type build_log.txt
    exit /b 1
) else (
    echo Compilation successful!
    type build_log.txt
)

REM Store the error level
set BUILD_ERROR=%ERRORLEVEL%

if %BUILD_ERROR% NEQ 0 (
    echo 编译失败！
    echo 错误代码: %BUILD_ERROR%
    type error.log 2>&1
    pause
    exit /b 1
)

echo 编译成功！
pause