@echo off
@REM 从csv导入点和边 到neo4j
pushd %~dp0
echo Running c3_create_s2t_conn.py...
python c3_create_s2t_conn.py
popd