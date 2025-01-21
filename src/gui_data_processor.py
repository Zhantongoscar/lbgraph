import configparser
import os
import json
import pandas as pd
from typing import Dict, List, Optional
from PyQt5.QtWidgets import QMessageBox

class GuiDataProcessor:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.df = None
        
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists('config.ini'):
            self.create_default_config()
            
        self.config.read('config.ini')
        
    def create_default_config(self):
        """创建默认配置文件"""
        self.config['DEFAULT'] = {
            'data_folder': './data',
            'default_file': 'data.xlsx'
        }
        
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
            
    def load_data(self, file_path: str, parent_widget=None) -> bool:
        """加载Excel数据
        
        Args:
            file_path: Excel文件路径
            parent_widget: 父窗口部件，用于显示对话框
            
        Returns:
            bool: 是否成功加载数据
        """
        if not os.path.exists(file_path):
            if parent_widget:
                QMessageBox.critical(parent_widget, "错误", f"文件不存在: {file_path}")
            return False
            
        try:
            # 直接加载所有数据
            self.df = pd.read_excel(file_path, dtype=str)
            
            # 定义需要处理的列
            required_columns = ['Consecutive number',
                              'Connection color / number',
                              'Device (source)',
                              'Device (target)']
            
            # 转换列类型并处理特殊字符
            for col in required_columns:
                if col in self.df.columns:
                    # 先转换为字符串
                    self.df[col] = self.df[col].astype(str)
                    # 处理特殊字符
                    self.df[col] = self.df[col].str.replace(r'[^\x00-\x7F]+', '', regex=True)
                    # 去除前后空白
                    self.df[col] = self.df[col].str.strip()
                    # 处理空值
                    self.df[col] = self.df[col].fillna('')
                    
            return True
            
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(parent_widget, "错误", f"加载数据失败: {str(e)}")
            return False
            
    def get_columns(self) -> List[str]:
        """获取所有列名"""
        if self.df is None:
            return []
        return list(self.df.columns)
    def process_data(self, selected_columns: Dict[str, str], parent_widget=None, row_limit: int = None) -> Optional[Dict]:
        """处理数据并生成图论数据结构
        
        Args:
            selected_columns: 选择的列映射
            parent_widget: 父窗口部件
            row_limit: 要处理的最大行数，None表示处理所有行
            
        Returns:
            Optional[Dict]: 处理后的图论数据，失败返回None
        """
        if self.df is None:
            if parent_widget:
                QMessageBox.warning(parent_widget, "警告", "请先加载数据")
            return None
            
        try:
            graph_data = {
                'nodes': [],
                'edges': [],
                'metadata': {
                    'created_at': pd.Timestamp.now().isoformat(),
                    'version': '1.0'
                }
            }
            
            # 创建节点集合
            nodes = set()
            # 应用行数限制
            limited_df = self.df.head(row_limit) if row_limit else self.df
            
            for _, row in limited_df.iterrows():
                source = str(row[selected_columns['source']])
                target = str(row[selected_columns['target']])
                nodes.add(source)
                nodes.add(target)
                
            # 添加节点
            for node in nodes:
                node_info = self.parse_iec_identifier(str(node))
                graph_data['nodes'].append({
                    'id': node,
                    'iec_identifier': node,
                    'properties': node_info
                })
                
            # 添加边
            for _, row in self.df.iterrows():
                source = str(row[selected_columns['source']])
                target = str(row[selected_columns['target']])
                color = str(row[selected_columns['color']])
                serial = str(row[selected_columns['serial']])
                
                graph_data['edges'].append({
                    'source': source,
                    'target': target,
                    'properties': {
                        'color': color,
                        'serial_number': serial
                    }
                })
                
            return self.clean_data(graph_data)
            
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(parent_widget, "错误", f"处理数据失败: {str(e)}")
            return None
            
    def parse_iec_identifier(self, identifier: str) -> Dict[str, str]:
        """解析IEC 60204标识符"""
        import re
        
        pattern = r'^=(?P<function>[^+]+)\+(?P<location>[^-]+)-(?P<device>[^:]+):(?P<terminal>.+)$'
        match = re.match(pattern, identifier)
        
        if not match:
            # 如果不符合标准格式，尝试解析location
            location_match = re.search(r'K1\.\d{1,3}(?:\.\d{1,3}){0,2}', identifier)  # 匹配K1开头，支持1-3位数字和最多三级编号
            return {
                'function': '',
                'location': location_match.group(0) if location_match else '',
                'device': '',
                'terminal': ''
            }
            
        return match.groupdict()
        
    def clean_data(self, graph_data: Dict) -> Dict:
        """清洗数据"""
        import re
        
        # 筛选有效连接
        valid_edges = []
        for edge in graph_data['edges']:
            source_node = next((n for n in graph_data['nodes'] if n['id'] == edge['source']), None)
            target_node = next((n for n in graph_data['nodes'] if n['id'] == edge['target']), None)
            
            # 检查location是否符合K1.格式
            source_valid = source_node and re.match(r'K1\..*', source_node['properties']['location'])
            target_valid = target_node and re.match(r'K1\..*', target_node['properties']['location'])
            
            if source_valid and target_valid:
                valid_edges.append(edge)
                
        # 更新图数据
        graph_data['edges'] = valid_edges
        
        return graph_data
        
    def save_data(self, graph_data: Dict, file_path: str, parent_widget=None) -> bool:
        """保存数据到JSON文件
        
        Args:
            graph_data: 图论数据
            file_path: 保存路径
            parent_widget: 父窗口部件
            
        Returns:
            bool: 是否成功保存
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            return True
            
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(parent_widget, "错误", f"保存数据失败: {str(e)}")
            return False