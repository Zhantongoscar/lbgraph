
echo 1 准备执行g0a.bat... 
1.1 从neo4j 图中X2x Harting 节点 --路由--PLCIDtype
1.2 反推需求Sim点 填写板到 devices内；创建 simpoints 表
echo ==========================
timeout /t 10/nobreak > nul
call g0a.bat

pause

echo 2 准备执行g0b.bat... 
2.1 从数据中sim的 点 加入neo4g
2.2 从 sim点---Harting点 建立连接
echo ==========================
timeout /t 10/nobreak > nul
call g0b.bat


