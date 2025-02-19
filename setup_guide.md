# 开发环境配置指南

为了编译和运行设备类型管理程序，需要按以下步骤配置开发环境：

## 1. 安装编译工具
1. 下载并安装 MinGW-w64：
   - 访问：https://github.com/niXman/mingw-builds-binaries/releases
   - 下载 x86_64-13.2.0-release-win32-seh-msvcrt-rt_v11-rev1.7z
   - 解压到 C:\mingw64
   - 将 C:\mingw64\bin 添加到系统环境变量 Path 中

2. 验证安装：
   - 打开命令提示符
   - 输入 `g++ --version` 确认安装成功

## 2. 配置 MySQL C Connector 库文件

1. 下载 MySQL C API 文件：
   - 访问：https://downloads.mysql.com/archives/get/p/19/file/mysql-connector-c-6.1.11-winx64.zip
   - 下载并解压 zip 文件

2. 复制必要文件到项目的 clib 目录：
   - 从解压目录的 lib64/ 复制：
     * libmysql.dll -> clib/mysql/lib/
     * libmysql.lib -> clib/mysql/lib/
   - 从解压目录的 include/ 复制所有 .h 文件 -> clib/mysql/include/

## 3. 编译程序

在命令提示符中执行：
```cmd
build.bat
```

## 4. 运行程序

完成编译后，运行生成的可执行文件：
```cmd
devicetype.exe
```

## 注意事项

1. 确保 config.json 文件在程序运行目录下
2. 确保 MySQL 服务器（192.168.35.10）可以正常访问
3. 控制台会自动设置为 UTF-8 编码

如果遇到编译错误，请检查：
- MinGW-w64 是否正确安装（g++ 命令是否可用）
- 系统环境变量 Path 中是否包含 C:\mingw64\bin
- 所需库文件是否都已正确复制到 clib/mysql 目录
- config.json 文件是否存在且格式正确