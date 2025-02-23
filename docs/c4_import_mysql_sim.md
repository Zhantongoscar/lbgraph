# c4_import_mysql_sim.py 文件说明

## 1. 基本功能
该文件实现了一个MySQL到Neo4j的数据同步工具，主要用于同步仿真设备数据。

## 2. 主要组件

### SimulationSyncer类
核心同步器类，包含以下主要方法：
- `__init__`: 初始化数据库连接
- `connect_mysql`: 建立MySQL连接
- `fetch_simulation_data`: 获取仿真数据
- `sync_to_neo4j`: 同步数据到Neo4j
- `_validate_data`: 数据验证
- `_create_simulation_vertices`: 创建仿真节点
- `_create_connections`: 创建节点间连接

### 数据模型
从MySQL读取的三种数据：
1. 设备类型(device_types)
2. 设备(devices)
3. 点位配置(device_type_points)

### Neo4j节点属性
创建的节点包含以下属性：
- name: 节点名称
- Function: 功能类型(B/D)
- Location: 位置信息
- Device: 设备ID
- Terminal: 端子号
- UnitType: 单元类型
- DeviceId: 设备ID
- PointIndex: 点位索引
- Voltage: 电压值
- NodeLayer: 节点层级
- type: 节点类型
- IsEnabled: 启用状态
- LastUpdate: 更新时间

### 连接关系类型
1. INTERNAL_CONNECTION: 设备内部连接
2. ADJACENT_CONNECTION: 相邻设备连接

## 3. 数据流程
1. 连接MySQL数据库
2. 获取设备类型、设备和点位数据
3. 验证数据完整性
4. 创建Neo4j节点
5. 建立节点间连接
6. 生成统计信息

## 4. 错误处理
- MySQL连接错误处理
- 数据验证警告
- Neo4j操作错误处理
- 详细的日志记录

## 5. 查询示例
提供6种Neo4j查询示例：
1. 查看所有仿真节点
2. 按类型统计节点
3. 查看启用的节点
4. 查看连接关系
5. 按设备分组统计
6. 查找孤立节点

## 6. 命令行参数
支持自定义数据库连接参数：
- MySQL: host, user, password, database
- Neo4j: uri, user, password

## 7. 输出内容
- 详细的操作日志
- 节点创建统计
- 连接关系统计
- 按设备分组的节点列表

## 8. 注意事项
1. 运行前确保MySQL和Neo4j服务可用
2. 检查配置文件(config.py)中的连接参数
3. 确保数据库权限正确
4. 注意大量数据同步时的性能影响