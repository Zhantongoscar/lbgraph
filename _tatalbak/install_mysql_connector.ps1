# MySQL Connector/C 安装脚本

$mysqlConnectorUrl = "https://dev.mysql.com/get/Downloads/Connector-C/mysql-connector-c-6.1.11-winx64.zip"
$downloadPath = "mysql-connector.zip"
$installPath = "C:\clib\mysql"

Write-Host "正在创建安装目录..."
New-Item -ItemType Directory -Force -Path $installPath | Out-Null

Write-Host "下载 MySQL Connector/C..."
Invoke-WebRequest -Uri $mysqlConnectorUrl -OutFile $downloadPath

Write-Host "解压文件..."
Expand-Archive -Path $downloadPath -DestinationPath "temp" -Force

Write-Host "复制文件到指定目录..."
Copy-Item "temp\mysql-connector-c-6.1.11-winx64\include\*" -Destination "$installPath\include" -Recurse -Force
Copy-Item "temp\mysql-connector-c-6.1.11-winx64\lib\*" -Destination "$installPath\lib" -Recurse -Force

Write-Host "清理临时文件..."
Remove-Item -Path $downloadPath -Force
Remove-Item -Path "temp" -Recurse -Force

Write-Host "MySQL Connector/C 安装完成！"
Write-Host "库文件已安装到: $installPath"