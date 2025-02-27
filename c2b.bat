@echo off
chcp 65001

set MYSQL_INC=C:\clib\mysql\include
set MYSQL_LIB=C:\clib\mysql\lib
set PROJ_DIR=%~dp0
set INCLUDE_DIR=%PROJ_DIR%include

echo 当前目录: %PROJ_DIR%
echo Include目录: %INCLUDE_DIR%
echo MySQL Include目录: %MYSQL_INC%

set "EXCEL_FILE=data/LOOD-17747-001_BOM_2025-02-20-03-24-05.xlsm"
set COMPILE_CMD=g++ -o c2b_import_excel.exe c2b_importExcelLeyboldPart.cpp -I"%MYSQL_INC%" -I. -I"%INCLUDE_DIR%" -L"%MYSQL_LIB%" -g -Wall "%MYSQL_LIB%\libmysql.lib" -lwsock32 -lws2_32 -DSELECTED_EXCEL_FILE=\\"%EXCEL_FILE%\\"

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
.\c2b_import_excel.exe
pause