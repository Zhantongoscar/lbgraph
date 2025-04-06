@echo off
set PYTHONPATH=.



echo 1 准备执行g0a.bat... 
创建 mysql表 v_csv_raw from selected csv
echo ==========================
python g0a_graph_neo_Harting.py
timeout /t 5/nobreak > nul