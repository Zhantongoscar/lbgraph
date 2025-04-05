@echo off
chcp 65001
echo Installing curl development files...

if not exist "C:\clib" mkdir "C:\clib"
if not exist "C:\clib\curl" mkdir "C:\clib\curl"
if not exist "C:\clib\curl\bin" mkdir "C:\clib\curl\bin"
if not exist "C:\clib\curl\include" mkdir "C:\clib\curl\include"
if not exist "C:\clib\curl\lib" mkdir "C:\clib\curl\lib"

echo Downloading curl...
powershell -Command "Invoke-WebRequest -Uri 'https://curl.se/windows/dl-7.88.1_5/curl-7.88.1_5-win64-mingw.zip' -OutFile 'curl.zip'"

echo Extracting curl...
powershell -Command "Expand-Archive -Path 'curl.zip' -DestinationPath 'temp' -Force"

echo Copying files...
powershell -Command "Copy-Item -Path 'temp\curl-7.88.1_5-win64-mingw\bin\*' -Destination 'C:\clib\curl\bin\' -Recurse -Force"
powershell -Command "Copy-Item -Path 'temp\curl-7.88.1_5-win64-mingw\include\*' -Destination 'C:\clib\curl\include\' -Recurse -Force"
powershell -Command "Copy-Item -Path 'temp\curl-7.88.1_5-win64-mingw\lib\*' -Destination 'C:\clib\curl\lib\' -Recurse -Force"

echo Cleaning up...
powershell -Command "Remove-Item -Path 'temp' -Recurse -Force"
powershell -Command "Remove-Item -Path 'curl.zip' -Force"

echo Curl installation complete!
pause