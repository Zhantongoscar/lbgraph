//在此填写 c1 到 c4 文件的功能描述
# c1 到 c4 文件的功能描述

## c1.bat
`c1.bat` 文件的功能是从csv读取设备，在mysql中创建设备 端子并预留连接。
创建type表格，用于标记设备的连接属性。

## c2.bat
`c2.bat` 为mysql的 types 表格 根据一些统用规则，自动建立连接。

## c3.bat
`c3.bat` python文件，用于csv文件 转换 vertex 和 edge ，筛选后写于 neo4j数据库

## c4.bat
`c4.bat` 导入 仿真simdevice 从mysql到 neo4j.
从mysql的 设备表增加内联数据，如线圈连接 触点连接到图论。
