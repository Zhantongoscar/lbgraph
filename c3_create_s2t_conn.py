from neo4j import GraphDatabase
import csv
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

class GraphConnector:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def get_vertex_id(self, node_str):
        """从完整字符串中提取节点ID"""
        plus_index = node_str.find('+')
        if plus_index != -1:
            vertex_id = node_str[plus_index + 1:].strip()
        else:
            vertex_id = node_str.strip()
        return vertex_id

    def parse_node_properties(self, node_str):
        """解析节点属性"""
        properties = {
            'name': node_str,
            'function': '',
            'location': '',
            'device': '',
            'terminal': '',
            'type': 'panel'  # 默认类型
        }

        # 处理特殊情况
        if not any(c in node_str for c in ['=', '+', '-', ':']):
            node_str = "=+" + node_str

        # 解析各个部分
        parts = node_str.split('+')
        if len(parts) > 1:
            properties['function'] = parts[0].replace('=', '').strip()
            remaining = parts[1]

            # 解析位置和设备
            parts = remaining.split('-')
            if len(parts) > 1:
                properties['location'] = parts[0].strip()
                device_terminal = parts[1]

                # 解析设备和端子
                if ':' in device_terminal:
                    device, terminal = device_terminal.split(':')
                    properties['device'] = device.strip()
                    properties['terminal'] = terminal.strip()
                else:
                    properties['device'] = device_terminal.strip()

        # 设置类型
        if properties['device']:
            if properties['device'].startswith('A'):
                properties['type'] = 'PLC'
            elif properties['location'] and not properties['location'].startswith('K1.'):
                properties['type'] = 'field'

        return properties

    def is_pe_or_n_terminal(self, terminal):
        """检查端子是否为PE或N"""
        if not terminal:
            return False
        terminal = terminal.upper()
        return 'PE' in terminal or terminal == 'N'

    def create_connection(self, source_str, target_str, wire_properties):
        """创建两个顶点之间的连接"""
        # 获取顶点ID和属性
        source_id = self.get_vertex_id(source_str)
        source_properties = self.parse_node_properties(source_str)
        target_id = self.get_vertex_id(target_str)
        target_properties = self.parse_node_properties(target_str)

        # 检查是否跳过PE/N连接
        if (self.is_pe_or_n_terminal(source_properties['terminal']) or 
            self.is_pe_or_n_terminal(target_properties['terminal'])):
            print(f"跳过PE/N连接: {source_str} -> {target_str}")
            return False

        # 只处理panel和PLC之间的连接
        if not ((source_properties['type'] in ['panel', 'PLC']) and 
                (target_properties['type'] in ['panel', 'PLC'])):
            print(f"跳过非panel/PLC连接: {source_str} -> {target_str}")
            return False

        with self.driver.session() as session:
            query = """
            MERGE (source:Vertex {id: $source_id})
            SET source += $source_properties
            MERGE (target:Vertex {id: $target_id})
            SET target += $target_properties
            MERGE (source)-[c:conn]->(target)
            SET c = $wire_properties
            MERGE (target)-[c2:conn]->(source)
            SET c2 = $wire_properties
            """
            session.run(
                query,
                source_id=source_id,
                source_properties=source_properties,
                target_id=target_id,
                target_properties=target_properties,
                wire_properties=wire_properties
            )
            return True

    def import_data(self, csv_path):
        """导入CSV数据"""
        print(f"开始从 {csv_path} 导入数据...")
        count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            # 跳过头两行
            next(file)
            next(file)
            
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                source_str = row.get('source', '').strip()
                target_str = row.get('target', '').strip()
                
                if not source_str or not target_str:
                    continue

                wire_properties = {
                    'wire_number': row.get('Consecutive number', ''),
                    'cable_type': row.get('cableType/connections number/RCS', ''),
                    'color': row.get('Connection color / number', ''),
                    'length': row.get('Length (full)', ''),
                    'bundle': row.get('Bundle', ''),
                    'remark': row.get('Remark', '')
                }
                # 移除空值
                wire_properties = {k: v for k, v in wire_properties.items() if v}

                if self.create_connection(source_str, target_str, wire_properties):
                    count += 1
                    if count % 100 == 0:
                        print(f"已处理 {count} 条连接")

        print(f"数据导入完成，共处理 {count} 条连接")

def main():
    connector = GraphConnector()
    try:
        connector.import_data("data/SmartWiringzta.csv")
    except Exception as e:
        print(f"导入过程中出现错误: {str(e)}")
    finally:
        connector.close()

if __name__ == "__main__":
    main()