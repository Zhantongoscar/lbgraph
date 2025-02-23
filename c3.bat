@echo off
echo Running c3_create_s2t_conn.py...

python "%~dp0c3_create_s2t_conn.py"

if %errorlevel% equ 0 (
    echo Program completed successfully
) else (
    echo Program failed with error %errorlevel%
)

pause