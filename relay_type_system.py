"""
继电器类型系统 - 用于管理和分析继电器型号及其实例
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import csv
import re
from collections import defaultdict

@dataclass
class RelayTerminalPattern:
    """继电器端子模式"""
    coil_terminals: List[str]  # 线圈端子列表 [A1, A2]
    power_terminals: List[Dict[str, str]]  # 主触头端子 [{input: L1, output: T1}, ...]
    auxiliary_terminals: List[Dict[str, str]]  # 辅助触点端子 [{com: "11", nc: "12", no: "14"}, ...]
    diagnostic_terminals: List[str]  # 诊断端子列表 [D1, D2]
    terminal_connections: List[Dict[str, any]]  # 端子间连接特征 [{source: "A1", target: "L1", type: "control"}, ...]

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
    def __init__(self):
        self.device_paths = {}  # 存储设备完整路径 {device_id: full_path}
        self.device_terminals = defaultdict(set)  # 存储设备端子 {device_id: {terminals}}
        self.device_features = {}  # 存储设备特征
        self.relay_types = {}  # 存储继电器类型
        self.type_instances = defaultdict(list)  # 存储类型实例
        self.terminal_connections = defaultdict(dict)  # 存储端子连接关系
        self.connection_types = {}  # 存储设备连接类型 {device_id: 'ctrl'/'direct'}
        self.device_pattern = re.compile(r"-[KDSQ]\d+$")  # 匹配 -K* -D* -S* -Q* 结尾的设备

    def is_valid_device(self, device_id: str) -> bool:
        """验证设备是否符合后缀规则"""
        # 匹配包含 -K* -D* -S* -Q* 结尾的设备
        # 示例有效设备：
        # =A01+K1.H2-K1
        # =B02+Q3-D2
        # =C03+S4-K5
        return bool(self.device_pattern.search(device_id))

    def analyze_csv(self, csv_path: str):
        """分析CSV文件中的继电器数据"""
        print("步骤1: 收集设备标识符...")
        self._collect_device_paths(csv_path)
        
        print("\n步骤2: 收集设备端子...")
        self._collect_device_terminals(csv_path)
        
        print("\n步骤3: 分析设备特征...")
        self._analyze_device_features()
        
        print("\n步骤4: 识别继电器类型...")
        self._identify_relay_types()

        # Print results
        print("\n分析结果:")
        if not self.device_paths:
            print("未找到任何设备!")
            return
            
        print(f"\n找到 {len(self.device_paths)} 个设备:")
        for device_id, path in self.device_paths.items():
            print(f"\n设备 {device_id}:")
            print(f"  路径: {path}")
            if device_id in self.device_terminals:
                print(f"  端子: {sorted(list(self.device_terminals[device_id]))}")

        print("\n继电器类型分析:")
        for type_id, relay_type in self.relay_types.items():
            print(f"\n类型 {type_id}:")
            print("  基础特征配置:")
            features = relay_type['features']
            print(f"    线圈端子: {features['coil_terminals']}")
            print(f"    主触点: {features['power_terminals']}")
            print(f"    辅助触点组: {features['auxiliary_groups']}")
            print(f"    诊断端子: {features['diagnostic_terminals']}")
            
            print("  端子间连接模式:")
            for source, target, conn_type in relay_type['connection_patterns']:
                print(f"    {source} -> {target} (类型: {conn_type})")
            
            print("  实例:")
            for device_id in self.type_instances[type_id]:
                print(f"    - {device_id} ({self.device_paths[device_id]})")

    def _is_valid_k_device(self, device_path: str) -> tuple[bool, str]:
        """
        检查是否是有效的K设备，并返回K编号
        返回: (是否有效, K编号)
        """
        if not device_path or '+K' not in device_path:
            return False, ''
            
        k_index = device_path.find('+K')
        if k_index == -1:
            return False, ''
            
        remaining = device_path[k_index+2:]
        k_part = remaining.split('.')[0].split('-')[0]
        
        if k_part.isdigit():
            return True, f"K{k_part}"
        return False, ''

    def _extract_device_info(self, device_str: str) -> tuple[str, str, str, str]:
        """
        从设备字符串中提取设备信息
        返回: (设备路径, K设备标识, 端子标识, 连接类型)
        """
        device_path, terminal, conn_type = self._parse_device_string(device_str)
        if not device_path:
            return None, None, None, None
            
        is_valid, k_id = self._is_valid_k_device(device_path)
        if not is_valid:
            return None, None, None, None
            
        return device_path, k_id, terminal, conn_type

    def _normalize_terminal_id(self, terminal: str) -> str:
        """
        规范化端子标识符
        例如:
        - X1:9 -> X1:9
        - 9 -> 9
        - 2.1 -> 2:1
        - X1.1 -> X1:1
        - SEC:31 -> SEC:31
        - PE:1 -> PE:1
        """
        if not terminal:
            return None
            
        # 去除空白字符
        terminal = terminal.strip()
        
        # 处理特殊端子标识符
        special_prefixes = ['SEC', 'PRI', 'PE', 'N', 'L']
        
        # 检查是否是特殊端子格式
        for prefix in special_prefixes:
            if terminal.startswith(prefix + ':') or terminal.startswith(prefix + '.'):
                return terminal.replace('.', ':')
        
        # 如果端子包含字母和数字（如 X1:9），保持原样但统一使用冒号
        if any(c.isalpha() for c in terminal) and any(c.isdigit() for c in terminal):
            return terminal.replace('.', ':')
            
        # 对于纯数字的情况（如 2.1），转换为冒号格式
        if all(c.isdigit() or c in '.' for c in terminal):
            return terminal.replace('.', ':')
            
        return terminal

    def _is_special_terminal(self, terminal: str) -> bool:
        """
        检查是否是特殊端子（如电源、通信等端子）
        """
        if not terminal:
            return False
            
        special_patterns = [
            'SEC:', 'PRI:', 'PE:', 'N:', 'L:',  # 电源相关
            'USB', 'RS485', 'COM',               # 通信相关
            'IN:', 'OUT:', 'IO:',                # 输入输出
            'A1', 'A2',                          # 线圈端子
            'NC:', 'NO:', 'COM:'                 # 触点端子
        ]
        
        return any(pattern in terminal for pattern in special_patterns)

    def _determine_connection_type(self, device_path: str) -> str:
        """
        确定设备的连接类型
        - ctrl: 如果设备路径中包含-K*、-Q*或-S*组件
        - direct: 其他设备
        例如:
        A01+K1.H2-K1      -> ctrl （包含-K1）
        A01+K1.B1-W5(-P1) -> direct （没有-K*/-Q*/-S*）
        """
        if not device_path:
            return 'direct'
            
        parts = device_path.split('-')
        for part in parts[1:]:  # 跳过第一个部分（因为它通常是区域标识）
            # 去除可能的括号内容
            clean_part = part.split('(')[0]
            if ((clean_part.startswith('K') or
                 clean_part.startswith('Q') or
                 clean_part.startswith('S')) and
                any(c.isdigit() for c in clean_part)):
                return 'ctrl'
        return 'direct'

    def _parse_device_string(self, device_str: str):
        """解析设备字符串，返回设备路径、端子和连接类型。
        格式示例:
        - =V01+K1.B1-V2:2.1                   -> (V01+K1.B1-V2, 2.1, direct)
        - =V01+K1.B1-K2:A1                    -> (V01+K1.B1-K2, A1, ctrl)
        - =A02+K1.B1-Q1:13                    -> (A02+K1.B1-Q1, 13, ctrl)
        - =V01+K1.B1-S1:1                     -> (V01+K1.B1-S1, 1, ctrl)
        """
        if not device_str or not isinstance(device_str, str):
            return None, None, None
            
        # 保持原始字符串，不去除等号
        orig_str = device_str
        
        # 首先找到 +K 的位置
        k_index = orig_str.find('+K')
        if k_index == -1:
            return None, None, None
            
        # 从 +K 开始向后查找，直到找到第一个冒号或字符串结束
        colon_index = -1
        paren_count = 0  # 用于跟踪括号配对
        for i in range(k_index, len(orig_str)):
            if orig_str[i] == '(':
                paren_count += 1
            elif orig_str[i] == ')':
                paren_count -= 1
            elif orig_str[i] == ':' and paren_count == 0:
                colon_index = i
                break
        
        # 如果没有找到冒号，说明整个字符串都是设备路径
        if colon_index == -1:
            # 移除开头的等号用于内部存储，但在 device_paths 中会保留原始格式
            device_path = orig_str[1:].strip() if orig_str.startswith('=') else orig_str.strip()
            return device_path, None, self._determine_connection_type(device_path)
            
        # 分离设备路径和端子部分
        # 移除开头的等号用于内部存储，但在 device_paths 中会保留原始格式
        device_path = (orig_str[1:colon_index] if orig_str.startswith('=') else orig_str[:colon_index]).strip()
        terminal_part = orig_str[colon_index + 1:].strip()
        
        # 规范化端子标识
        terminal = self._normalize_terminal_id(terminal_part)
        
        # 确定连接类型
        conn_type = self._determine_connection_type(device_path)
        
        return device_path, terminal, conn_type

    def _extract_terminal_info(self, terminal: str) -> dict:
        """
        解析端子的详细信息
        返回: {
            'type': 'power/coil/aux/diag',  # 端子类型
            'number': str,                   # 端子编号
            'group': str,                    # 端子组（如果有）
            'function': str                  # 端子功能（如 NC/NO/COM）
        }
        """
        if not terminal:
            return None
            
        result = {
            'type': None,
            'number': None,
            'group': None,
            'function': None
        }
        
        # 检查特殊端子
        if self._is_special_terminal(terminal):
            if terminal.startswith(('PE:', 'N:', 'L:')):
                result['type'] = 'power'
                result['function'] = terminal.split(':')[0]
                if ':' in terminal:
                    result['number'] = terminal.split(':')[1]
            elif terminal in ('A1', 'A2'):
                result['type'] = 'coil'
                result['number'] = terminal
            return result
            
        # 处理常规端子
        parts = terminal.split(':')
        if len(parts) == 2:
            # 例如 X1:9
            prefix = parts[0]
            if prefix.startswith('X'):
                result['type'] = 'aux'
                result['group'] = prefix
                result['number'] = parts[1]
            else:
                try:
                    # 如果是纯数字，可能是简化的辅助触点表示
                    num = int(parts[1])
                    result['type'] = 'aux'
                    result['number'] = str(num)
                except ValueError:
                    pass
                    
        return result

    def _format_device_info(self, device_str: str) -> str:
        """格式化设备信息输出"""
        device_path, k_id, terminal, conn_type = self._extract_device_info(device_str)
        
        result = [
            f"原始字符串: {device_str}",
            f"设备路径: {device_path if device_path else '<无效>'}"
        ]
        
        if k_id:
            result.append(f"K设备编号: {k_id}")
        
        if terminal:
            result.append(f"规范化端子: {terminal}")
        else:
            result.append("端子标识: <无端子>")
            
        if conn_type:
            result.append(f"连接类型: {conn_type}")
            
        return "\n  ".join(result)

    def _collect_device_paths(self, csv_path: str):
        """步骤1: 收集所有设备路径，只处理包含 +K 的设备"""
        print(f"\n开始读取CSV文件: {csv_path}")
        device_count = 0
        
        # 增加一个字典来存储设备的完整连接信息
        self.device_connections = defaultdict(list)
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                source = row.get('source', '').strip()
                target = row.get('target', '').strip()
                connection_number = row.get('cable Type/connections number/RCS', '').strip()
                
                # 处理源端
                if source:
                    source_device, source_terminal, conn_type = self._parse_device_string(source)
                    if source_device and '+K' in source_device:
                        is_valid, k_id = self._is_valid_k_device(source_device)
                        if is_valid:
                            # 存储设备路径、连接类型和原始连接信息
                            orig_device = source.split(':')[0] if ':' in source else source
                            self.device_paths[source_device] = orig_device
                            self.connection_types[source_device] = conn_type
                            self.device_connections[source_device].append({
                                'original_string': source,
                                'connection_number': connection_number,
                                'terminal': source_terminal,
                                'target': target
                            })
                            device_count += 1
                
                # 处理目标端
                if target:
                    target_device, target_terminal, conn_type = self._parse_device_string(target)
                    if target_device and '+K' in target_device:
                        is_valid, k_id = self._is_valid_k_device(target_device)
                        if is_valid:
                            # 存储设备路径、连接类型和原始连接信息
                            orig_device = target.split(':')[0] if ':' in target else target
                            self.device_paths[target_device] = orig_device
                            self.connection_types[target_device] = conn_type
                            self.device_connections[target_device].append({
                                'original_string': target,
                                'connection_number': connection_number,
                                'terminal': target_terminal,
                                'source': source
                            })
                            device_count += 1
        
        ctrl_count = sum(1 for conn_type in self.connection_types.values() if conn_type == 'ctrl')
        print(f"\n总共找到 {device_count} 个设备，其中 {ctrl_count} 个控制连接设备")
        print("\n控制连接设备列表:")
        # 收集每个设备的所有端子
        device_terminals = defaultdict(set)
        for device, connections in self.device_connections.items():
            for conn in connections:
                if conn['terminal']:
                    device_terminals[device].add(conn['terminal'])

        # 仅显示控制连接设备
        for device in sorted(self.device_paths.keys()):
            if self.connection_types.get(device) == 'ctrl':
                terminals = device_terminals[device]
                if terminals:
                    print(f"设备: {self.device_paths[device]}")
                    print(f"  连接类型: 控制连接")
                    print(f"  端子列表: {sorted(list(terminals))}")
                    print("  --------")
        
        input("\n设备路径收集完成，按回车键继续...")

    def _collect_device_terminals(self, csv_path: str):
        """步骤2: 收集每个设备的所有端子"""
        terminal_count = 0
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                source = row.get('source', '').strip()
                target = row.get('target', '').strip()
                connection_number = row.get('cable Type/connections number/RCS', '').strip()
                
                print("\n" + "="*80)
                print(f"当前行数据 [序号: {row.get('Consecutive number', '')}]")
                print("-"*80)
                
                # 处理源端和目标端的连接关系
                source_device, source_terminal, _ = self._parse_device_string(source)
                target_device, target_terminal, _ = self._parse_device_string(target)
                
                # 展示解析结果
                if source:
                    print("\n源端解析结果:")
                    print("  " + self._format_device_info(source))
                    
                    if source_device and '+K' in source_device and source_terminal:
                        k_index = source_device.find('+K')
                        k_part = source_device[k_index+2:].split('.')[0].split('-')[0]
                        if k_part.isdigit():
                            if source_device in self.device_paths:
                                self.device_terminals[source_device].add(source_terminal)
                                print("  状态: [已添加端子]")
                                terminal_count += 1
                                
                                # 记录连接关系
                                if target_device:
                                    if source_device not in self.terminal_connections:
                                        self.terminal_connections[source_device] = {}
                                    if source_terminal not in self.terminal_connections[source_device]:
                                        self.terminal_connections[source_device][source_terminal] = []
                                    conn_info = {
                                        'connection_number': connection_number,
                                        'target_device': target_device,
                                        'target_terminal': target_terminal
                                    }
                                    self.terminal_connections[source_device][source_terminal].append(conn_info)
                                    print(f"  连接信息: -> {target_device}:{target_terminal}")
                                    if connection_number:
                                        print(f"  连接号码: {connection_number}")
                            else:
                                print("  状态: [设备未在步骤1中收集，已忽略]")
                        else:
                            print("  状态: [不是有效的K设备端子，已忽略]")
                
                if target:
                    print("\n目标端解析结果:")
                    print("  " + self._format_device_info(target))
                    
                    if target_device and '+K' in target_device and target_terminal:
                        k_index = target_device.find('+K')
                        k_part = target_device[k_index+2:].split('.')[0].split('-')[0]
                        if k_part.isdigit():
                            if target_device in self.device_paths:
                                self.device_terminals[target_device].add(target_terminal)
                                print("  状态: [已添加端子]")
                                terminal_count += 1
                                
                                # 记录连接关系
                                if source_device:
                                    if target_device not in self.terminal_connections:
                                        self.terminal_connections[target_device] = {}
                                    if target_terminal not in self.terminal_connections[target_device]:
                                        self.terminal_connections[target_device][target_terminal] = []
                                    conn_info = {
                                        'connection_number': connection_number,
                                        'target_device': source_device,
                                        'target_terminal': source_terminal
                                    }
                                    self.terminal_connections[target_device][target_terminal].append(conn_info)
                                    print(f"  连接信息: -> {source_device}:{source_terminal}")
                                    if connection_number:
                                        print(f"  连接号码: {connection_number}")
                            else:
                                print("  状态: [设备未在步骤1中收集，已忽略]")
                        else:
                            print("  状态: [不是有效的K设备端子，已忽略]")
                
                print("="*80)
        
        print(f"\n总共收集到 {terminal_count} 个端子")
        print("\n各K设备的端子列表:")
        for device in sorted(self.device_terminals.keys()):
            k_index = device.find('+K')
            k_part = device[k_index+2:].split('.')[0].split('-')[0]
            print(f"\nK{k_part}:")
            print(f"  设备路径: {device}")
            print("  端子列表:")
            for terminal in sorted(self.device_terminals[device]):
                print(f"    - {terminal}")
                if device in self.terminal_connections and terminal in self.terminal_connections[device]:
                    for conn in self.terminal_connections[device][terminal]:
                        print(f"      连接到: {conn['target_device']}:{conn['target_terminal']}")
                        if conn['connection_number']:
                            print(f"      连接号码: {conn['connection_number']}")
        
        input("\n设备端子收集完成，按回车键继续...")

    def _extract_device_id(self, device_path: str):
        """从设备路径中提取设备ID"""
        parts = device_path.split('.')
        if len(parts) > 1:
            return parts[-1]
        return device_path

    def _analyze_device_features(self):
        """步骤3: 分析设备特征，使用连接号码进行分析"""
        for device_id, terminals in self.device_terminals.items():
            # 初始化设备特征
            features = {
                'coil_terminals': [],
                'power_terminals': [],
                'auxiliary_groups': [],
                'diagnostic_terminals': []
            }
            
            # 获取该设备的所有连接信息
            device_connections = self.terminal_connections.get(device_id, {})
            
            print(f"\n分析设备 {device_id} 的连接关系:")
            for terminal in sorted(list(terminals)):
                # 只处理以'-'开头的端子
                if not terminal.startswith('-'):
                    continue
                    
                connections = device_connections.get(terminal, [])
                print(f"\n  端子 {terminal} 的连接:")
                for conn in connections:
                    print(f"    连接号码: {conn['connection_number']}")
                    print(f"    连接到: {conn['target_device']}:{conn['target_terminal']}")
                
                # 根据连接号码分析端子功能
                if connections:
                    for conn in connections:
                        conn_number = conn['connection_number']
                        # 如果连接号码存在，使用它来帮助识别端子功能
                        if conn_number:
                            if terminal.startswith('-L') or terminal.startswith('-T'):
                                features['power_terminals'].append({
                                    'terminal': terminal,
                                    'connection': conn_number
                                })
                            elif terminal.startswith('-A'):
                                features['coil_terminals'].append({
                                    'terminal': terminal,
                                    'connection': conn_number
                                })
                            elif terminal.startswith('-D'):
                                features['diagnostic_terminals'].append({
                                    'terminal': terminal,
                                    'connection': conn_number
                                })
                            else:
                                # 尝试将端子分配到辅助触点组
                                terminal_num = ''.join(filter(str.isdigit, terminal))
                                if terminal_num:
                                    group_num = (int(terminal_num) - 1) // 10
                                    while len(features['auxiliary_groups']) <= group_num:
                                        features['auxiliary_groups'].append([])
                                    features['auxiliary_groups'][group_num].append({
                                        'terminal': terminal,
                                        'connection': conn_number
                                    })
            
            # 排序并存储特征
            features['power_terminals'].sort(key=lambda x: x['terminal'])
            features['coil_terminals'].sort(key=lambda x: x['terminal'])
            features['diagnostic_terminals'].sort(key=lambda x: x['terminal'])
            for group in features['auxiliary_groups']:
                group.sort(key=lambda x: x['terminal'])
            
            self.device_features[device_id] = features
            
            print(f"\n设备 {device_id} 的特征分析结果:")
            print(f"  电源端子:")
            for term in features['power_terminals']:
                print(f"    {term['terminal']} (连接号码: {term['connection']})")
            print(f"  线圈端子:")
            for term in features['coil_terminals']:
                print(f"    {term['terminal']} (连接号码: {term['connection']})")
            print(f"  辅助触点组:")
            for i, group in enumerate(features['auxiliary_groups']):
                print(f"    组 {i+1}:")
                for term in group:
                    print(f"      {term['terminal']} (连接号码: {term['connection']})")
            print(f"  诊断端子:")
            for term in features['diagnostic_terminals']:
                print(f"    {term['terminal']} (连接号码: {term['connection']})")
def _determine_connection_type(self, source_terminal: str, target_terminal: str) -> str:
    """确定两个端子之间的连接类型"""
    if source_terminal.startswith('-A') or target_terminal.startswith('-A'):
        return 'control'  # 控制连接（线圈相关）
    elif source_terminal.startswith('-L') or source_terminal.startswith('-T') or \
         target_terminal.startswith('-L') or target_terminal.startswith('-T'):
        return 'power'   # 电源连接
    elif source_terminal.startswith('-D') or target_terminal.startswith('-D'):
        return 'diagnostic'  # 诊断连接
    else:
        return 'auxiliary'  # 辅助连接

def _identify_relay_types(self):
    """步骤4: 基于连接号码和端子连接关系识别继电器类型"""
    # 通过连接特征对设备进行分组
    type_groups = defaultdict(list)
    
    for device_id, features in self.device_features.items():
        # 收集所有连接号码信息
        terminal_connections = []
        
        # 添加电源端子连接
        for term in features['power_terminals']:
            terminal_connections.append((term['terminal'], term['connection']))
        
        # 添加线圈端子连接
        for term in features['coil_terminals']:
            terminal_connections.append((term['terminal'], term['connection']))
        
        # 添加辅助触点连接
        for group in features['auxiliary_groups']:
            group_connections = []
            for term in group:
                group_connections.append((term['terminal'], term['connection']))
            terminal_connections.extend(sorted(group_connections))
        
        # 添加诊断端子连接
        for term in features['diagnostic_terminals']:
            terminal_connections.append((term['terminal'], term['connection']))
        
        # 对连接信息进行排序以确保一致性
        terminal_connections.sort()
        
        # 分析端子间的连接关系
        terminal_relationships = []
        for terminal, conn_num in terminal_connections:
            # 获取此端子的所有连接
            if device_id in self.terminal_connections and terminal in self.terminal_connections[device_id]:
                for conn in self.terminal_connections[device_id][terminal]:
                    relationship = {
                        'source': terminal,
                        'target': conn['target_terminal'],
                        'connection_number': conn['connection_number'],
                        'type': self._determine_connection_type(terminal, conn['target_terminal'])
                    }
                    terminal_relationships.append(relationship)
        
        # 创建增强的特征签名，包含端子连接模式
        enhanced_signature = (
            tuple(terminal_connections),  # 基本端子连接信息
            tuple(sorted(  # 端子间连接关系
                (rel['source'], rel['target'], rel['type'])
                for rel in terminal_relationships
            ))
        )
        
        type_groups[enhanced_signature].append(device_id)
    
    # 为每个独特的连接组合创建类型
    type_counter = 1
    for signature, devices in type_groups.items():
        basic_connections, connection_patterns = signature
        type_id = f"TYPE_{type_counter}"
        print(f"\n发现继电器类型 {type_id}:")
        print("基本连接特征:")
        for terminal, connection in basic_connections:
            print(f"  端子 {terminal} - 连接号码: {connection}")
        
        print("端子间连接模式:")
        for source, target, conn_type in connection_patterns:
            print(f"  {source} -> {target} (类型: {conn_type})")
        
        print("实例:")
        for device_id in devices:
            print(f"  - {device_id} ({self.device_paths[device_id]})")
        
        # 存储类型信息
        self.relay_types[type_id] = {
            'type_id': type_id,
            'basic_connections': basic_connections,
            'connection_patterns': connection_patterns,
            'features': self.device_features[devices[0]]  # 使用第一个设备的特征作为代表
        }
        self.type_instances[type_id].extend(devices)
        type_counter += 1
    
    print("\n继电器类型分析完成")
    print(f"总共发现 {len(self.relay_types)} 种不同类型的继电器")

if __name__ == "__main__":
    # Create an instance of RelayTypeAnalyzer
    analyzer = RelayTypeAnalyzer()
    
    # Try to analyze the CSV file from the data directory
    try:
        csv_path = "data/SmartWiringzta.csv"
        print(f"Analyzing CSV file (仅处理-K/-D/-S/-Q设备): {csv_path}")
        analyzer.analyze_csv(csv_path)
        
        # Print discovered relay types
        print("\nDiscovered Relay Types:")
        for type_key, relay_type in analyzer.relay_types.items():
            if analyzer.is_valid_device(relay_type['type_id']):
                print(f"\nType ID: {relay_type['type_id']}")
                print(f"Features:")
                print(f"  线圈端子: {relay_type['features']['coil_terminals']}")
                print(f"  主触点: {relay_type['features']['power_terminals']}")
                print(f"  辅助触点组: {relay_type['features']['auxiliary_groups']}")
                print(f"  诊断端子: {relay_type['features']['diagnostic_terminals']}")
                print(f"Instances:")
                for device_id in analyzer.type_instances[type_key]:
                    print(f"  - {analyzer.device_paths[device_id]}")
    except FileNotFoundError:
        print("Error: Could not find the CSV file. Please ensure the data file exists in the correct location.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")