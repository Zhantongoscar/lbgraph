@echo off
chcp 65001 > nul
echo ==========================
echo 准备执行c0c1.bat...
echo 该脚本将创建设备内部连接
echo ==========================
timeout /t 2 /nobreak > nul
call c0c1.bat

echo ==========================
echo 准备执行c0c2.bat...
echo 该脚本将更新设备类型信息
echo ==========================
timeout /t 2 /nobreak > nul
call c0c2.bat

echo ==========================
echo 所有操作执行完毕
echo ==========================
