 1 清空导入csv
 python cleanup_db.py; 
 
 python import_csv_data_panel.py 


2 导入mysql的sim模块
 python import_mysql_sim.py

 1. 查看所有仿真节点:
MATCH (v:Vertex {NodeLayer: 'Simulation'})
RETURN v