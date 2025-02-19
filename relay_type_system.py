"""
继电器类型系统 - 用于管理和分析继电器型号及其实例
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
import csv
import re
from collections import defaultdict
from relay_rules import RelayRules, create_relay, get_terminal_info, get_possible_connections

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
        self.device_structures = {}  # 存储设备结构信息 {device_id: structure}

    def _create_device_structure(self, device_path: str, device_type: str, device_id: str) -> Dict:
        """创建设备结构"""
        try:
            # 提取设备属性
            props = {
                'location': device_path.split('-')[0],  # 例如 A01+K1.H2
                'function': device_path.split('+')[0].replace('=', ''),  # 例如 A01
                'status': 'active'
            }
            
            # 使用relay_rules创建结构
            structure = create_relay(device_type, device_id, props)
            print(f"成功创建{device_type}设备结构: {device_id}")
            return structure
        except Exception as e:
            print(f"创建{device_type}设备结构时出错 {device_id}: {str(e)}")
            return None

    # 继电器/接触器的标准端子连接规则
    TERMINAL_RULES = {
        'coil': {
            'terminals': ['A1', 'A2'],  # 线圈端子
            'relations': [
                {'type': 'control', 'affects': 'main_contacts'}  # 线圈控制主触点
            ]
        },
        'main_contacts': {
            'pairs': [
                {'input': 'L1', 'output': 'T1'},
                {'input': 'L2', 'output': 'T2'},
                {'input': 'L3', 'output': 'T3'}
            ],
            'types': {
                'NO': {'L1-T1', 'L2-T2', 'L3-T3'},  # 常开主触点
                'NC': {'L1-T2', 'L2-T3', 'L3-T1'}   # 常闭主触点（如有）
            }
        },
        'auxiliary_contacts': {
            'groups': [
                {'com': '13', 'nc': '14', 'no': '12'},  # 第一组辅助触点
                {'com': '23', 'nc': '24', 'no': '22'},  # 第二组辅助触点
                {'com': '33', 'nc': '34', 'no': '32'}   # 第三组辅助触点
            ],
            'meaning': {
                'com': '公共端',
                'nc': '常闭触点',
                'no': '常开触点'
            }
        }
    }

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
        # 显示连接模型定义
        print("继电器连接模型定义:")
        print("1. 连接类型:")
        print("  - control: 控制连接（线圈相关）")
        print("  - power: 电源连接（主触点）")
        print("  - auxiliary: 辅助连接")
        print("  - diagnostic: 诊断连接")
        print("\n2. 端子分类:")
        print("  - 线圈端子: -A1, -A2")
        print("  - 主触点: -L*, -T*")
        print("  - 辅助触点: 数字编号（如11, 12, 14等）")
        print("  - 诊断端子: -D*")
        print("\n3. 设备识别规则:")
        print("  - 控制设备: -K*, -Q*, -S*结尾")
        print("  - 直接连接: 其他设备")
        print("\n" + "="*80 + "\n")

        print("步骤1: 收集设备标识符...")
        self._collect_device_paths(csv_path)
        
           
        print("\n步骤2: 分析设备特征...")
        self._analyze_device_features()
        
       

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

    def _determine_device_type(self, device_path: str) -> str:
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
            # 排除 -X 开头的设备
            if clean_part.startswith('X'):
                return 'terminal_block'  # 端子排设备
            if ((clean_part.startswith('K') or
                 clean_part.startswith('Q') or
                 clean_part.startswith('S')) and
                any(c.isdigit() for c in clean_part)):
                return 'ctrl'
        return 'direct'

    def _analyze_terminal_type(self, terminal: str) -> dict:
        """分析端子类型和功能"""
        if not terminal or not terminal.startswith('-'):
            return None
        
        result = {
            'type': None,        # power/coil/auxiliary/diagnostic
            'subtype': None,     # 对于主触点: input/output; 对于辅助触点: com/nc/no
            'number': None,      # 端子编号
            'group': None        # 辅助触点组编号
        }
        
        # 分析主触点（L/T）
        if terminal.startswith('-L') or terminal.startswith('-T'):
            result['type'] = 'power'
            result['subtype'] = 'input' if terminal.startswith('-L') else 'output'
            result['number'] = terminal[2:]  # 去除'-L'或'-T'前缀
            return result
        
        # 分析线圈端子（A1/A2）
        if terminal.startswith('-A'):
            result['type'] = 'coil'
            result['number'] = terminal[2:]  # 去除'-A'前缀
            result['subtype'] = 'A1' if result['number'] == '1' else 'A2'
            return result
        
        # 分析诊断端子（D）
        if terminal.startswith('-D'):
            result['type'] = 'diagnostic'
            result['number'] = terminal[2:]  # 去除'-D'前缀
            return result
        
        # 分析辅助触点（数字编号）
        terminal_num = ''.join(filter(str.isdigit, terminal))
        if terminal_num:
            result['type'] = 'auxiliary'
            result['number'] = terminal_num
            result['group'] = (int(terminal_num) - 1) // 10  # 计算组号
            
            # 确定辅助触点类型
            if terminal_num.endswith('3'):
                result['subtype'] = 'com'  # 公共端
            elif terminal_num.endswith('4'):
                result['subtype'] = 'nc'   # 常闭触点
            elif terminal_num.endswith('2'):
                result['subtype'] = 'no'   # 常开触点
            
            return result
        
        return None

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
            
        # 检查是否是端子排设备
        if '-X' in device_str:
            return None, None, 'terminal_block'
        
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
            return device_path, None, self._determine_device_type(device_path)
            
        # 分离设备路径和端子部分
        # 移除开头的等号用于内部存储，但在 device_paths 中会保留原始格式
        device_path = (orig_str[1:colon_index] if orig_str.startswith('=') else orig_str[:colon_index]).strip()
        terminal_part = orig_str[colon_index + 1:].strip()
        
        # 规范化端子标识
        terminal = self._normalize_terminal_id(terminal_part)
        
        # 确定连接类型
        conn_type = self._determine_device_type(device_path)
        
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
                            # 检查是否是端子排设备
                            if conn_type != 'terminal_block':
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
                            else:
                                print(f"  跳过端子排设备: {source}")
                
                # 处理目标端
                if target:
                    target_device, target_terminal, conn_type = self._parse_device_string(target)
                    if target_device and '+K' in target_device:
                        is_valid, k_id = self._is_valid_k_device(target_device)
                        if is_valid:
                            # 检查是否是端子排设备
                            if conn_type != 'terminal_block':
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
                            else:
                                print(f"  跳过端子排设备: {target}")
        
        ctrl_count = sum(1 for conn_type in self.connection_types.values() if conn_type == 'ctrl')
        print(f"\n总共找到 {device_count} 个设备，其中 {ctrl_count} 个控制连接设备")
        print("\n控制连接设备列表:")
        # 收集每个设备的所有端子并存储到类属性中
        print("\n开始收集设备端子信息...")
        for device, connections in self.device_connections.items():
            print(f"\n处理设备: {device} ({self.device_paths[device]})")
            # 收集端子
            for conn in connections:
                if conn['terminal']:
                    self.device_terminals[device].add(conn['terminal'])
                # 从目标端也收集端子
                if ':' in conn.get('target', ''):
                    target_device = conn['target'].split(':')[0]
                    target_terminal = conn['target'].split(':')[1]
                    if target_device == self.device_paths[device]:
                        self.device_terminals[device].add(target_terminal)
            
            # 显示收集结果
            terminals = sorted(list(self.device_terminals[device]))
            if terminals:
                print(f"  找到 {len(terminals)} 个端子:")
                print(f"  {terminals}")
        
        input("\n设备路径收集完成，按回车键继续...")



    def _extract_device_id(self, device_path: str):
        """从设备路径中提取设备ID"""
        parts = device_path.split('.')
        if len(parts) > 1:
            return parts[-1]
        return device_path

    def _analyze_device_features(self):
        """分析设备特征并建立端子间的图论连接关系"""
        print("\n开始分析设备特征和建立图论连接关系...")
        if not self.device_terminals:
            print("警告: 没有找到任何设备的端子信息")
            return

        for device_id, terminals in self.device_terminals.items():
            print(f"\n分析设备: {device_id}")
            device_path = self.device_paths.get(device_id, '<未知>')
            print(f"设备路径: {device_path}")
            
            if not terminals:
                print("  警告：设备没有端子信息，跳过分析")
                continue
            
            # 从设备ID提取设备类型
            match = re.search(r'-([KQS])\d+', device_id)
            if not match:
                print(f"  警告：无法从设备ID提取类型: {device_id}")
                continue
                
            device_type = match.group(1)
            print(f"  设备类型: {device_type}")
                
            # 创建或获取设备结构
            if device_id not in self.device_structures:
                structure = self._create_device_structure(device_path, device_type, device_id)
                if not structure:
                    print(f"  错误：无法创建设备结构，跳过分析")
                    continue
                self.device_structures[device_id] = structure
            
            structure = self.device_structures[device_id]
            
            # 初始化设备的图论结构
            device_graph = {
                'nodes': [],      # 端子节点
                'edges': [],      # 端子间连接
                'device_type': device_type,
                'structure': structure
            }
            
            # 分析并添加端子节点
            for terminal in sorted(terminals):
                terminal_info = self._classify_terminal(terminal, device_id)
                if terminal_info['type'] != 'unknown':
                    device_graph['nodes'].append({
                        'id': terminal,
                        'device': device_id,
                        'type': terminal_info['type'],
                        'subtype': terminal_info['subtype'],
                        'valid_connections': terminal_info['valid_connections']
                    })
                    print(f"  添加端子节点: {terminal} (类型: {terminal_info['type']}, 子类型: {terminal_info['subtype']})")
            
            # 根据继电器规则和验证建立端子之间的连接
            for terminal in sorted(terminals):
                for other_terminal in sorted(terminals):
                    if terminal != other_terminal:
                        if self._validate_connection(terminal, other_terminal, structure):
                            device_graph['edges'].append({
                                'source': terminal,
                                'target': other_terminal,
                                'type': 'validated_connection'
                            })
                            print(f"  建立验证连接: {terminal} -> {other_terminal}")
            
            # 存储图论结构
            self.device_features[device_id] = device_graph
            
            # 打印分析结果
            print(f"\n设备 {device_id} ({device_type}) 的图论分析结果:")
            print("  节点列表:")
            for node in device_graph['nodes']:
                print(f"    - {node['id']} (类型: {node['type']}, 子类型: {node.get('subtype', 'N/A')})")
            print("  连接关系:")
            for edge in device_graph['edges']:
                print(f"    - {edge['source']} -> {edge['target']} (类型: {edge['type']})")
                
        print("\n设备特征和图论连接分析完成")

    def _validate_connection(self, source_terminal: str, target_terminal: str, device_structure: dict) -> bool:
        """
        验证两个端子之间的连接是否合法
        Args:
            source_terminal: 源端子
            target_terminal: 目标端子
            device_structure: 设备结构信息
        Returns:
            bool: 连接是否合法
        """
        possible_connections = get_possible_connections(source_terminal, device_structure)
        return target_terminal in possible_connections

    def _classify_terminal(self, terminal: str, device_id: str) -> dict:
        """
        识别并分类端子
        Args:
            terminal: 端子标识符
            device_id: 设备ID
        Returns:
            dict: 端子信息
        """
        if device_id not in self.device_structures:
            print(f"  警告：设备 {device_id} 的结构信息不存在")
            return {'type': 'unknown', 'subtype': None, 'terminal': terminal}
            
        device_structure = self.device_structures[device_id]
        term_type, subtype = get_terminal_info(terminal)
        
        return {
            'type': term_type,
            'subtype': subtype,
            'terminal': terminal,
            'valid_connections': get_possible_connections(terminal, device_structure)
        }

    def _print_device_features(self, device_id: str, features: dict):
        """打印设备特征分析结果"""
        print(f"\n设备 {device_id} 的特征统计:")
        print(f"  主触点数量: {len(features['power_terminals'])}")
        print(f"  线圈端子数量: {len(features['coil_terminals'])}")
        print(f"  辅助触点组数量: {len(features['auxiliary_groups'])}")
        print(f"  辅助触点总数: {sum(len(g) for g in features['auxiliary_groups'])}")
        print(f"  诊断端子数量: {len(features['diagnostic_terminals'])}")



    def _build_terminal_graph(self, device_id: str, features: dict) -> dict:
        """构建设备内部端子的图论关系"""
        graph = {
            'nodes': [],  # 存储端子节点
            'edges': [],  # 存储端子间的关系
            'device_id': device_id
        }

        # 1. 添加线圈节点和控制关系
        coil_terminals = [t['terminal'] for t in features['coil_terminals']]
        for terminal in coil_terminals:
            graph['nodes'].append({
                'id': terminal,
                'type': 'coil',
                'function': '线圈端子'
            })

        # 2. 添加主触点节点和其内部关系
        power_terminals = {}
        for term in features['power_terminals']:
            terminal = term['terminal']
            graph['nodes'].append({
                'id': terminal,
                'type': 'main_contact',
                'function': 'L端子' if terminal.startswith('L') else 'T端子'
            })
            power_terminals[terminal] = term

        # 3. 添加辅助触点节点和其内部关系
        for group_idx, group in enumerate(features['auxiliary_groups'], 1):
            terminals = [t['terminal'] for t in group]
            for term in group:
                terminal = term['terminal']
                terminal_num = ''.join(filter(str.isdigit, terminal))
                
                # 确定端子功能（COM/NC/NO）
                function = None
                if terminal_num.endswith('3'):  # COM端子
                    function = 'COM'
                elif terminal_num.endswith('4'):  # NC端子
                    function = 'NC'
                elif terminal_num.endswith('2'):  # NO端子
                    function = 'NO'
                
                graph['nodes'].append({
                    'id': terminal,
                    'type': 'auxiliary_contact',
                    'group': group_idx,
                    'function': function
                })

        # 4. 建立控制关系（线圈->主触点）
        for coil in coil_terminals:
            for term in power_terminals.values():
                graph['edges'].append({
                    'source': coil,
                    'target': term['terminal'],
                    'type': 'control',
                    'description': '线圈控制'
                })

        # 5. 建立主触点内部关系
        self._build_main_contact_relations(graph, power_terminals)

        # 6. 建立辅助触点组内部关系
        self._build_auxiliary_contact_relations(graph, features['auxiliary_groups'])

        return graph

    def _build_main_contact_relations(self, graph: dict, power_terminals: dict):
        """构建主触点内部关系"""
        # 根据端子号配对
        pairs = {}
        for terminal, term_info in power_terminals.items():
            if terminal.startswith('L'):
                num = terminal.replace('L', '')
                pairs[num] = {'L': terminal}
            elif terminal.startswith('T'):
                num = terminal.replace('T', '')
                if num not in pairs:
                    pairs[num] = {}
                pairs[num]['T'] = terminal

        # 添加主触点对之间的关系
        for pair in pairs.values():
            if 'L' in pair and 'T' in pair:
                graph['edges'].append({
                    'source': pair['L'],
                    'target': pair['T'],
                    'type': 'power_connection',
                    'description': '主触点对'
                })

    def _build_auxiliary_contact_relations(self, graph: dict, aux_groups: List[list]):
        """构建辅助触点组内部关系"""
        for group_idx, group in enumerate(aux_groups, 1):
            terminals = [t['terminal'] for t in group]
            com = nc = no = None
            
            # 识别COM/NC/NO端子
            for terminal in terminals:
                terminal_num = ''.join(filter(str.isdigit, terminal))
                if not terminal_num:
                    continue
                    
                if terminal_num.endswith('3'):  # COM
                    com = terminal
                elif terminal_num.endswith('4'):  # NC
                    nc = terminal
                elif terminal_num.endswith('2'):  # NO
                    no = terminal
            
            # 添加COM到NC/NO的关系
            if com:
                if nc:
                    graph['edges'].append({
                        'source': com,
                        'target': nc,
                        'type': 'auxiliary_nc',
                        'description': f'辅助触点组{group_idx}常闭连接'
                    })
                if no:
                    graph['edges'].append({
                        'source': com,
                        'target': no,
                        'type': 'auxiliary_no',
                        'description': f'辅助触点组{group_idx}常开连接'
                    })

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
            for term_type in ['power_terminals', 'coil_terminals']:
                for terminal in features[term_type]:
                    for conn in terminal.get('connections', []):
                        relationship = {
                            'source': terminal['terminal'],
                            'target': conn.get('target_terminal'),
                            'type': self._determine_connection_type(
                                terminal['terminal'],
                                conn.get('target_terminal')
                            )
                        }
                        if relationship['target']:  # 只添加有效目标的关系
                            terminal_relationships.append(relationship)
            
            # 处理辅助触点组
            for group in features['auxiliary_groups']:
                for terminal in group:
                    for conn in terminal.get('connections', []):
                        relationship = {
                            'source': terminal['terminal'],
                            'target': conn.get('target_terminal'),
                            'type': 'auxiliary'
                        }
                        if relationship['target']:
                            terminal_relationships.append(relationship)
            
            # 创建设备特征签名
            enhanced_signature = (
                len(features['coil_terminals']),       # 线圈端子数量
                len(features['power_terminals']),      # 主触点数量
                len(features['auxiliary_groups']),     # 辅助触点组数量
                sum(len(g) for g in features['auxiliary_groups']),  # 辅助触点总数
                tuple(sorted(                          # 端子连接模式
                    (rel['source'], rel['target'], rel['type'])
                    for rel in terminal_relationships
                ))
            )
            
            type_groups[enhanced_signature].append(device_id)
        
        # 为每个独特的连接组合创建类型
        type_counter = 1
        for signature, devices in type_groups.items():
            # 解析特征签名
            coil_count, power_count, aux_groups, aux_total, connection_patterns = signature
            type_id = f"TYPE_{type_counter}"

            print(f"\n发现继电器类型 {type_id}:")
            print("端子配置:")
            print(f"  线圈端子数量: {coil_count}")
            print(f"  主触点组数量: {power_count}")
            print(f"  辅助触点组数量: {aux_groups}")
            print(f"  辅助触点总数: {aux_total}")
            
            print("\n连接模式:")
            connection_groups = defaultdict(list)
            for source, target, conn_type in connection_patterns:
                connection_groups[conn_type].append((source, target))
            
            for conn_type, conns in sorted(connection_groups.items()):
                print(f"  {conn_type}类型连接:")
                for source, target in sorted(conns):
                    print(f"    {source} -> {target}")
            
            print("\n关联设备:")
            for device_id in sorted(devices):
                print(f"  - {device_id} ({self.device_paths[device_id]})")
            
            # 构建内部端子图论
            terminal_graph = self._build_terminal_graph(devices[0], self.device_features[devices[0]])

            # 存储类型信息
            self.relay_types[type_id] = {
                'type_id': type_id,
                'type_id': type_id,
                'terminal_counts': {
                    'coil': coil_count,
                    'power': power_count,
                    'auxiliary_groups': aux_groups,
                    'auxiliary_total': aux_total
                },
                'connection_patterns': connection_patterns,
                'features': self.device_features[devices[0]],
                'terminal_graph': terminal_graph,
                'instance_count': len(devices)
            }
            self.type_instances[type_id].extend(devices)
            
            # 打印内部端子图论信息
            print("\n内部端子图论分析:")
            print("  节点列表:")
            for node in terminal_graph['nodes']:
                print(f"    - {node['id']} (类型: {node['type']}, 功能: {node.get('function', 'unknown')})")
            print("  连接关系:")
            for edge in terminal_graph['edges']:
                print(f"    - {edge['source']} -> {edge['target']} "
                      f"(类型: {edge['type']}, 说明: {edge['description']})")
            
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
        
        # # Print discovered relay types
        # print("\nDiscovered Relay Types:")
        # for type_key, relay_type in analyzer.relay_types.items():
        #     if analyzer.is_valid_device(relay_type['type_id']):
        #         print(f"\nType ID: {relay_type['type_id']}")
        #         print(f"Features:")
        #         print(f"  线圈端子: {relay_type['features']['coil_terminals']}")
        #         print(f"  主触点: {relay_type['features']['power_terminals']}")
        #         print(f"  辅助触点组: {relay_type['features']['auxiliary_groups']}")
        #         print(f"  诊断端子: {relay_type['features']['diagnostic_terminals']}")
        #         print(f"Instances:")
        #         for device_id in analyzer.type_instances[type_key]:
        #             print(f"  - {analyzer.device_paths[device_id]}")
    except FileNotFoundError:
        print("Error: Could not find the CSV file. Please ensure the data file exists in the correct location.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")