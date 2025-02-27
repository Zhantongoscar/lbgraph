//在此填写 c1 到 c4 文件的功能描述
# c1 到 c4 文件的功能描述

## c1.bat
`c1.bat` 文件的功能是从csv读取设备，在mysql中创建设备 端子并预留连接。
创建type表格，用于标记设备的连接属性。

## c1a.bat
`c1a.bat` 文件的功能是编译和运行 c1a_create_devicepoint_table.cpp 程序，该程序从CSV文件读取设备点信息，创建和填充 v_devices 表。此表中保存了设备的基本属性，如FDID、Function、Location、Device等，同时标记设备类型(如PLC设备、端子设备等)。

## c1b.bat
`c1b.bat` 文件的功能是编译和运行 c1b_create_vertexpoint_table.cpp 程序，该程序从CSV文件读取设备点信息，创建和填充 v_device_points 表。此表中保存了设备点的详细属性，包括点ID、所属设备、电气特性、功能标记(如isSocket、isSetPoint、isSensePoint)等，完成了设备点与设备的关联映射。

## c1c.bat
`c1c.bat` 文件的功能是编译和运行 c1c_create_conn.cpp 程序，该程序从CSV文件读取连接信息，创建和填充 conn_graph 表。此表保存了设备点之间的连接关系，包括连接编号、源点和目标点、颜色、连接类型(内部线圈、内部触点、外部连接)、电气特性(电压、电流、电阻)以及是否在柜内等信息。

## c2.bat
`c2.bat` 为mysql的 types 表格 根据一些统用规则，自动建立连接。

## c3.bat
`c3.bat` python文件，用于csv文件 转换 vertex 和 edge ，筛选后写于 neo4j数据库

## c4.bat
`c4.bat` 导入 仿真simdevice 从mysql到 neo4j.
从mysql的 设备表增加内联数据，如线圈连接 触点连接到图论。
