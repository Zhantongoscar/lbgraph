# Python库安装指南

## 前置条件
- 已安装 Python 3.x
- 已安装 pip 包管理器

## 安装步骤

1. 首先升级 pip、setuptools 和 wheel：
```
python -m pip install --upgrade pip setuptools wheel
```

2. 使用管理员权限运行PowerShell，进入项目目录：
```
cd c:\project\2025\2025 leybold 图论\lbgraph
```

3. 运行安装脚本：
```
.\install_deps.ps1
```

如果出现权限问题，可以执行：
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
```

4. 等待安装完成。安装过程会自动安装以下依赖：
- pandas: 数据处理库
- neo4j: 图数据库驱动
- openpyxl: Excel文件处理
- pymysql: MySQL数据库驱动
- xlsxwriter: Excel文件写入

## 常见问题

1. 如果安装neo4j失败，可以尝试单独安装较新版本：
```
pip install neo4j>=5.13.0 --no-deps
```

2. 如果遇到权限问题，请确保以管理员身份运行PowerShell

3. 如果需要单独安装某个包：
```
pip install <包名>
```

## 验证安装

安装完成后，可以运行测试连接：
```
python export_graph_data.py
```

如果看到成功连接的提示，说明安装成功。
