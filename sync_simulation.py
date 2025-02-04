[代码更新内容主要包含以下改进：

1. 添加层级分类：
```python
# 在创建节点时添加层级判断
node_layer = 'Cabinet' if device['location'] == 'MainCabinet' else 'External'
if device['is_simulated']:
    node_layer = 'Simulation'
```

2. 连接关系管理：
```python
# 创建连接关系时检查IsEnabled属性
tx.run("""
    MATCH (src:Vertex {DeviceId: $src_id, PointIndex: $src_index, IsEnabled: true})
    MATCH (dst:Vertex {DeviceId: $dst_id, PointIndex: $dst_index, IsEnabled: true})
    CREATE (src)-[:CONNECTS {
        resistance: $resistance,
        capacity: $capacity,
        created_at: datetime()
    }]->(dst)
""")
```

3. 电压传播逻辑：
```python
# 使用APOC库进行电压传播模拟
tx.run("""
    CALL apoc.path.expandConfig($startNode, {
        relationshipFilter: "CONNECTS>",
        minLevel: 1,
        maxLevel: 5,
        bfs: true,
        terminatorNodes: [],
        sequence: nil
    })
    YIELD path
    WITH relationships(path) AS rels
    UNWIND rels AS rel
    WITH rel.dst AS node, SUM(rel.src.Voltage * (1 - rel.resistance)) AS newVoltage
    SET node.Voltage = newVoltage
""")
```

