@echo off
chcp 65001 > nul

echo 开始运行 d1a.bat, d1b.bat, d1d.bat, d1c.bat, e1a.bat...
echo.

echo 步骤 1: 运行 d1a.bat (创建设备节点)
echo ====================================
call d1a.bat
if errorlevel 1 (
    echo d1a.bat 执行失败!
    exit /b 1
)
echo.
echo d1a.bat 执行完成
echo.

echo 步骤 2: 运行 d1b.bat (创建终端节点)
echo ====================================
call d1b.bat
if errorlevel 1 (
    echo d1b.bat 执行失败!
    exit /b 1
)
echo.
echo d1b.bat 执行完成
echo.

echo 步骤 3: 运行 d1d.bat (创建内部连接)
echo ====================================
call d1d.bat
if errorlevel 1 (
    echo d1d.bat 执行失败!
    exit /b 1
)
echo.
echo d1d.bat 执行完成
echo.

echo 步骤 4: 运行 d1c.bat (创建外部连接)
echo ====================================
call d1c.bat
if errorlevel 1 (
    echo d1c.bat 执行失败!
    exit /b 1
)
echo.
echo d1c.bat 执行完成
echo.

echo 步骤 5: 运行 e1a.bat (创建设备终端连接)
echo ====================================
call e1a.bat
if errorlevel 1 (
    echo e1a.bat 执行失败!
    exit /b 1
)
echo.
echo e1a.bat 执行完成
echo.

echo 所有脚本执行完成!