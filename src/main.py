import json
from typing import Dict, List
import os
import time
from data_preprocessor import DataPreprocessor
from test_device_processor import TestDeviceProcessor
import networkx as nx
from collections import defaultdict

class JsonProcessor:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.graph_data = self.load_json()

    def load_json(self) -> Dict:
        """加载JSON文件"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

        with open(self.file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_nodes(self) -> List[Dict]:
        """获取所有节点"""
        return self.graph_data.get('nodes', [])

    def get_edges(self) -> List[Dict]:
        """获取所有边"""
        return self.graph_data.get('edges', [])

    def get_node_by_id(self, node_id: str) -> Dict:
        """根据ID获取节点"""
        return next((n for n in self.graph_data['nodes'] if n['id'] == node_id), None)

    def get_edges_by_node(self, node_id: str) -> List[Dict]:
        """获取与指定节点相连的所有边"""
        return [e for e in self.graph_data['edges'] 
                if e['source'] == node_id or e['target'] == node_id]

    def save_processed_data(self, output_path: str, data: Dict):
        """保存处理后的数据"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

class GraphAnalyzer:
    def __init__(self, processors: List[JsonProcessor]):
        self.processors = processors
        self.graph = nx.Graph()
        self.build_graph()

    def build_graph(self):
        """构建图"""
        for processor in self.processors:
            nodes = processor.get_nodes()
            edges = processor.get_edges()
            
            for node in nodes:
                self.graph.add_node(node['id'], **node)
            
            for edge in edges:
                self.graph.add_edge(edge['source'], edge['target'], **edge['properties'])

    def get_shortest_path(self, source: str, target: str) -> List[str]:
        """获取最短路径"""
        try:
            return nx.shortest_path(self.graph, source=source, target=target)
        except nx.NetworkXNoPath:
            return []

    def get_connected_components(self) -> List[List[str]]:
        """获取连通组件"""
        return list(nx.connected_components(self.graph))

    def get_node_degree(self, node_id: str) -> int:
        """获取节点的度"""
        return self.graph.degree(node_id)

    def get_graph_density(self) -> float:
        """获取图的密度"""
        return nx.density(self.graph)

    def get_betweenness_centrality(self) -> Dict[str, float]:
        """获取节点的介数中心性"""
        return nx.betweenness_centrality(self.graph)

def process_excel_data():
    """处理Excel数据"""
    preprocessor = DataPreprocessor()
    preprocessor.load_config()
    
    try:
        file_path = preprocessor.get_file_path()
        preprocessor.load_data(file_path)
        
        print("\n数据加载成功")
        columns = preprocessor.show_columns()
        
        selected_columns = preprocessor.select_columns()
        print("\n选择的列:")
        for col_type, col_name in selected_columns.items():
            print(f"{col_type}: {col_name}")
            
        graph_data = preprocessor.to_graph_data(selected_columns)
        cleaned_data = preprocessor.clean_data(graph_data)
        
        return cleaned_data
        
    except Exception as e:
        print(f"错误: {e}")
        return None

def process_device_data():
    """处理设备数据"""
    processor = TestDeviceProcessor()
    max_idle_minutes = 5  # 最大空闲时间（分钟）
    last_activity_time = time.time()
    
    while True:
        try:
            choice = processor.display_menu()
            
            if choice == '1':
                processor.add_device_interactive(processor)
                last_activity_time = time.time()
            elif choice == '2':
                processor.list_devices(processor)
                last_activity_time = time.time()
            elif choice == '3':
                file_name = input("请输入保存文件名（不带扩展名）：").strip()
                if file_name:
                    processor.save_to_json(f'output/{file_name}.json')
                    print(f"配置已保存到 output/{file_name}.json")
                    last_activity_time = time.time()
                else:
                    print("文件名不能为空")
            elif choice == '4':
                print("退出系统")
                break
            else:
                print("无效的选择，请重试")
                
            # 检查空闲时间
            if time.time() - last_activity_time > max_idle_minutes * 60:
                print(f"\n警告：系统已空闲超过{max_idle_minutes}分钟，自动退出...")
                break
                
        except KeyboardInterrupt:
            print("\n检测到中断信号，退出系统...")
            break
        except Exception as e:
            print(f"发生错误：{str(e)}")
            print("返回主菜单...")

def graph_test():
    """图论测试"""
    print("\n==== 图论测试 ====")
    
    # 获取第一个JSON文件
    while True:
        try:
            file1 = input("请输入第一个JSON文件路径（默认：output/processed_data.json）：").strip()
            if not file1:
                file1 = 'output/processed_data.json'
                
            processor1 = JsonProcessor(file1)
            break
        except FileNotFoundError as e:
            print(f"错误：{e}")
            print("请检查文件路径是否正确")
        except json.JSONDecodeError:
            print("错误：文件格式不正确，请确保是有效的JSON文件")
    
    # 获取第二个JSON文件
    while True:
        try:
            file2 = input("请输入第二个JSON文件路径（默认：output/test_devices.json）：").strip()
            if not file2:
                file2 = 'output/test_devices.json'
                
            processor2 = JsonProcessor(file2)
            break
        except FileNotFoundError as e:
            print(f"错误：{e}")
            print("请检查文件路径是否正确")
        except json.JSONDecodeError:
            print("错误：文件格式不正确，请确保是有效的JSON文件")
    
    # 创建图分析器
    analyzer = GraphAnalyzer([processor1, processor2])
    
    # 执行图论测试
    print("\n开始图论测试...")
    
    # 获取所有节点
    nodes1 = processor1.get_nodes()
    nodes2 = processor2.get_nodes()
    
    # 获取所有边
    edges1 = processor1.get_edges()
    edges2 = processor2.get_edges()
    
    # 显示统计信息
    print(f"\n文件1统计：")
    print(f"- 节点数: {len(nodes1)}")
    print(f"- 边数: {len(edges1)}")
    
    print(f"\n文件2统计：")
    print(f"- 节点数: {len(nodes2)}")
    print(f"- 边数: {len(edges2)}")
    
    # 示例：比较两个图的连通性
    print("\n比较两个图的连通性...")
    connected_nodes1 = set()
    connected_nodes2 = set()
    
    for edge in edges1:
        connected_nodes1.add(edge['source'])
        connected_nodes1.add(edge['target'])
        
    for edge in edges2:
        connected_nodes2.add(edge['source'])
        connected_nodes2.add(edge['target'])
        
    print(f"文件1连通节点数: {len(connected_nodes1)}/{len(nodes1)}")
    print(f"文件2连通节点数: {len(connected_nodes2)}/{len(nodes2)}")
    
    # 查找共同节点
    common_nodes = set(n['id'] for n in nodes1).intersection(set(n['id'] for n in nodes2))
    print(f"\n共同节点数: {len(common_nodes)}")
    
    # 查找共同边
    edge_set1 = set((e['source'], e['target']) for e in edges1)
    edge_set2 = set((e['source'], e['target']) for e in edges2)
    common_edges = edge_set1.intersection(edge_set2)
    print(f"共同边数: {len(common_edges)}")
    
    # 显示图论测试结果
    print("\n图论测试结果：")
    print("1. 统计了两个图的节点和边数量")
    print("2. 比较了两个图的连通性")
    print("3. 找出了两个图的共同节点")
    print("4. 找出了两个图的共同边")
    
    # 示例：获取最短路径
    if common_nodes:
        source = list(common_nodes)[0]
        target = list(common_nodes)[-1]
        shortest_path = analyzer.get_shortest_path(source, target)
        print(f"\n最短路径示例（{source} -> {target}）：")
        print(shortest_path)
    
    # 示例：获取连通组件
    connected_components = analyzer.get_connected_components()
    print(f"\n连通组件数: {len(connected_components)}")
    print(f"最大连通组件大小: {max(len(c) for c in connected_components)}")
    
    # 示例：获取图的密度
    density = analyzer.get_graph_density()
    print(f"\n图的密度: {density:.4f}")
    
    # 示例：获取介数中心性
    betweenness = analyzer.get_betweenness_centrality()
    print("\n介数中心性最高的5个节点：")
    for node, centrality in sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{node}: {centrality:.4f}")

def main_menu():
    """主菜单"""
    print("==== 主菜单 ====")
    print("1. 处理Excel数据")
    print("2. 处理设备数据")
    print("3. 图论测试")
    print("4. 退出")
    
    while True:
        choice = input("请选择操作（1-4）：").strip()
        
        if choice == '1':
            process_excel_data()
        elif choice == '2':
            process_device_data()
        elif choice == '3':
            graph_test()
        elif choice == '4':
            print("退出程序")
            break
        else:
            print("无效的选择，请重试")

if __name__ == "__main__":
    # 启动GUI界面
    from gui import MainWindow
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())