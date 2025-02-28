//在此填写 c1 到 c4 文件的功能描述
# c1 到 c4 文件的功能描述


## c1a.bat
### zt 从csv创建 v_devices 表
`c1a.bat` 文件的功能是编译和运行 c1a_create_devicepoint_table.cpp 程序，该程序从CSV文件读取设备点信息，创建和填充 v_devices 表。此表中保存了设备的基本属性，如FDID、Function、Location、Device等，同时标记设备类型(如PLC设备、端子设备等)。

## c1b.bat
### zt 从csv创建 v_device_points 表
`c1b.bat` 文件的功能是编译和运行 c1b_create_vertexpoint_table.cpp 程序，该程序从CSV文件读取设备点信息，创建和填充 v_device_points 表。此表中保存了设备点的详细属性，包括点ID、所属设备、电气特性、功能标记(如isSocket、isSetPoint、isSensePoint)等，完成了设备点与设备的关联映射。

## c1c.bat
### zt 从csv创建 conn_graph 表
`c1c.bat` 文件的功能是编译和运行 c1c_create_conn.cpp 程序，该程序从CSV文件读取连接信息，创建和填充 conn_graph 表。此表保存了设备点之间的连接关系，包括连接编号、源点和目标点、颜色、连接类型(内部线圈、内部触点、外部连接)、电气特性(电压、电流、电阻)以及是否在柜内等信息。



## c2a.bat
### zt: 建立设备类型的连机定义 以及具体实例的连接空白表。
zt: 建立设备类型的连机定义 以及具体实例的连接空白表。
`c2a.bat` 文件的功能是编译和运行 c2a_create_devicetype_table.cpp 程序，该程序用于创建和填充 panel_device_inner 表和 panel_types 表。程序从配置文件中读取CSV路径和项目编号，然后从CSV文件中提取设备信息，分析设备端口并根据端口特征进行设备类型分类。它主要执行以下功能：
1. 解析设备标识符，提取功能(Function)和位置(Location)信息
2. 为每个设备创建端口列表(terminal_list)
3. 根据端口特征对设备进行分类，为相似设备分配相同的类型(TYPE)
4. 创建内部连接列表(inner_conn_list)，定义设备内部端口之间的关系
5. 自动清理端口数量少于2个的无效设备记录
6. 使用MySQL事务确保数据完整性
7. 支持UTF-8字符集处理中文描述

## c2b.bat
### zt: 从Leybold的另外设备表 导出 同样leybolede 设备库 leybold_device_lib

`c2b.bat` 文件的功能是编译和运行 c2b_importExcelLeyboldPart.cpp 程序，该程序用于导入来自Leybold设备库的数据到MySQL数据库。主要功能包括：
1. 扫描data目录下的CSV文件并提供文件选择界面
2. 处理带有引号和换行符的复杂CSV格式
3. 创建和管理leybold_device_lib表，包含以下字段：
   - id (自增主键)
   - level (层级)
   - number (编号)
   - type (类型)
   - assembly_mode (装配模式)
   - name (名称)
   - operating_element (操作元件)
   - bom_class (BOM类别)
   - name_zh_chs (中文名称)
4. 支持UTF-8编码，确保中文字符正确显示
5. 使用MySQL事务确保数据导入的完整性
6. 提供详细的导入进度和错误报告

## d1a.bat
### zt: 设备点形成图
在config.json 中有neo4j 和mysql的信息。
从设备v_devices mysql的数据表读取数据作为点，生成一个LB_TT图。
