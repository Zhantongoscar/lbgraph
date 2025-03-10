@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo ========================================
echo  开始执行C系列批处理脚本
echo ========================================

echo.
echo [1/3] 执行 c1a.bat - 创建设备点位表...
call c1a.bat
if errorlevel 1 (
    echo 执行 c1a.bat 失败，错误代码: %errorlevel%
    goto :error
)
echo c1a.bat 执行完成

echo.
echo [2/3] 执行 c1b.bat - 创建顶点点位表...
call c1b.bat
if errorlevel 1 (
    echo 执行 c1b.bat 失败，错误代码: %errorlevel%
    goto :error
)
echo c1b.bat 执行完成

echo.
echo [3/3] 执行 c1c.bat - 创建连接...
call c1c.bat
if errorlevel 1 (
    echo 执行 c1c.bat 失败，错误代码: %errorlevel%
    goto :error
)
echo c1c.bat 执行完成

echo.
echo ========================================
echo  所有C系列批处理脚本执行完成
echo ========================================
goto :end

:error
echo.
echo ========================================
echo  执行过程中出现错误，流程已中断
echo ========================================
exit /b 1

:end
exit /b 0