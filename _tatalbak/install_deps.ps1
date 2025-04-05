# Ensure we can run scripts
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

Write-Host "正在安装依赖包..." -ForegroundColor Green

$packages = @(
    @{name="pandas"; version=">=2.2.0"},
    @{name="neo4j"; version=">=5.13.0"},
    @{name="openpyxl"; version=">=3.1.2"},
    @{name="pymysql"; version=">=1.1.0"},
    @{name="xlsxwriter"; version=">=3.1.9"}
)

foreach ($package in $packages) {
    $fullName = "$($package.name)$($package.version)"
    Write-Host "`n正在安装 $fullName..." -ForegroundColor Cyan
    
    try {
        if ($package.name -eq "neo4j") {
            $cmd = "pip install --no-deps $fullName"
        } else {
            $cmd = "pip install $fullName"
        }
        
		Write-Host "执行命令: $cmd" -ForegroundColor Yellow
        $output = Invoke-Expression $cmd 2>&1
		Write-Host "命令输出: $output" -ForegroundColor Gray
		
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $($package.name) 安装成功" -ForegroundColor Green
        } else {
            Write-Host "❌ $($package.name) 安装失败" -ForegroundColor Red
            Write-Host "错误代码: $LASTEXITCODE" -ForegroundColor Red
            Write-Host "错误信息: $output" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ 安装 $($package.name) 时出错: $_" -ForegroundColor Red
    }
}

Write-Host "`n安装完成。正在验证..." -ForegroundColor Green

# 验证是否所有包都已安装
$allInstalled = $true
foreach ($package in $packages) {
    $checkCmd = "pip show $($package.name)"
    $installed = Invoke-Expression $checkCmd
    
    if (-not $installed) {
        Write-Host "❌ $($package.name) 未安装成功" -ForegroundColor Red
        $allInstalled = $false
    }
}

if ($allInstalled) {
    Write-Host "`n✅ 所有依赖包已成功安装!" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ 某些包可能未正确安装，请检查上述输出" -ForegroundColor Yellow
}

Write-Host "`n按任意键退出..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
