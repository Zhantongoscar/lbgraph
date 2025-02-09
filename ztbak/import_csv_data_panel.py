# import csv
# from neo4j import GraphDatabase
# from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# class DataImporter:
#     def __init__(self):
#         self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

#     def close(self):
#         self.driver.close()

#     def get_vertex_id(self, node_str):
#         """获取节点ID
#         从完整字符串中提取第一个+后的所有字符串作为节点ID
#         """
#         plus_index = node_str.find('+')
#         if plus_index != -1:
#             vertex_id = node_str[plus_index + 1:].strip()
#         else:
#             vertex_id = node_str.strip()
            
#         print(f"原始字符串: {node_str}")
#         print(f"提取的ID: {vertex_id}")
#         return vertex_id

#     def parse_node_properties(self, node_str):
#         """解析节点属性
#         从字符串中提取Function、Location、Device和Terminal属性
#         基于=+-:四种标记进行分割
#         """
#         print(f"\n开始解析节点属性: {node_str}")
        
#         # 保存原始字符串作为name属性
#         properties = {
#             'name': node_str,
#         }
        
#         # 如果字符串中没有任何标记,在开头添加标记
#         if not any(mark in node_str for mark in ['=', '+', '-', ':']):
#             print(f"未找到任何标记,添加默认标记")
#             node_str = f"=+{node_str}"
#             print(f"添加标记后: {node_str}")
        
#         # 如果没有冒号,在最后一个减号后添加冒号
#         if ':' not in node_str:
#             last_dash_index = node_str.rfind('-')
#             if last_dash_index != -1:
#                 node_str = f"{node_str[:last_dash_index+1]}:{node_str[last_dash_index+1:]}"
#                 print(f"添加冒号后: {node_str}")
#             else:
#                 node_str = f"{node_str}:"
#                 print(f"在末尾添加冒号: {node_str}")

#         # 查找所有标记的位置
#         equal_index = node_str.find('=')
#         plus_index = node_str.find('+')
#         dash_index = node_str.find('-')
#         colon_index = node_str.find(':')

#         print(f"标记位置: = ({equal_index}), + ({plus_index}), - ({dash_index}), : ({colon_index})")

#         # 如果没有等号,假设它在开头
#         if equal_index == -1:
#             equal_index = 0

#         # 提取各个部分
#         if plus_index != -1:
#             function = node_str[equal_index+1:plus_index].strip()
#             if function:
#                 properties['function'] = function
#                 print(f"提取Function: {function}")
                
#             if dash_index != -1:
#                 location = node_str[plus_index+1:dash_index].strip()
#                 if location:
#                     properties['location'] = location
#                     print(f"提取Location: {location}")
                    
#                 if colon_index != -1:
#                     device = node_str[dash_index+1:colon_index].strip()
#                     if device:
#                         properties['device'] = device
#                         print(f"提取Device: {device}")
                        
#                         # 增加 type 属性
#                         if device.startswith('A'):
#                             properties['type'] = 'PLC'
#                             print(f"设置 type 属性为 PLC")
#                         elif not location.startswith('K1.'):
#                             properties['type'] = 'field'
#                             print(f"设置 type 属性为 field")
#                         else:
#                             properties['type'] = 'panel'
#                             print(f"设置 type 属性为 panel")
                        
#                     terminal = node_str[colon_index+1:].strip()
#                     if terminal:
#                         properties['terminal'] = terminal
#                         print(f"提取Terminal: {terminal}")
#                 else:
#                     device = node_str[dash_index+1:].strip()
#                     if device:
#                         properties['device'] = device
#                         print(f"提取Device: {device}")
                        
#                         # 增加 type 属性
#                         if device.startswith('A'):
#                             properties['type'] = 'PLC'
#                             print(f"设置 type 属性为 PLC")
#                         elif not location.startswith('K1.'):
#                             properties['type'] = 'field'
#                             print(f"设置 type 属性为 field")
#                         else:
#                             properties['type'] = 'panel'
#                             print(f"设置 type 属性为 panel")
#             else:
#                 location = node_str[plus_index+1:].strip()
#                 if location:
#                     properties['location'] = location
#                     print(f"提取Location: {location}")
#         else:
#             function = node_str
#             if function:
#                 properties['function'] = function
#                 print(f"提取Function: {function}")

#         print(f"最终属性: {properties}\n")
#         return properties

#     def import_data(self):
#         with open('data/SmartWiringzta.csv', mode='r', encoding='utf-8') as file:
#             # 跳过前两行合并的标题行
#             next(file)
#             next(file)
            
#             csv_reader = csv.reader(file)
#             fieldnames = [
#                 'Consecutive number',
#                 'Connectiondevice identifier(full)',
#                 'cableType/connections number/RCS',
#                 'Connection: Type designation',
#                 'Connection color / number',
#                 'Connection: Cross-section / diameter',
#                 'Length (full)',
#                 'source',
#                 'target',
#                 'Wire termination processing source',
#                 'Wire termination processing target',
#                 'Routing direction source',
#                 'Routing direction target',
#                 'Bundle',
#                 'Layout space: Routing track',
#                 'Connection designation',
#                 'Remark'
#             ]
            
#             # csv_reader = csv.DictReader(file, fieldnames=fieldnames)
            
#             count = 0
#             i=0
#             test_count = 0  # 在循环之前初始化 test_count
#             for row in csv_reader:
#                 # 跳过第一行（字段名）
#                 if i == 0:
#                     i += 1
#                     continue
                
#                 # 构建字典
#                 row_dict = {}
#                 for j, value in enumerate(row):
#                     row_dict[fieldnames[j]] = value.strip()
                
#                 # 检查是否存在 None 键
#                 if None in row_dict:
#                     print(f"发现包含 None 键的行: {row_dict}")
#                     # 可以选择跳过该行或用默认值填充
#                     # continue  # 跳过该行
#                     row_dict.pop(None)  # 移除 None 键
                
#                 # 打印row 和换行
#                 i+=1
#                 print(f"{i}\n", row_dict, end='\n\n')  # 在行后添加两个换行符
                
#                 source_str = row_dict.get('source', '').strip()
#                 target_str = row_dict.get('target', '').strip()
#                 wire_termination_processing_source_str = row_dict.get('Wire termination processing source', '').strip()
#                 wire_termination_processing_target_str = row_dict.get('Wire termination processing target', '').strip()

#                 # 获取或创建 Wire termination processing source Vertex
#                 wire_termination_processing_source_id = self.get_vertex_id(wire_termination_processing_source_str)
#                 wire_termination_processing_source_properties = self.parse_node_properties(wire_termination_processing_source_str)

#                 # 获取或创建 Wire termination processing target Vertex
#                 wire_termination_processing_target_id = self.get_vertex_id(wire_termination_processing_target_str)
#                 wire_termination_processing_target_properties = self.parse_node_properties(wire_termination_processing_target_str)

#                 # 获取或创建 source Vertex
#                 source_id = self.get_vertex_id(source_str)
#                 source_properties = self.parse_node_properties(source_str)

#                 # 获取或创建 target Vertex
#                 target_id = self.get_vertex_id(target_str)
#                 target_properties = self.parse_node_properties(target_str)

#                 wire_properties = {
#                     'wire_number': row_dict.get('Consecutive number', ''),
#                     'cable_type': row_dict.get('cableType/connections number/RCS', ''),
#                     # 'connection_type': row_dict.get('Connection: Type designation', ''), # 删除 connection_type
#                     'color': row_dict.get('Connection color / number', ''),
#                     # 'cross_section': row_dict.get('Connection: Cross-section / diameter', ''), # 删除 cross_section
#                     'length': row_dict.get('Length (full)', ''),
#                     'bundle': row_dict.get('Bundle', ''),
#                     'remark': row_dict.get('Remark', '')
#                 }

#                 wire_properties = {k: v for k, v in wire_properties.items() if v}

#                 with self.driver.session() as session:
#                     # 创建节点和关系
#                     query = (
#                         "MERGE (w_source:Vertex {id: $wire_termination_processing_source_id}) "
#                         "SET w_source += $wire_termination_processing_source_properties "
#                         "MERGE (w_target:Vertex {id: $wire_termination_processing_target_id}) "
#                         "SET w_target += $wire_termination_processing_target_properties "
#                         "MERGE (source:Vertex {id: $source_id}) "
#                         "SET source += $source_properties "
#                         "MERGE (target:Vertex {id: $target_id}) "
#                         "SET target += $target_properties "
#                         "MERGE (source)-[c:conn]->(target) " # 修改关系名称为 conn
#                         "SET c = $wire_properties "
#                         "MERGE (target)-[c2:conn]->(source) " # 修改关系名称为 conn
#                         "SET c2 = $wire_properties"
#                     )
#                     session.run(
#                         query,
#                         wire_termination_processing_source_id=wire_termination_processing_source_id,
#                         wire_termination_processing_source_properties=wire_termination_processing_source_properties,
#                         wire_termination_processing_target_id=wire_termination_processing_target_id,
#                         wire_termination_processing_target_properties=wire_termination_processing_target_properties,
#                         source_id=source_id,
#                         target_id=target_id,
#                         source_properties=source_properties,
#                         target_properties=target_properties,
#                         wire_properties=wire_properties
#                     )
#                     count += 1

#                     if count % 100 == 0:
#                         print(f"已处理 {count} 条连接")

#                 test_count += 1
#                 if test_count >= 200:
#                     print("已处理10行数据，停止测试")
#                     break

# if __name__ == "__main__":
#     importer = DataImporter()
#     try:
#         print("开始导入数据...")
#         importer.import_data()
#         print("数据导入完成")
#     except Exception as e:
#         print(f"导入过程中出现错误: {str(e)}")
#     finally:
#         importer.close()



import csv
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

class DataImporter:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def is_pe_or_n_terminal(self, terminal):
        """检查端子是否为 PE 或 N 端子
        PE: 包含'PE'的任何端子
        N: 必须精确匹配'N'
        """
        terminal = terminal.upper()
        return 'PE' in terminal or terminal == 'N'

    def get_vertex_id(self, node_str):
        """获取节点ID
        从完整字符串中提取第一个+后的所有字符串作为节点ID
        """
        node_str = node_str.strip()
        plus_index = node_str.find('+')
        if plus_index != -1:
            vertex_id = node_str[plus_index + 1:].strip()
        else:
            vertex_id = node_str.strip()
        print(f"完整设备标识符: {node_str}")
        print(f"简化设备标识符: {vertex_id}")
        return vertex_id

    def parse_node_properties(self, node_str):
        """解析节点属性
        从字符串中提取Function、Location、Device和Terminal属性
        基于=+-:四种标记进行分割
        """
        formatted_output = "="
        properties = {'name': node_str}
        
        if not any(mark in node_str for mark in ['=', '+', '-', ':']):
            print(f"未找到任何标记,添加默认标记")
            node_str = f"=+{node_str}"
            print(f"添加标记后: {node_str}")
        
        if ':' not in node_str:
            last_dash_index = node_str.rfind('-')
            if last_dash_index != -1:
                node_str = f"{node_str[:last_dash_index+1]}:{node_str[last_dash_index+1:]}"
            else:
                node_str = f"{node_str}:"

        equal_index = node_str.find('=')
        plus_index = node_str.find('+')
        dash_index = node_str.find('-')
        colon_index = node_str.find(':')

        if equal_index == -1:
            equal_index = 0

        if plus_index != -1:
            function = node_str[equal_index+1:plus_index].strip()
            if function:
                properties['function'] = function
                formatted_output += f"<{function}>+"
                
            if dash_index != -1:
                location = node_str[plus_index+1:dash_index].strip()
                if location:
                    properties['location'] = location
                    formatted_output += f"<{location}>-"
                    
                if colon_index != -1:
                    device = node_str[dash_index+1:colon_index].strip()
                    if device:
                        properties['device'] = device
                        formatted_output += f"<{device}>;"
                        
                        if device.startswith('A'):
                            properties['type'] = 'PLC'
                        elif not location.startswith('K1.'):
                            properties['type'] = 'field'
                        else:
                            properties['type'] = 'panel'
                        print(f"type={properties['type']}")
                        
                    terminal = node_str[colon_index+1:].strip()
                    if terminal:
                        properties['terminal'] = terminal
                        formatted_output += f"<{terminal}>"
        
        print(formatted_output)
        print(f"最终属性: {properties}")
        return properties

    def import_data(self):
        with open('data/SmartWiringzta.csv', mode='r', encoding='utf-8') as file:
            next(file)  # 跳过前两行合并的标题行
            next(file)
            
            csv_reader = csv.reader(file)
            fieldnames = [
                'Consecutive number',
                'Connectiondevice identifier(full)',
                'cableType/connections number/RCS',
                'Connection: Type designation',
                'Connection color / number',
                'Connection: Cross-section / diameter',
                'Length (full)',
                'source',
                'target',
                'Wire termination processing source',
                'Wire termination processing target',
                'Routing direction source',
                'Routing direction target',
                'Bundle',
                'Layout space: Routing track',
                'Connection designation',
                'Remark'
            ]
            
            count = 0
            i = 0
            test_count = 0
            
            for row in csv_reader:
                print(f"-------------------- i = {i}, count = {count} --------------------")
                
                if i == 0:  # 跳过第一行（字段名）
                    i += 1
                    continue
                
                row_dict = {fieldnames[j]: value.strip() for j, value in enumerate(row)}
                if None in row_dict:
                    row_dict.pop(None)
                
                print(f"**row No{i}**\n", row_dict, end='\n\n')
                
                source_str = row_dict.get('source', '').strip()
                target_str = row_dict.get('target', '').strip()

                source_id = self.get_vertex_id(source_str)
                source_properties = self.parse_node_properties(source_str)

                target_id = self.get_vertex_id(target_str)
                target_properties = self.parse_node_properties(target_str)

                # 检查端子是否为 PE 或 N
                source_terminal = source_properties.get('terminal', '')
                target_terminal = target_properties.get('terminal', '')
                skip_terminals = (self.is_pe_or_n_terminal(source_terminal) or 
                                self.is_pe_or_n_terminal(target_terminal))

                wire_properties = {
                    'wire_number': row_dict.get('Consecutive number', ''),
                    'cable_type': row_dict.get('cableType/connections number/RCS', ''),
                    'color': row_dict.get('Connection color / number', ''),
                    'length': row_dict.get('Length (full)', ''),
                    'bundle': row_dict.get('Bundle', ''),
                    'remark': row_dict.get('Remark', '')
                }
                wire_properties = {k: v for k, v in wire_properties.items() if v}

                if (source_properties.get('type') in ('panel', 'PLC') and 
                    target_properties.get('type') in ('panel', 'PLC') and 
                    not skip_terminals):
                    with self.driver.session() as session:
                        query = (
                            "MERGE (source:Vertex {id: $source_id}) "
                            "SET source += $source_properties "
                            "MERGE (target:Vertex {id: $target_id}) "
                            "SET target += $target_properties "
                            "MERGE (source)-[c:conn]->(target) "
                            "SET c = $wire_properties "
                            "MERGE (target)-[c2:conn]->(source) "
                            "SET c2 = $wire_properties"
                        )
                        session.run(
                            query,
                            source_id=source_id,
                            source_properties=source_properties,
                            target_id=target_id,
                            target_properties=target_properties,
                            wire_properties=wire_properties
                        )
                        count += 1

                        if count % 100 == 0:
                            print(f"已处理 {count} 条连接")
                else:
                    if skip_terminals:
                        print(f"跳过PE/N连接：source terminal = {source_terminal}, target terminal = {target_terminal}")
                    else:
                        print(f"跳过连接：source type = {source_properties.get('type')}, target type = {target_properties.get('type')}")

                i += 1
                test_count += 1
                if test_count >= 2000:
                    print("已处理5行数据，停止测试")
                    break

if __name__ == "__main__":
    importer = DataImporter()
    try:
        print("开始导入数据...")
        importer.import_data()
        print("数据导入完成")
    except Exception as e:
        print(f"导入过程中出现错误: {str(e)}")
    finally:
        importer.close()