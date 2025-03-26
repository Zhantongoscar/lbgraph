# force_update_device_point 功能实现计划

## 功能目标
根据v_csv_devpoint表中的Function、Device和Terminal值，通过多表关联查询更新Type字段。

## 数据流图

```mermaid
graph TD
    A[开始] --> B[查询v_csv_devpoint记录]
    B --> C[获取Function,Device,Terminal]
    C --> D[在v_plc_typeitem中查询Type]
    D --> E{是否找到Type?}
    E -->|是| F[在device_types中查询id]
    E -->|否| G[跳过此记录]
    F --> H[将Terminal转换为point_index]
    H --> I[在device_type_points中查询匹配记录]
    I --> J{是否找到匹配?}
    J -->|是| K[更新v_csv_devpoint的Type]
    J -->|否| L[跳过此记录]
    K --> M[提交更新]
    G --> N[处理下一条记录]
    L --> N
    N --> O{是否还有记录?}
    O -->|是| B
    O -->|否| P[结束]
```

## 实现步骤

1. **函数定义**
   ```python
   def force_update_device_point(conn):
       """根据多表关联更新v_csv_devpoint的Type字段"""
   ```

2. **查询v_csv_devpoint记录**
   ```sql
   SELECT id, Function, Device, Terminal 
   FROM v_csv_devpoint
   WHERE Type IS NULL OR Type = ''
   ```

3. **处理每条记录**
   - 从v_plc_typeitem获取Type:
     ```sql
     SELECT Type FROM v_plc_typeitem
     WHERE Function = %s AND Device = %s
     LIMIT 1
     ```
   - 从device_types获取id:
     ```sql
     SELECT id FROM device_types
     WHERE type_name = %s
     LIMIT 1
     ```
   - 转换Terminal为point_index:
     ```python
     point_index = int(Terminal.replace('T', ''))
     ```
   - 从device_type_points获取point_type:
     ```sql
     SELECT point_type FROM device_type_points
     WHERE device_type_id = %s AND point_index = %s
     LIMIT 1
     ```

4. **更新记录**
   ```sql
   UPDATE v_csv_devpoint
   SET Type = %s
   WHERE id = %s
   ```

5. **提交事务**
   ```python
   conn.commit()
   ```

## 注意事项
1. Terminal值需要转换为point_index（如"T1"→1）
2. 需要处理可能的数据类型转换异常
3. 建议添加事务回滚机制
4. 添加适当的日志记录