
















4. 检查数据是否按照 `connection_number` 升序排列，且没有重复的 `connection_number`。3. 确认 `source_name` 和 `target_name` 列正确显示特殊字符，没有被 Excel 错误解析为公式。2. 确认 `connection_number` 列为整数格式。1. 打开 `graph_data.xlsx` 文件。## 验证数据3. 检查 `output` 目录，确认生成了 `graph_data.csv` 和 `graph_data.xlsx` 文件。   ```   python export_graph_data.py   ```2. 运行 `export_graph_data.py` 脚本：1. 确保所有依赖已正确安装。## 导出图数据# 测试指南