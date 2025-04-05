@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

echo ========================================
echo  开始分析Socket端子连接路径
echo ========================================

python -u f1a_checkSocketPath.py
if errorlevel 1 (
    echo 程序执行失败，错误代码: %errorlevel%
    echo 详细日志请查看 logs\socket_path_analysis.log
 
    exit /b 1
) else (
    echo 程序执行成功
    echo 详细分析结果已保存到 logs\socket_path_analysis.log
)

echo.
echo ========================================
echo  Socket路径分析完成
echo ========================================

exit /b 0