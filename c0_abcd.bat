@echo off
chcp 65001 > nul
echo ==========================
echo 准备执行c0a.bat... 
创建 mysql表 v_csv_raw from selected csv
echo ==========================
timeout /t 5/nobreak > nul
call c0a.bat

echo ==========================
echo 准备执行c0b.bat...
创建 v_csv_device 表 v_csv_devpoint表 v_csv_conn表
echo ==========================
timeout /t 5 /nobreak > nul
call c0b.bat

echo ==========================
echo 准备执行c0c1.bat...
echo 该脚本将创建设备内部连接
echo ==========================
timeout /t 5 /nobreak > nul
call c0c1.bat

echo ==========================
echo 准备执行c0c2.bat...
echo 该脚本将更新设备类型信息
echo ==========================
timeout /t 5 /nobreak > nul
call c0c2.bat

echo ==========================
echo 准备执行c0d.bat...
echo  更新后的设备(type) 点（type） 连接 创建neo4j 基本数据
echo ==========================
timeout /t 5 /nobreak > nul
call c0d.bat

