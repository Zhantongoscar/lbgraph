# Get current user's PATH environment variable
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")

# Python installation paths
$pythonPath = "C:\Users\13701\AppData\Local\Programs\Python\Python313"
$pythonScriptsPath = "C:\Users\13701\AppData\Local\Programs\Python\Python313\Scripts"

# Check if paths are already in PATH
if (-not $userPath.Contains($pythonPath)) {
    # Add Python paths to PATH
    $newPath = $userPath + ";" + $pythonPath + ";" + $pythonScriptsPath
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
    Write-Host "Python paths added to user environment variables"
} else {
    Write-Host "Python paths already exist in environment variables"
}

# Refresh current session's environment variables
$env:Path = [Environment]::GetEnvironmentVariable("PATH", "User")

Write-Host "Environment variables setup completed"
Write-Host "Testing Python availability:"
python --version