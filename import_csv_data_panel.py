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
                if test_count >= 50:
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