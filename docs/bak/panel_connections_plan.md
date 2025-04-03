# Panel Device内部连接实现计划

## 1. 需求分析
需要从MySQL数据库中读取panel_device_inner表的连接数据，并将其写入Neo4j数据库。

### 数据格式示例
```json
[
    {
        "to": "22",
        "from": "21",
        "type": "contact_connection"
    },
    {
        "to": "A2",
        "from": "A1",
        "type": "coil_connection"
    }
]
```

## 2. 实现步骤

### 2.1 数据获取
1. 在fetch_simulation_data方法中增加：
   ```sql
   SELECT * FROM panel_device_inner
   ```
2. 解析JSON格式的连接数据

### 2.2 数据处理
1. 创建新方法process_panel_connections处理连接数据
2. JSON解析和数据验证
3. 将from/to映射到对应的节点

### 2.3 Neo4j写入
1. 创建新方法create_panel_connections
2. 根据连接类型创建不同的关系：
   - contact_connection: 触点连接
   - coil_connection: 线圈连接

### 2.4 关系属性
为每个连接添加以下属性：
- type: 连接类型
- created_at: 创建时间戳
- source: 来源("panel_device_inner")

## 3. 代码修改
1. SimulationSyncer类
   - 新增process_panel_connections方法
   - 新增create_panel_connections方法
   - 修改sync_to_neo4j方法

2. 更新Neo4j查询
   - 增加面板连接相关的查询示例
   - 增加连接统计信息

## 4. 错误处理
1. JSON解析错误处理
2. 数据验证
   - 确保from/to节点存在
   - 验证连接类型有效性
3. 详细的错误日志

## 5. 测试计划
1. 测试JSON解析
2. 测试节点映射
3. 测试关系创建
4. 验证统计信息

## 6. 注意事项
1. 确保连接节点已存在
2. 处理可能的重复连接
3. 注意数据格式的一致性
4. 保持良好的日志记录

## 7. 后续步骤
1. 切换到code模式
2. 实现计划的功能
3. 进行测试
4. 更新文档