# 电路图分析工具

这是一个用于分析电路连接关系的工具，包括数据预处理和图论分析两个主要部分。

## 环境要求

1. Python 3.8+
2. 必需的Python库：
```bash
pip install -r requirements.txt
```

## 文件结构

```
src/
├── process_excel.py     # Excel数据预处理
├── graph.py            # 图论模型核心
├── graph_visualization.py  # 图形可视化
├── circuit_analysis.py    # 电路分析
└── main.py             # 图论分析主程序
```

## 工作流程

### 1. 数据预处理

将Excel数据转换为标准的JSON格式：

```bash
python src/process_excel.py
```

运行后会提示：
1. 选择Excel文件
2. 选择相关字段：
   - 图纸ID
   - 源点（起始连接点）
   - 目标点（目标连接点）
   - 导线截面
   - 导线颜色

输出：
- JSON格式的数据文件
- Excel格式的数据文件（用于查看）

### 2. 图论分析

使用处理好的JSON数据进行分析：

```bash
python src/main.py path/to/processed_data.json
```

例如：
```bash
python src/main.py reference/processed_data/EOS1350-1550线束表_20250110_030049.json
```

可选参数：
- `--output`或`-o`：指定输出目录（默认为'output'）

输出内容：
1. 可视化图形：
   - comparison.png：原始图和电柜子图的对比
   - cabinet_detail.png：电柜内部连接的详细图

2. 分析报告：
   - analysis_report.html：包含完整的分析结果
   - analysis_data.json：详细的分析数据

## 分析内容

1. 基本统计：
   - 闭合回路数量
   - 悬空节点数量
   - 并联连接数量
   - 串联连接数量

2. 连接性分析：
   - 图的连通性
   - 强连通分量
   - 关节点分析

3. 导线使用分析：
   - 截面分布统计
   - 颜色分布统计

4. 安全检查：
   - PE连接检查
   - 导线截面规范检查
   - 连接完整性检查

## 使用建议

1. 数据预处理：
   - 确保Excel数据格式正确
   - 仔细选择对应的字段
   - 检查生成的JSON数据

2. 图论分析：
   - 使用处理好的JSON文件
   - 查看可视化图形了解整体结构
   - 仔细阅读分析报告

## 开发说明

1. 添加新的分析规则：
   - 在 `circuit_analysis.py` 中扩展 `CircuitAnalyzer` 类
   - 在 `main.py` 中更新报告生成逻辑

2. 改进可视化：
   - 在 `graph_visualization.py` 中修改 `CircuitVisualizer` 类
   - 调整颜色、布局等参数

3. 添加新的数据处理功能：
   - 在 `process_excel.py` 中添加新的处理逻辑

## 注意事项

1. 数据预处理：
   - 保持Excel数据格式一致
   - 确保必要字段都已正确选择
   - 检查生成的JSON数据格式

2. 图论分析：
   - 确保JSON文件路径正确
   - 检查输出目录权限
   - 查看调试信息了解执行过程

3. 性能考虑：
   - 大型数据集可能需要更多内存
   - 可视化大型图可能需要更长时间
   - 考虑使用子图进行局部分析

## 常见问题

1. 如果遇到模块导入错误：
```bash
pip install -r requirements.txt
```

2. 如果图形显示不正常：
```bash
# 确保安装了matplotlib
pip install matplotlib
```

3. 如果JSON读取错误：
   - 检查文件路径是否正确
   - 确认JSON格式是否有效

4. 如果分析报告为空：
   - 检查JSON数据是否包含必要字段
   - 查看程序输出的调试信息