@echo on
echo Building test.cpp...

g++ test.cpp -o test.exe -I. -Iinclude -std=c++17
if %errorlevel% equ 0 (
    echo Build successful
    echo Running program...
    test.exe
) else (
    echo Build failed with error %errorlevel%
)
pause