# 图论数据预处理工具

## 功能概述
本工具用于处理电气柜连接数据，将其转换为图论数据结构。主要功能包括：
1. 读取Excel格式的原始数据
2. 筛选有效的柜内连接
3. 解析IEC 60204标识符
4. 生成图论数据结构（节点和边）
5. 保存清洗后的数据为JSON格式

## 使用方法
1. 准备Excel数据文件，确保包含以下列：
   - Consecutive number (序列号)
   - Connection color / number (颜色/编号)
   - Device (source) (源设备)
   - Device (target) (目标设备)

2. 运行程序：
   ```bash
   python src/data_preprocessor.py
   ```

3. 按照提示选择对应的列

4. 查看筛选结果

5. 输入文件名保存清洗后的数据

## 输出格式
生成的JSON文件包含以下结构：
```json
{
  "nodes": [
    {
      "id": "节点ID",
      "iec_identifier": "IEC标识符",
      "properties": {
        "function": "功能",
        "location": "位置",
        "device": "设备",
        "terminal": "端子"
      }
    }
  ],
  "edges": [
    {
      "source": "源节点",
      "target": "目标节点",
      "properties": {
        "color": "颜色",
        "serial_number": "序列号"
      }
    }
  ],
  "metadata": {
    "created_at": "创建时间",
    "version": "版本号"
  }
}
```

## 注意事项
1. 确保Excel文件路径正确
2. 选择列时请仔细核对列名
3. 保存文件时请确保文件名合法
4. 输出文件保存在output目录下