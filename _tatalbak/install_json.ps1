$installPath = "include\nlohmann"
$jsonUrl = "https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp"

# 确保目录存在
New-Item -ItemType Directory -Path $installPath -Force

# 下载 json.hpp
Write-Host "正在下载 json.hpp..."
Invoke-WebRequest -Uri $jsonUrl -OutFile "$installPath\json.hpp"

Write-Host "JSON库安装完成！"