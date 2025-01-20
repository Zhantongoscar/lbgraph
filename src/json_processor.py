import json
from typing import Dict, List
import os

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

if __name__ == "__main__":
    # 获取用户输入
    while True:
        try:
            file_path = input("请输入JSON文件路径（默认：output/processed_data.json）：").strip()
            if not file_path:
                file_path = 'output/processed_data.json'
                
            processor = JsonProcessor(file_path)
            break
        except FileNotFoundError as e:
            print(f"错误：{e}")
            print("请检查文件路径是否正确")
        except json.JSONDecodeError:
            print("错误：文件格式不正确，请确保是有效的JSON文件")
    
    # 获取所有节点
    nodes = processor.get_nodes()
    print(f"总节点数: {len(nodes)}")
    
    # 获取所有边
    edges = processor.get_edges()
    print(f"总边数: {len(edges)}")
    
    # 示例：获取特定节点的信息
    if nodes:
        sample_node = nodes[0]
        print(f"\n示例节点信息:")
        print(f"ID: {sample_node['id']}")
        print(f"位置: {sample_node['properties']['location']}")
        
        # 获取与该节点相连的边
        connected_edges = processor.get_edges_by_node(sample_node['id'])
        print(f"连接边数: {len(connected_edges)}")