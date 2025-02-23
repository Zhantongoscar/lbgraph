@echo off
@REM 基于在mysql数据库表，导出仿真设备及点到neo4j
pushd %~dp0
echo Running c4_import_mysql_sim.py...
python c4_import_mysql_sim.py
popd