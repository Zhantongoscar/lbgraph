Write-Host "Building c3_create_s2t_conn.cpp..."

# Try to compile using g++
$output = & g++ -Wall -O2 c3_create_s2t_conn.cpp -o s2t_conn.exe -I. -Iinclude -std=c++17 2>&1

# Display the output
$output | ForEach-Object { Write-Host $_ }

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful"
    Write-Host "Running program..."
    & ./s2t_conn.exe
} else {
    Write-Host "Build failed with error $LASTEXITCODE"
}