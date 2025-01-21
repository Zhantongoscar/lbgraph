import configparser
import os
import pandas as pd
from typing import Dict, List, Optional

class DataPreprocessor:
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
            
    def get_file_path(self) -> str:
        """获取文件路径"""
        if not self.config.has_section('USER'):
            return self.prompt_for_file_path()
            
        return self.config['USER'].get('last_used_file', 
            os.path.join(
                self.config['DEFAULT']['data_folder'],
                self.config['DEFAULT']['default_file']
            )
        )
        
    def prompt_for_file_path(self) -> str:
        """提示用户输入文件路径"""
        default_path = os.path.join(
            self.config['DEFAULT']['data_folder'],
            self.config['DEFAULT']['default_file']
        )
        
        # 格式化输出
        print(f"{'默认文件路径:':<15} {default_path}")
        choice = input(f"{'使用默认路径？(y/n):':<15} ").strip().lower()
        
        if choice == 'y':
            return default_path
            
        while True:
            # 限制输入长度并格式化提示
            file_path = input(f"{'请输入文件路径:':<15} ").strip()[:100]  # 限制100字符
            if os.path.exists(file_path):
                # 保存用户选择
                if not self.config.has_section('USER'):
                    self.config.add_section('USER')
                self.config['USER']['last_used_file'] = file_path
                with open('config.ini', 'w') as configfile:
                    self.config.write(configfile)
                return file_path
            print(f"{'错误:':<15} 文件不存在，请重新输入")
            
    def load_data(self, file_path: str):
        """加载Excel数据"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        # 询问转换数量
        while True:
            try:
                count = input("请输入要转换的数量（输入'all'转换全部）：").strip().lower()
                if count == 'all':
                    self.df = pd.read_excel(file_path, dtype=str)
                    break
                else:
                    count = int(count)
                    if count > 0:
                        self.df = pd.read_excel(file_path, dtype=str, nrows=count)
                        break
                    print("请输入大于0的数字或'all'")
            except ValueError:
                print("请输入有效的数字或'all'")
        
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
        
    def show_columns(self) -> List[str]:
        """显示可用列"""
        if self.df is None:
            raise ValueError("请先加载数据")
            
        print("可用列:")
        columns = list(self.df.columns)
        max_len = 20  # 每行显示3个，适当减少单个列名长度
        
        for i in range(0, len(columns), 3):
            row = columns[i:i+3]
            # 处理列名显示，移除换行符
            cols = [col.replace('\n', ' ').replace('\r', '') for col in row]
            # 截断过长列名
            cols = [col if len(col) <= max_len else col[:max_len-3] + '...' for col in cols]
            
            # 格式化输出，确保对齐
            if len(cols) == 3:
                print(f"{i+1:>2}. {cols[0]:<{max_len}}  {i+2:>2}. {cols[1]:<{max_len}}  {i+3:>2}. {cols[2]}")
            elif len(cols) == 2:
                print(f"{i+1:>2}. {cols[0]:<{max_len}}  {i+2:>2}. {cols[1]}")
            else:
                print(f"{i+1:>2}. {cols[0]}")
                
        return list(self.df.columns)
        
    def select_columns(self) -> Dict[str, str]:
        """选择需要的列"""
        required_columns = {
            'serial': 'Consecutive number',
            'color': 'Connection color / number',
            'source': 'Device (source)',
            'target': 'Device (target)'
        }
        
        selected = {}
        for col_type, col_name in required_columns.items():
            print(f"\n请选择 {col_name} 列:")
            self.show_columns()
            
            # 根据列名猜测可能的列
            suggestions = []
            for i, col in enumerate(self.df.columns, 1):
                if col_name.lower() in col.lower():
                    suggestions.append(i)
                    
            if suggestions:
                print(f"建议选择: {', '.join(map(str, suggestions))}")
                
            while True:
                try:
                    choice = int(input("请输入列编号: "))
                    if 1 <= choice <= len(self.df.columns):
                        selected[col_type] = self.df.columns[choice-1]
                        break
                    print("无效的选择，请重试")
                except ValueError:
                    print("请输入有效的数字")
                    
        return selected
        
    def parse_iec_identifier(self, identifier: str) -> Dict[str, str]:
        """解析IEC 60204标识符"""
        import re
        print(f"\n解析标识符: {identifier}")  # 调试信息
        
        pattern = r'=(?P<function>[^+]*)\+(?P<location>[^-]*)-(?P<device>[^:]*):(?P<terminal>.*)'
        match = re.match(pattern, identifier)
        
        if not match:
            # 如果不符合标准格式，尝试解析location
            print("不符合标准格式，尝试提取location")  # 调试信息
            location_match = re.search(r'K1\.\d{2}', identifier)
            result = {
                'function': '',
                'location': location_match.group(0) if location_match else '',
                'device': '',
                'terminal': ''
            }
            print(f"解析结果: {result}")  # 调试信息
            return result
            
        result = match.groupdict()
        print(f"标准格式解析结果: {result}")  # 调试信息
        return result

    def to_graph_data(self, selected_columns: Dict[str, str]):
        """转换为图论数据结构"""
        if self.df is None:
            raise ValueError("请先加载数据")
            
        graph_data = {
            'nodes': [],
            'edges': [],
            'metadata': {
                'created_at': pd.Timestamp.now().isoformat(),
                'version': '1.0'
            }
        }
        
        try:
            # 创建节点集合
            nodes = set()
            for _, row in self.df.iterrows():
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
                
        except KeyError as e:
            raise ValueError(f"选择的列不存在: {e}")
        except Exception as e:
            raise ValueError(f"数据转换错误: {e}")
            
        return graph_data
        
    def clean_data(self, graph_data: Dict):
        """清洗数据"""
        import re
        import json
        
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
        
        # 显示筛选结果
        print(f"\n筛选后的连接（共{len(valid_edges)}条）:")
        print(f"{'序列号':<10} {'源':<20} {'目标':<20} {'颜色':<10}")
        for edge in valid_edges:  # 显示所有结果
            print(f"{edge['properties']['serial_number']:<10} {edge['source']:<20} {edge['target']:<20} {edge['properties']['color']:<10}")
            
        # 保存清洗后的数据
        while True:
            try:
                filename = input("\n请输入保存文件名（不带扩展名）：").strip()
                if not filename:
                    raise ValueError("文件名不能为空")
                    
                save_path = f"output/{filename}.json"
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(graph_data, f, ensure_ascii=False, indent=2)
                    
                print(f"\n数据已成功保存到：{save_path}")
                break
                
            except Exception as e:
                print(f"保存失败：{e}，请重试")
            
        return graph_data
        
    def show_results(self, graph_data: Dict):
        """展示结果"""
        # 实现结果展示逻辑
        # ...

if __name__ == "__main__":
    processor = DataPreprocessor()
    processor.load_config()
    
    try:
        file_path = processor.get_file_path()
        processor.load_data(file_path)
        
        print("\n数据加载成功")
        columns = processor.show_columns()
        
        selected_columns = processor.select_columns()
        print("\n选择的列:")
        for col_type, col_name in selected_columns.items():
            print(f"{col_type}: {col_name}")
            
        graph_data = processor.to_graph_data(selected_columns)
        cleaned_data = processor.clean_data(graph_data)
        processor.show_results(cleaned_data)
        
    except Exception as e:
        print(f"错误: {e}")