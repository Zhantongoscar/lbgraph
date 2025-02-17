"""
继电器类型系统 - 用于管理和分析继电器型号及其实例
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import csv
from collections import defaultdict

@dataclass
class RelayTerminalPattern:
    """继电器端子模式"""
    coil_terminals: List[str]  # 线圈端子列表 [A1, A2]
    power_terminals: List[Dict[str, str]]  # 主触头端子 [{input: L1, output: T1}, ...]
    auxiliary_terminals: List[Dict[str, str]]  # 辅助触点端子 [{com: "11", nc: "12", no: "14"}, ...]
    diagnostic_terminals: List[str]  # 诊断端子列表 [D1, D2]

@dataclass
class RelayTypeInfo:
    """继电器类型信息"""
    type_id: str  # 型号标识，如 "3RT1024"
    manufacturer: str  # 制造商
    category: str  # 类别（接触器、继电器等）
    coil_voltage: str  # 线圈电压
    terminal_pattern: RelayTerminalPattern  # 端子模式
    power_rating: Optional[str] = None  # 功率等级
    auxiliary_contact_count: int = 0  # 辅助触点数量

class RelayTypeAnalyzer:
    """继电器型号分析器"""
    def __init__(self):
        self.relay_types = {}  # 存储已知的继电器型号
        self.relay_instances = defaultdict(list)  # 存储每个型号的实例
        self.device_features = defaultdict(dict)  # 存储设备特征
        
    def analyze_csv(self, csv_path: str):
        """分析CSV文件中的继电器数据"""
        device_terminals = defaultdict(set)  # 收集每个设备的所有端子
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # 处理source端
                if row['source']:
                    device, terminal = self._parse_device_terminal(row['source'])
                    if device and terminal and (device.startswith('Q') or device.startswith('K')):
                        device_terminals[device].add(terminal)
                
                # 处理target端
                if row['target']:
                    device, terminal = self._parse_device_terminal(row['target'])
                    if device and terminal and (device.startswith('Q') or device.startswith('K')):
                        device_terminals[device].add(terminal)
        
        # 分析收集到的数据
        for device, terminals in device_terminals.items():
            relay_type = self._analyze_relay_type(device, terminals)
            if relay_type:
                self.relay_types[relay_type.type_id] = relay_type
                self.relay_instances[relay_type.type_id].append(device)

    def _parse_device_terminal(self, device_string: str) -> tuple:
        """解析设备字符串，返回(设备ID, 端子号)"""
        if ':' not in device_string:
            return None, None
        
        parts = device_string.split(':')
        if len(parts) != 2:
            return None, None
            
        device_part = parts[0]
        terminal = parts[1]
        
        # 提取设备ID
        if '-' in device_part:
            device = device_part.split('-')[-1]
        else:
            device = device_part
            
        return device.strip(), terminal.strip()

    def analyze_device_features(self, device: str, terminals: set):
        """分析设备特征
        Args:
            device: 设备ID
            terminals: 该设备的所有端子
        """
        features = {
            'terminal_count': len(terminals),
            'has_coil': any(t.startswith('A') for t in terminals),
            'contact_groups': self._analyze_contact_groups(terminals),
            'power_terminals': [t for t in terminals if t.startswith(('L', 'T'))],
            'diagnostic_terminals': [t for t in terminals if t.startswith('D')]
        }
        self.device_features[device] = features
        return features
    
    def _analyze_contact_groups(self, terminals: set) -> dict:
        """分析触点组配置"""
        contact_groups = defaultdict(dict)
        for term in terminals:
            if term.isdigit() and len(term) == 2:
                group = int(term[0])
                type_num = int(term[1])
                if type_num == 1:
                    contact_groups[group]['com'] = term
                elif type_num == 2:
                    contact_groups[group]['nc'] = term
                elif type_num == 4:
                    contact_groups[group]['no'] = term
        return dict(contact_groups)
    
    def find_similar_devices(self, device: str) -> list:
        """查找具有相似特征的设备
        Args:
            device: 设备ID
        Returns:
            list: 相似设备的ID列表
        """
        if device not in self.device_features:
            return []
            
        base_features = self.device_features[device]
        similar_devices = []
        
        for other_device, other_features in self.device_features.items():
            if other_device != device and self._compare_features(base_features, other_features):
                similar_devices.append(other_device)
                
        return similar_devices
    
    def _compare_features(self, features1: dict, features2: dict) -> bool:
        """比较两个设备的特征是否相似"""
        # 检查端子数量
        if features1['terminal_count'] != features2['terminal_count']:
            return False
            
        # 检查线圈存在性
        if features1['has_coil'] != features2['has_coil']:
            return False
            
        # 检查触点组结构
        if len(features1['contact_groups']) != len(features2['contact_groups']):
            return False
            
        # 比较每个触点组的配置
        for group_num in features1['contact_groups']:
            if group_num not in features2['contact_groups']:
                return False
            if features1['contact_groups'][group_num].keys() != features2['contact_groups'][group_num].keys():
                return False
                
        # 比较功率端子
        if len(features1['power_terminals']) != len(features2['power_terminals']):
            return False
            
        return True
    
    def _analyze_relay_type(self, device: str, terminals: set) -> Optional[RelayTypeInfo]:
        """分析继电器类型"""
        # 首先分析设备特征
        features = self.analyze_device_features(device, terminals)
        
        # 对终端进行分类
        coil_terms = []
        power_terms = []
        aux_terms = []
        diag_terms = []
        
        for term in terminals:
            if term.startswith('A'):
                coil_terms.append(term)
            elif term.startswith(('L', 'T')):
                power_terms.append(term)
            elif term.startswith('D'):
                diag_terms.append(term)
            elif term.isdigit():
                aux_terms.append(term)

        # 根据特征推断设备类型
        if device.startswith('S'):
            category = "Button"
            type_prefix = "S"
            if len(aux_terms) > 2:
                type_prefix = "S-MULTI"
        elif power_terms:  # 可能是接触器
            category = "Contactor"
            type_prefix = "3RT"
        elif not features['has_coil']:  # 无线圈的设备
            category = "Button"
            type_prefix = "S"
        elif len(aux_terms) >= 4:  # 多触点继电器
            category = "Relay"
            type_prefix = "RY"
        else:  # 基本继电器
            category = "Relay"
            type_prefix = "K"

        # 创建端子模式
        terminal_pattern = RelayTerminalPattern(
            coil_terminals=sorted(coil_terms),
            power_terminals=[{'input': f'L{i}', 'output': f'T{i}'} 
                           for i in range(1, (len(power_terms)//2) + 1)],
            auxiliary_terminals=self._group_auxiliary_contacts(aux_terms),
            diagnostic_terminals=sorted(diag_terms)
        )

        # 检查是否已存在相似的类型
        similar_devices = self.find_similar_devices(device)
        if similar_devices:
            existing_type = None
            for similar_device in similar_devices:
                for type_id, instances in self.relay_instances.items():
                    if similar_device in instances:
                        existing_type = self.relay_types[type_id]
                        break
            if existing_type:
                return existing_type

        # 创建新的继电器类型信息
        return RelayTypeInfo(
            type_id=f"{type_prefix}{len(self.relay_types) + 1}",
            manufacturer="Unknown",
            category=category,
            coil_voltage="24VDC" if category == "Relay" else "230VAC",
            terminal_pattern=terminal_pattern,
            power_rating="10A" if category == "Relay" else "30A",
            auxiliary_contact_count=len(aux_terms) // 3
        )

    def _group_auxiliary_contacts(self, terminals: List[str]) -> List[Dict[str, str]]:
        """将辅助触点端子分组"""
        groups = defaultdict(dict)
        for term in terminals:
            if len(term) == 2:
                group = int(term[0])
                type_num = int(term[1])
                if type_num == 1:
                    groups[group]['com'] = term
                elif type_num == 2:
                    groups[group]['nc'] = term
                elif type_num == 4:
                    groups[group]['no'] = term
        
        return [dict(groups[g]) for g in sorted(groups.keys())]

    def get_relay_type_config(self, type_id: str) -> dict:
        """获取继电器类型配置"""
        if type_id not in self.relay_types:
            return None
            
        relay_type = self.relay_types[type_id]
        return {
            "type": relay_type.category,
            "coil_voltage": relay_type.coil_voltage,
            "power_poles": {
                "type": "3-PHASE" if len(relay_type.terminal_pattern.power_terminals) == 3 else "1-PHASE",
                "count": len(relay_type.terminal_pattern.power_terminals),
                "rating": relay_type.power_rating,
                "terminals": relay_type.terminal_pattern.power_terminals
            } if relay_type.terminal_pattern.power_terminals else None,
            "auxiliary_contacts": [{
                "type": "CO",
                "count": relay_type.auxiliary_contact_count,
                "rating": "6A"
            }] if relay_type.auxiliary_contact_count > 0 else []
        }

    def get_instances_of_type(self, type_id: str) -> List[str]:
        """获取指定型号的所有实例"""
        return self.relay_instances.get(type_id, [])

if __name__ == "__main__":
    # Create an instance of RelayTypeAnalyzer
    analyzer = RelayTypeAnalyzer()
    
    # Try to analyze the CSV file from the data directory
    try:
        csv_path = "data/SmartWiringzta.csv"
        print(f"Analyzing CSV file: {csv_path}")
        analyzer.analyze_csv(csv_path)
        
        # Print discovered relay types
        print("\nDiscovered Relay Types:")
        for type_id, relay_type in analyzer.relay_types.items():
            print(f"\nType ID: {type_id}")
            print(f"Category: {relay_type.category}")
            print(f"Manufacturer: {relay_type.manufacturer}")
            print(f"Coil Voltage: {relay_type.coil_voltage}")
            print(f"Power Rating: {relay_type.power_rating}")
            print(f"Auxiliary Contact Count: {relay_type.auxiliary_contact_count}")
            
            # Print instances of this type
            instances = analyzer.get_instances_of_type(type_id)
            print(f"Instances: {', '.join(instances)}")
            
    except FileNotFoundError:
        print("Error: Could not find the CSV file. Please ensure the data file exists in the correct location.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")