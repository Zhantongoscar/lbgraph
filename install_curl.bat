@echo off
echo Installing libcurl dependencies...

REM Create directories if they don't exist
mkdir deps 2>nul
mkdir lib 2>nul
mkdir include 2>nul

cd deps

REM Use scoop to install curl
scoop install curl

REM Copy necessary files from scoop installation
xcopy /Y /I "%USERPROFILE%\scoop\apps\curl\current\bin\*.dll" "..\\"
xcopy /Y /I "%USERPROFILE%\scoop\apps\curl\current\include\curl" "..\include\curl\"
xcopy /Y /I "%USERPROFILE%\scoop\apps\curl\current\lib\*.lib" "..\lib\"

echo Installation complete!
cd ..