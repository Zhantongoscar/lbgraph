@echo off
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing dependencies one by one...
python -m pip install pandas>=2.2.0
python -m pip install openpyxl>=3.1.2 
python -m pip install --no-deps neo4j>=5.13
python -m pip install pymysql>=1.1.0
python -m pip install xlsxwriter>=3.1.9

echo.
echo Installation complete. Press any key to exit.
pause
