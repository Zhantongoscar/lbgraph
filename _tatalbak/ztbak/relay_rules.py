"""
继电器规则处理模块 - 基于图论的继电器建模
"""

class RelayType:
    """继电器类型定义"""
    POWER_RELAY = "POWER_RELAY"  # 功率继电器
    SIGNAL_RELAY = "SIGNAL_RELAY"  # 信号继电器
    TIME_RELAY = "TIME_RELAY"    # 时间继电器
    SAFETY_RELAY = "SAFETY_RELAY"  # 安全继电器
    BUTTON = "BUTTON"  # 按钮类型

class ContactType:
    """触点类型定义"""
    NO = "NO"  # 常开触点
    NC = "NC"  # 常闭触点
    CO = "CO"  # 转换触点
    DM = "DM"  # 双断点触点
    POWER = "POWER"  # 功率触点
    MANUAL = "MANUAL"  # 手动操作触点

class RelayTerminalType:
    """继电器端子类型"""
    POWER_IN = "POWER_IN"      # 电源输入端子 (L1,L2,L3)
    POWER_OUT = "POWER_OUT"    # 负载输出端子 (T1,T2,T3)
    COIL = "COIL"             # 线圈端子 (A1,A2)
    CONTACT = "CONTACT"        # 触点端子 (11,12,14等)
    DIAGNOSTIC = "DIAGNOSTIC"  # 诊断端子 (D1,D2)

class RelayTerminalRole:
    """端子角色"""
    # 电源相关
    LINE = "LINE"             # 火线
    NEUTRAL = "NEUTRAL"       # 零线
    EARTH = "EARTH"          # 接地
    # 线圈相关
    COIL_PLUS = "COIL_PLUS"   # 线圈正极
    COIL_MINUS = "COIL_MINUS" # 线圈负极
    # 触点相关
    COM = "COM"              # 公共端
    NO = "NO"               # 常开端
    NC = "NC"               # 常闭端
    # 其他
    DIAGNOSTIC = "DIAGNOSTIC" # 诊断端子
    AUXILIARY = "AUXILIARY"   # 辅助端子

TERMINAL_MAPPING = {
    # 电源端子
    'L': {'type': RelayTerminalType.POWER_IN, 'role': RelayTerminalRole.LINE},
    'N': {'type': RelayTerminalType.POWER_IN, 'role': RelayTerminalRole.NEUTRAL},
    'T': {'type': RelayTerminalType.POWER_OUT, 'role': RelayTerminalRole.LINE},
    'PE': {'type': RelayTerminalType.POWER_IN, 'role': RelayTerminalRole.EARTH},
    # 控制端子
    'A': {'type': RelayTerminalType.COIL, 'role': None},  # role将根据数字确定
    'B': {'type': RelayTerminalType.CONTACT, 'role': RelayTerminalRole.AUXILIARY},
    # 诊断端子
    'D': {'type': RelayTerminalType.DIAGNOSTIC, 'role': RelayTerminalRole.DIAGNOSTIC},
}

# 继电器型号配置
RELAY_CONFIGS = {
    # 三相接触器系列
    "3RT": {
        "type": RelayType.POWER_RELAY,
        "coil_voltage": "230VAC",
        "power_poles": {
            "type": "3-PHASE",
            "count": 3,
            "rating": "30A",
            "terminals": [
                {"input": "L1", "output": "T1"},
                {"input": "L2", "output": "T2"},
                {"input": "L3", "output": "T3"}
            ]
        },
        "auxiliary_contacts": [
            {"type": ContactType.NO, "count": 1, "rating": "10A"}
        ],
        "diagnostic_contacts": [
            {"type": ContactType.NO, "terminals": ["D1", "D2"]}
        ]
    },
    
    # 标准继电器类型
    "K": {
        "type": RelayType.SIGNAL_RELAY,
        "coil_voltage": "24VDC",
        "contacts": [
            {"type": ContactType.CO, "count": 1, "rating": "6A"}
        ]
    },
    
    # 按钮类型
    "S": {
        "type": RelayType.BUTTON,
        "contacts": [
            {"type": ContactType.MANUAL, "count": 1, "rating": "6A"}
        ]
    },
    
    # 多功能按钮
    "S-MULTI": {
        "type": RelayType.BUTTON,
        "contacts": [
            {"type": ContactType.NO, "count": 2, "rating": "6A"},
            {"type": ContactType.NC, "count": 2, "rating": "6A"}
        ]
    },
    
    # 多功能继电器
    "RY": {
        "type": RelayType.SIGNAL_RELAY,
        "coil_voltage": "24VDC",
        "versions": {
            "standard": {
                "contacts": [
                    {"type": ContactType.CO, "count": 2, "rating": "6A"}
                ]
            },
            "extended": {
                "contacts": [
                    {"type": ContactType.CO, "count": 4, "rating": "6A"},
                    {"type": ContactType.NO, "count": 2, "rating": "6A"}
                ]
            },
            "safety": {
                "contacts": [
                    {"type": ContactType.NO, "count": 4, "rating": "6A"},
                    {"type": ContactType.NC, "count": 2, "rating": "6A"}
                ]
            }
        }
    },
    
    # 时间继电器
    "H3Y": {
        "type": RelayType.TIME_RELAY,
        "coil_voltage": "24VDC",
        "timing": "0.1-10s",
        "contacts": [
            {"type": ContactType.CO, "count": 2, "rating": "5A"}
        ]
    },
    
    # Phoenix Contact 继电器模块
    "PSR-SCP-24UC/URM/5X1/2X2": {
        "type": RelayType.SAFETY_RELAY,
        "coil_voltage": "24VDC",
        "contacts": [
            {"type": ContactType.NO, "count": 5, "rating": "6A"},
            {"type": ContactType.NC, "count": 2, "rating": "6A"}
        ]
    },
    "PSR-SPC-24DC/ESD/4X1/30": {
        "type": RelayType.SAFETY_RELAY,
        "coil_voltage": "24VDC",
        "contacts": [
            {"type": ContactType.NO, "count": 4, "rating": "6A"},
            {"type": ContactType.NC, "count": 1, "rating": "6A"}
        ]
    }
}

def create_terminal_id(device_path, terminal_id):
    """创建端子完整标识符
    Args:
        device_path: 设备完整路径，如 "=A01+K1.H2-Q1"
        terminal_id: 端子基本ID，如 "A1"
    Returns:
        str: 完整的端子标识符，如 "=A01+K1.H2-Q1:A1"
    """
    return f"{device_path}:{terminal_id}"

def create_relay_structure(device_id, config):
    """创建继电器的完整图结构
    Args:
        device_id: 设备ID，可以是简单形式如 "K1" 或完整形式如 "=A01+K1.H2-Q1"
        config: 继电器配置
    Returns:
        dict: 节点和关系的配置
    """
    # 解析设备标识符
    device_info = None
    device_path = device_id
    if any(c in device_id for c in ['=', '+', '.', '-']):
        device_info = parse_device_identifier(device_id)
        if device_info:
            device_id = device_info['device_id']
            device_path = device_info['device_path']
    
    structure = {
        'nodes': [],
        'relationships': []
    }
    
    # 创建继电器本体节点
    relay_node = {
        'id': device_path,  # 使用完整的设备路径作为ID
        'labels': ['Component', 'IntComp', 'Relay'],
        'properties': {
            'name': device_path,
            'device_id': device_id,
            'type': config['type'],
            'coil_voltage': config['coil_voltage']
        }
    }
    
    # 如果有完整的设备信息，添加到属性中
    if device_info:
        relay_node['properties'].update({
            'location': device_info['location'],
            'sub_terminal': device_info['sub_terminal'],
            'reference_device': device_info['reference']
        })
    
    structure['nodes'].append(relay_node)
    
    # 2. 创建线圈端子节点
    coil_terminals = []
    if config['type'] == RelayType.POWER_RELAY:
        # 功率继电器使用标准线圈
        coil_terminals.extend([
            {
                'id': create_terminal_id(device_path, 'A1'),
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': create_terminal_id(device_path, 'A1'),
                    'device_path': device_path,
                    'terminal': 'A1',
                    'coil_type': RelayCoilType.STANDARD,
                    'polarity': 'positive',
                    'voltage': 0.0
                }
            },
            {
                'id': create_terminal_id(device_path, 'A2'),
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': create_terminal_id(device_path, 'A2'),
                    'device_path': device_path,
                    'terminal': 'A2',
                    'coil_type': RelayCoilType.STANDARD,
                    'polarity': 'negative',
                    'voltage': 0.0
                }
            }
        ])
    elif config['type'] == RelayType.TIME_RELAY:
        # 时间继电器可能有额外的控制端子
        coil_terminals.extend([
            {
                'id': create_terminal_id(device_path, 'A1'),
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': create_terminal_id(device_path, 'A1'),
                    'device_path': device_path,
                    'terminal': 'A1',
                    'coil_type': RelayCoilType.ELECTRONIC,
                    'polarity': 'positive',
                    'voltage': 0.0
                }
            },
            {
                'id': create_terminal_id(device_path, 'A2'),
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': create_terminal_id(device_path, 'A2'),
                    'device_path': device_path,
                    'terminal': 'A2',
                    'coil_type': RelayCoilType.ELECTRONIC,
                    'polarity': 'negative',
                    'voltage': 0.0
                }
            },
            {
                'id': create_terminal_id(device_path, 'B1'),
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': create_terminal_id(device_path, 'B1'),
                    'device_path': device_path,
                    'terminal': 'B1',
                    'coil_type': RelayCoilType.ELECTRONIC,
                    'function': 'timing_control',
                    'voltage': 0.0
                }
            }
        ])
    else:
        # 标准控制继电器，支持多组线圈
        for i in range(1, 3):  # 最多支持两组线圈
            group_suffix = str(i) if i > 1 else ''
            coil_terminals.extend([
                {
                    'id': create_terminal_id(device_path, f"A1{group_suffix}"),
                    'labels': ['Component', 'Vertex', 'CoilTerminal'],
                    'properties': {
                        'name': create_terminal_id(device_path, f"A1{group_suffix}"),
                        'device_path': device_path,
                        'terminal': f"A1{group_suffix}",
                        'coil_type': RelayCoilType.DUAL if group_suffix else RelayCoilType.STANDARD,
                        'coil_group': i,
                        'polarity': 'positive',
                        'voltage': 0.0
                    }
                },
                {
                    'id': create_terminal_id(device_path, f"A2{group_suffix}"),
                    'labels': ['Component', 'Vertex', 'CoilTerminal'],
                    'properties': {
                        'name': create_terminal_id(device_path, f"A2{group_suffix}"),
                        'device_path': device_path,
                        'terminal': f"A2{group_suffix}",
                        'coil_type': RelayCoilType.DUAL if group_suffix else RelayCoilType.STANDARD,
                        'coil_group': i,
                        'polarity': 'negative',
                        'voltage': 0.0
                    }
                }
            ])
    
    structure['nodes'].extend(coil_terminals)
    
    # 3. 创建线圈关系
    for i in range(0, len(coil_terminals), 2):
        structure['relationships'].append({
            'from': coil_terminals[i]['id'],
            'to': coil_terminals[i+1]['id'],
            'type': 'COIL_CONNECTION',
            'properties': {
                'impedance': config.get('coil_impedance', '100Ω'),
                'rated_voltage': config['coil_voltage'],
                'coil_group': coil_terminals[i]['properties'].get('coil_group', 1)
            }
        })
    
    # 4. 创建主触点端子和关系
    if 'power_poles' in config:
        poles = config['power_poles']
        for term in poles['terminals']:
            # 创建输入端子(L1,L2,L3)
            input_node = {
                'id': create_terminal_id(device_path, term['input']),
                'labels': ['Component', 'Vertex', 'PowerTerminal'],
                'properties': {
                    'name': create_terminal_id(device_path, term['input']),
                    'device_path': device_path,
                    'terminal': term['input'],
                    'terminal_type': 'POWER_IN',
                    'phase': term['input'][-1],
                    'rating': poles['rating']
                }
            }
            
            # 创建输出端子(T1,T2,T3)
            output_node = {
                'id': create_terminal_id(device_path, term['output']),
                'labels': ['Component', 'Vertex', 'PowerTerminal'],
                'properties': {
                    'name': create_terminal_id(device_path, term['output']),
                    'device_path': device_path,
                    'terminal': term['output'],
                    'terminal_type': 'POWER_OUT',
                    'phase': term['output'][-1],
                    'rating': poles['rating']
                }
            }
            
            structure['nodes'].extend([input_node, output_node])
            
            # 创建开关关系
            structure['relationships'].append({
                'from': input_node['id'],
                'to': output_node['id'],
                'type': 'SWITCH_TO',
                'properties': {
                    'state': 'open',
                    'phase': term['input'][-1],
                    'rating': poles['rating']
                }
            })
            
    # 5. 创建辅助触点节点和关系
    if 'contacts' in config:
        for contact_config in config['contacts']:
            for i in range(contact_config['count']):
                group = i + 1
                
                # 根据触点类型创建不同的端子组合
                if contact_config['type'] == ContactType.CO:
                    # 创建转换触点组 (COM-NC-NO)
                    terminals = [
                        (f"{group}1", RelayTerminalRole.COM, "closed"),
                        (f"{group}2", RelayTerminalRole.NC, "closed"),
                        (f"{group}4", RelayTerminalRole.NO, "open")
                    ]
                elif contact_config['type'] == ContactType.NO:
                    # 创建常开触点
                    terminals = [(f"{group}4", RelayTerminalRole.NO, "open")]
                elif contact_config['type'] == ContactType.NC:
                    # 创建常闭触点
                    terminals = [(f"{group}2", RelayTerminalRole.NC, "closed")]
                    
                # 创建端子节点
                contact_nodes = []
                for terminal_id, role, default_state in terminals:
                    node = {
                        'id': create_terminal_id(device_path, terminal_id),
                        'labels': ['Component', 'Vertex', 'ContactTerminal'],
                        'properties': {
                            'name': create_terminal_id(device_path, terminal_id),
                            'device_path': device_path,
                            'terminal': terminal_id,
                            'contact_role': role,
                            'contact_group': group,
                            'rating': contact_config['rating'],
                            'default_state': default_state
                        }
                    }
                    contact_nodes.append(node)
                    structure['nodes'].append(node)
                
                # 创建触点组内的关系
                if len(contact_nodes) > 1:
                    com_node = next(n for n in contact_nodes 
                                  if n['properties']['contact_role'] == RelayTerminalRole.COM)
                    
                    for node in contact_nodes:
                        if node['id'] != com_node['id']:
                            structure['relationships'].append({
                                'from': com_node['id'],
                                'to': node['id'],
                                'type': 'SWITCH_TO',
                                'properties': {
                                    'state': node['properties']['default_state'],
                                    'group': group
                                }
                            })
    
    # 6. 创建诊断端子（如果有）
    if 'diagnostic_contacts' in config:
        for diag_config in config['diagnostic_contacts']:
            for terminal_id in diag_config['terminals']:
                node = {
                    'id': create_terminal_id(device_path, terminal_id),
                    'labels': ['Component', 'Vertex', 'DiagnosticTerminal'],
                    'properties': {
                        'name': create_terminal_id(device_path, terminal_id),
                        'device_path': device_path,
                        'terminal': terminal_id,
                        'terminal_type': 'DIAGNOSTIC',
                        'state': 'open'
                    }
                }
                structure['nodes'].append(node)
    
    # 7. 创建继电器本体与所有端子的从属关系
    for node in structure['nodes'][1:]:  # 跳过继电器本体节点
        structure['relationships'].append({
            'from': relay_node['id'],
            'to': node['id'],
            'type': 'HAS_TERMINAL',
            'properties': {
                'group': node['properties'].get('contact_group', 
                         node['properties'].get('coil_group', 1))
            }
        })
    
    return structure

def parse_relay_model(device_id, terminals=None):
    """解析继电器型号
    Args:
        device_id: 设备ID，可以是简单形式如 "K1" 或完整形式如 "=A01+K1.H2-Q1"
        terminals: 可选的端子集合，用于特征分析
    Returns:
        tuple: (继电器类型, 配置字典)
    """
    # 解析完整设备标识符
    if any(c in device_id for c in ['=', '+', '.', '-']):
        device_info = parse_device_identifier(device_id)
        if device_info:
            device_id = device_info['device_id']
    
    # 如果提供了端子信息，使用特征分析
    if terminals is not None:
        config = create_relay_config_from_features(device_id, terminals)
        return config['type'], config

    # 否则使用原有的型号判断逻辑
    # 移除可能存在的设备位置前缀
    device_id = device_id.split('-')[-1]
    
    # 获取基本型号前缀
    if device_id.startswith('Q'):
        base_config = RELAY_CONFIGS["3RT"]
    elif device_id.startswith('K'):
        if len(device_id) > 2 and device_id[1:3].isdigit():
            number = int(device_id[1:3])
            # 根据编号范围判断继电器版本
            if number <= 10:
                base_config = RELAY_CONFIGS["K"]
            elif 11 <= number <= 30:
                base_config = RELAY_CONFIGS["RY"]["versions"]["standard"]
            elif 31 <= number <= 40:
                base_config = RELAY_CONFIGS["RY"]["versions"]["extended"]
            else:
                base_config = RELAY_CONFIGS["RY"]["versions"]["safety"]
        else:
            base_config = RELAY_CONFIGS["K"]
    else:
        # 默认使用标准继电器配置
        base_config = RELAY_CONFIGS["K"]
    
    # 复制配置，避免修改原始配置
    config = base_config.copy()
    
    # 确保配置中包含 'contacts' 字段
    if 'contacts' not in config:
        config['contacts'] = []
        
    return config["type"], config

def analyze_device_features(device_id, terminals):
    """分析设备的特征
    Args:
        device_id: 设备ID，如 "K1" 或完整形式如 "=A01+K1.H2-Q1"
        terminals: 设备的端子集合
    Returns:
        dict: 设备特征字典
    """
    features = {
        'terminal_count': len(terminals),
        'has_coil': any(t.startswith('A') for t in terminals),
        'contact_groups': {},
        'power_terminals': [t for t in terminals if t.startswith(('L', 'T'))],
        'diagnostic_terminals': [t for t in terminals if t.startswith('D')]
    }

    # 分析触点组
    for term in terminals:
        if term.isdigit() and len(term) == 2:
            group = int(term[0])
            type_num = int(term[1])
            if group not in features['contact_groups']:
                features['contact_groups'][group] = {}
            if type_num == 1:
                features['contact_groups'][group]['com'] = term
            elif type_num == 2:
                features['contact_groups'][group]['nc'] = term
            elif type_num == 4:
                features['contact_groups'][group]['no'] = term

    return features

def infer_relay_type(features):
    """根据设备特征推断继电器类型
    Args:
        features: 设备特征字典
    Returns:
        tuple: (继电器类型, 基本配置)
    """
    # 无线圈的设备判定为按钮类型
    if not features['has_coil']:
        if len(features['contact_groups']) > 2:
            return RelayType.BUTTON, RELAY_CONFIGS['S-MULTI'].copy()
        return RelayType.BUTTON, RELAY_CONFIGS['S'].copy()
    
    # 有功率端子的判定为接触器
    if features['power_terminals']:
        return RelayType.POWER_RELAY, RELAY_CONFIGS['3RT'].copy()
        
    # 根据触点组特征判断继电器类型
    contact_group_count = len(features['contact_groups'])
    if contact_group_count >= 4:
        # 多触点继电器
        return RelayType.SIGNAL_RELAY, RELAY_CONFIGS['RY']['versions']['extended'].copy()
    elif contact_group_count >= 2:
        # 标准继电器
        return RelayType.SIGNAL_RELAY, RELAY_CONFIGS['RY']['versions']['standard'].copy()
    else:
        # 基本继电器
        return RelayType.SIGNAL_RELAY, RELAY_CONFIGS['K'].copy()

def create_relay_config_from_features(device_id, terminals):
    """根据设备特征创建继电器配置
    Args:
        device_id: 设备ID
        terminals: 设备的端子集合
    Returns:
        dict: 继电器配置
    """
    # 分析设备特征
    features = analyze_device_features(device_id, terminals)
    
    # 推断继电器类型
    relay_type, base_config = infer_relay_type(features)
    
    # 更新配置中的触点信息
    config = base_config.copy()
    contacts = []
    
    for group, terminals in features['contact_groups'].items():
        if 'com' in terminals and 'nc' in terminals and 'no' in terminals:
            # 转换触点
            contacts.append({
                'type': ContactType.CO,
                'count': 1,
                'rating': '6A'
            })
        elif 'no' in terminals:
            # 常开触点
            contacts.append({
                'type': ContactType.NO,
                'count': 1,
                'rating': '6A'
            })
        elif 'nc' in terminals:
            # 常闭触点
            contacts.append({
                'type': ContactType.NC,
                'count': 1,
                'rating': '6A'
            })
    
    if contacts:
        config['contacts'] = contacts
    
    return config

class RelayCoil:
    """继电器线圈类"""
    def __init__(self, voltage, device_path, connections=None):
        self.voltage = voltage
        self.device_path = device_path  # 添加完整设备路径
        self.connections = connections or {
            create_terminal_id(device_path, 'A1'): None,
            create_terminal_id(device_path, 'A2'): None
        }
        self.state = 'de-energized'
        
    def calculate_voltage_difference(self):
        """计算线圈两端电压差"""
        a1_id = create_terminal_id(self.device_path, 'A1')
        a2_id = create_terminal_id(self.device_path, 'A2')
        if self.connections[a1_id] and self.connections[a2_id]:
            return abs(self.connections[a1_id].voltage - self.connections[a2_id].voltage)
        return 0

class RelayContact:
    """继电器触点类"""
    def __init__(self, contact_type, device_path, group_number=1):
        self.type = contact_type
        self.device_path = device_path  # 添加完整设备路径
        self.group = group_number
        self.state = 'open'
        self.connections = {}
        
    def get_terminal_id(self, terminal):
        """获取端子的完整标识符"""
        return create_terminal_id(self.device_path, terminal)
        
    def update_state(self, coil_energized):
        """根据线圈状态更新触点状态"""
        if self.type == ContactType.NO:
            self.state = 'closed' if coil_energized else 'open'
        elif self.type == ContactType.NC:
            self.state = 'open' if coil_energized else 'closed'

class Relay:
    """继电器类"""
    def __init__(self, device_id, config):
        # 解析设备标识符以获取完整路径
        device_info = parse_device_identifier(device_id) if any(c in device_id for c in ['=', '+', '.', '-']) else None
        self.device_path = device_info['device_path'] if device_info else device_id
        self.device_id = device_info['device_id'] if device_info else device_id
        self.config = config
        self.coil = RelayCoil(config['coil_voltage'], self.device_path)
        self.contacts = {}
        self._initialize_contacts()
        
    def _initialize_contacts(self):
        """初始化触点组"""
        for contact_config in self.config['contacts']:
            for i in range(contact_config['count']):
                group_number = i + 1
                if contact_config['type'] == ContactType.CO:
                    # 创建一组转换触点（COM-NO-NC）
                    self.contacts[f'{group_number}'] = {
                        'COM': RelayContact(ContactType.CO, self.device_path, group_number),
                        'NO': RelayContact(ContactType.NO, self.device_path, group_number),
                        'NC': RelayContact(ContactType.NC, self.device_path, group_number)
                    }
                else:
                    # 创建单个触点
                    self.contacts[f'{group_number}'] = {
                        'MAIN': RelayContact(contact_config['type'], self.device_path, group_number)
                    }
                    
    def get_terminal_id(self, terminal):
        """获取端子的完整标识符"""
        return create_terminal_id(self.device_path, terminal)
        
    def energize(self):
        """励磁线圈"""
        voltage_diff = self.coil.calculate_voltage_difference()
        if voltage_diff >= float(self.config['coil_voltage'].replace('VDC', '')):
            self.coil.state = 'energized'
            self._update_all_contacts()
            
    def de_energize(self):
        """断开线圈"""
        self.coil.state = 'de-energized'
        self._update_all_contacts()
        
    def _update_all_contacts(self):
        """更新所有触点状态"""
        is_energized = (self.coil.state == 'energized')
        for contact_group in self.contacts.values():
            for contact in contact_group.values():
                contact.update_state(is_energized)
                
    def get_terminal_properties(self, terminal_id):
        """获取特定端子的属性"""
        properties = get_terminal_properties(self.device_path, terminal_id)
        
        # 添加运行时状态
        if terminal_id.startswith('A'):
            # 线圈端子
            properties.update({
                'coil_state': self.coil.state,
                'voltage': self.coil.connections.get(self.get_terminal_id(terminal_id), 0.0)
            })
        else:
            # 触点端子
            for group in self.contacts.values():
                for contact in group.values():
                    if contact.get_terminal_id(terminal_id) in contact.connections:
                        properties.update({
                            'contact_state': contact.state,
                            'last_update': contact.last_update if hasattr(contact, 'last_update') else None
                        })
                        break
                        
        return properties

def get_contact_properties(terminal_id, relay_config):
    """获取触点属性
    Args:
        terminal_id: 端子ID，如 "13", "14", "21", "22", "D1", "D2" 等
        relay_config: 继电器配置字典
    Returns:
        dict: 触点属性字典
    """
    properties = {
        "terminal_type": "contact",
        "state": "open"
    }
    
    # 处理特殊端子号（如D1, D2等）
    if terminal_id.startswith('D'):
        try:
            contact_group = 1  # 默认为第一组
            contact_number = int(terminal_id[1:])  # 提取D后面的数字
            properties.update({
                "contact_role": "NO",
                "contact_type": ContactType.NO,
                "special_terminal": "diagnostic",
                "contact_group": contact_group,
                "is_connection": True  # 标记为连接点
            })
            return properties
        except ValueError:
            properties.update({
                "contact_role": "UNKNOWN",
                "contact_type": ContactType.NO,
                "is_connection": True
            })
            return properties
    
    try:
        # 解析标准端子号（如13, 14等）
        contact_group = int(terminal_id[0])  # 第一个数字表示触点组
        contact_type = int(terminal_id[1])   # 第二个数字表示触点类型
        
        # 添加触点角色和连接点标记
        properties.update({
            "contact_group": contact_group,
            "is_connection": True
        })
        
        if contact_type == 1:
            properties["contact_role"] = "COM"
        elif contact_type == 2:
            properties["contact_role"] = "NC"
        elif contact_type == 4:
            properties["contact_role"] = "NO"
            
        # 获取触点配置
        for contact_config in relay_config["contacts"]:
            if contact_group <= contact_config["count"]:
                properties["contact_type"] = contact_config["type"]
                properties["rating"] = contact_config["rating"]
                break
                
    except (ValueError, IndexError):
        properties.update({
            "contact_role": "UNKNOWN",
            "contact_type": ContactType.NO,
            "contact_group": 1,
            "is_connection": True
        })
        
    return properties

def get_coil_properties(terminal_id, relay_config):
    """获取线圈属性
    Args:
        terminal_id: 端子ID，如 "A1", "A2" 等
        relay_config: 继电器配置字典
    Returns:
        dict: 线圈属性字典
    """
    properties = {
        "terminal_type": "coil",
        "coil_voltage": relay_config["coil_voltage"],
        "is_connection": True  # 标记为连接点
    }
    
    # 添加极性
    if terminal_id == "A1":
        properties["polarity"] = "positive"
    elif terminal_id == "A2":
        properties["polarity"] = "negative"
        
    # 添加时间继电器特有属性
    if relay_config["type"] == RelayType.TIME_RELAY:
        properties["timing"] = relay_config["timing"]
        
    return properties

def parse_device_identifier(full_identifier):
    """解析完整的设备标识符
    Args:
        full_identifier: 完整设备标识符，如 "=A01+K1.H2-Q1:D2"
    Returns:
        dict: 解析后的设备信息，包含：
            - device_path: 设备路径 (=A01+K1.H2-Q1)
            - location: 位置标识 (A01)
            - device_id: 设备ID (K1)
            - sub_terminal: 子端子 (H2)
            - reference: 引用设备 (Q1)
            - terminal: 端子号 (D2)
    """
    parts = {}
    try:
        # 先分离端子号
        main_part, *terminal_part = full_identifier.split(':')
        parts['terminal'] = terminal_part[0] if terminal_part else None
        
        # 处理主要部分
        if (main_part.startswith('=')):
            main_part = main_part[1:]
            
        # 分解位置和设备部分
        location, rest = main_part.split('+', 1) if '+' in main_part else (None, main_part)
        parts['location'] = location
        
        # 分解设备ID和子端子
        if '.' in rest:
            device_id, sub_rest = rest.split('.', 1)
            parts['device_id'] = device_id
            
            # 处理引用部分
            if '-' in sub_rest:
                sub_terminal, reference = sub_rest.split('-', 1)
            else:
                sub_terminal, reference = sub_rest, None
            
            parts['sub_terminal'] = sub_terminal
            parts['reference'] = reference
        else:
            parts['device_id'] = rest
            parts['sub_terminal'] = None
            parts['reference'] = None
            
        # 构建设备路径
        parts['device_path'] = f"={'=' + location if location else ''}"
        if parts['device_id']:
            parts['device_path'] += f"+{parts['device_id']}"
        if parts['sub_terminal']:
            parts['device_path'] += f".{parts['sub_terminal']}"
        if parts['reference']:
            parts['device_path'] += f"-{parts['reference']}"
            
    except Exception as e:
        print(f"解析设备标识符失败: {str(e)}")
        return None
        
    return parts

def analyze_terminal(device_id, terminal_id):
    """分析端子类型和属性
    Args:
        device_id: 设备ID，如 "K1" 或完整形式如 "=A01+K1.H2-Q1"
        terminal_id: 端子ID，如 "A1" 或带子端子的形式如 "P2:1"
    Returns:
        tuple: (端子类型, 属性字典)
    """
    # 解析完整设备标识符
    device_info = None
    if any(c in device_id for c in ['=', '+', '.', '-']):
        validator = DevicePathValidator()
        device_info = validator.extract_device_info(device_id)
        if device_info:
            device_id = device_info['device_id']  # 使用基本设备ID进行配置查找
    
    # 处理带有子端子的端子ID
    terminal_parts = terminal_id.split(':') if ':' in terminal_id else [terminal_id]
    base_terminal = terminal_parts[0]
    sub_terminals = terminal_parts[1:] if len(terminal_parts) > 1 else []
    
    # 基本属性
    properties = {
        "terminal": terminal_id,
        "base_terminal": base_terminal,
        "sub_terminals": sub_terminals,
        "is_connection": True,
        "type": "generic"  # 添加默认类型
    }
    
    # 如果有完整的设备信息，添加到属性中
    if device_info:
        properties.update({
            "device_path": device_info.get('normalized_path'),
            "location": device_info.get('location'),
            "sub_terminal": device_info.get('sub_terminal'),
            "reference": device_info.get('reference'),
            "sub_references": device_info.get('sub_references', [])
        })

    # 判断端子类型
    if base_terminal.startswith('P'):
        # 处理连接器端子
        properties.update({
            "type": "connector",
            "terminal_type": "connector",
            "role": "pin",
            "connector_type": "terminal_block",
            "pin_number": sub_terminals[0] if sub_terminals else None
        })
        return "ConnectorTerminal", properties
        
    # 获取继电器配置（如果是继电器设备）
    if device_id.startswith(('K', 'Q')):
        relay_type, config = parse_relay_model(device_id)
        
        # 解析端子基本属性
        terminal_props = parse_terminal_id(base_terminal)
        properties["type"] = terminal_props['type']
        properties["terminal_type"] = terminal_props['type']
        
        # 根据端子类型处理
        if terminal_props['type'] == RelayTerminalType.POWER_IN:
            properties.update({
                "role": "power_input",
                "phase": terminal_props.get('phase'),
                "state": "open"
            })
            if 'power_poles' in config:
                properties["rating"] = config['power_poles']['rating']
            return "PowerTerminal", properties
            
        elif terminal_props['type'] == RelayTerminalType.POWER_OUT:
            properties.update({
                "role": "power_output",
                "phase": terminal_props.get('phase'),
                "state": "open"
            })
            if 'power_poles' in config:
                properties["rating"] = config['power_poles']['rating']
            return "PowerTerminal", properties
            
        elif terminal_props['type'] == RelayTerminalType.COIL:
            properties.update({
                "role": terminal_props.get('role', 'coil'),
                "coil_voltage": config["coil_voltage"],
                "polarity": "positive" if terminal_props.get('role') == RelayTerminalRole.COIL_PLUS else "negative"
            })
            return "RelayCoilTerm", properties
            
        elif terminal_props['type'] == RelayTerminalType.CONTACT:
            properties.update({
                "role": terminal_props.get('role', 'auxiliary'),
                "state": "open" if terminal_props.get('role') == RelayTerminalRole.NO else "closed",
                "contact_role": terminal_props.get('role'),
                "contact_group": terminal_props.get('group', 1)
            })
            return "RelayContactTerm", properties
            
    # 处理其他类型的设备端子
    if device_id.startswith('W'):
        # 导线端子
        properties.update({
            "type": "wire",
            "terminal_type": "wire",
            "role": "conductor",
            "conductor_type": "signal"
        })
        return "WireTerminal", properties
        
    # 默认属性
    properties.update({
        "type": "generic",
        "terminal_type": "generic",
        "role": "connection",
        "state": "unknown"
    })
    return "Terminal", properties

class PowerPoleType:
    """电源极类型"""
    L1 = "L1"  # 第一相输入
    L2 = "L2"  # 第二相输入
    L3 = "L3"  # 第三相输入
    T1 = "T1"  # 第一相输出
    T2 = "T2"  # 第二相输出
    T3 = "T3"  # 第三相输出

def parse_terminal_id(terminal_id):
    """解析端子ID
    Args:
        terminal_id: 端子ID，如 "L1", "T1", "13", "14", "A1" 等
    Returns:
        dict: 端子属性字典
    """
    # 电源端子映射
    POWER_TERMINAL_MAPPING = {
        'L1': {'type': RelayTerminalType.POWER_IN, 'role': RelayTerminalRole.LINE, 'phase': 1},
        'L2': {'type': RelayTerminalType.POWER_IN, 'role': RelayTerminalRole.LINE, 'phase': 2},
        'L3': {'type': RelayTerminalType.POWER_IN, 'role': RelayTerminalRole.LINE, 'phase': 3},
        'T1': {'type': RelayTerminalType.POWER_OUT, 'role': RelayTerminalRole.LINE, 'phase': 1},
        'T2': {'type': RelayTerminalType.POWER_OUT, 'role': RelayTerminalRole.LINE, 'phase': 2},
        'T3': {'type': RelayTerminalType.POWER_OUT, 'role': RelayTerminalRole.LINE, 'phase': 3},
    }
    
    # 触点端子映射
    CONTACT_TERMINAL_MAPPING = {
        '1': RelayTerminalRole.COM,
        '2': RelayTerminalRole.NC,
        '4': RelayTerminalRole.NO
    }
    
    # 线圈端子映射
    COIL_TERMINAL_MAPPING = {
        'A1': {'type': RelayTerminalType.COIL, 'role': RelayTerminalRole.COIL_PLUS},
        'A2': {'type': RelayTerminalType.COIL, 'role': RelayTerminalRole.COIL_MINUS}
    }
    
    # 诊断端子映射
    DIAGNOSTIC_TERMINAL_MAPPING = {
        'D1': {'type': RelayTerminalType.DIAGNOSTIC, 'role': RelayTerminalRole.DIAGNOSTIC},
        'D2': {'type': RelayTerminalType.DIAGNOSTIC, 'role': RelayTerminalRole.DIAGNOSTIC}
    }
    
    # 解析端子ID
    if terminal_id in POWER_TERMINAL_MAPPING:
        return POWER_TERMINAL_MAPPING[terminal_id]
    elif terminal_id in COIL_TERMINAL_MAPPING:
        return COIL_TERMINAL_MAPPING[terminal_id]
    elif terminal_id in DIAGNOSTIC_TERMINAL_MAPPING:
        return DIAGNOSTIC_TERMINAL_MAPPING[terminal_id]
    elif len(terminal_id) == 2 and terminal_id[0] in CONTACT_TERMINAL_MAPPING:
        return {
            'type': RelayTerminalType.CONTACT,
            'role': CONTACT_TERMINAL_MAPPING[terminal_id[0]],
            'group': int(terminal_id[1])
        }
    else:
        return {
            'type': RelayTerminalType.CONTACT,
            'role': RelayTerminalRole.AUXILIARY
        }

class RelayCoilType:
    """线圈类型定义"""
    STANDARD = "STANDARD"    # 标准线圈 (A1-A2)
    DUAL = "DUAL"           # 双线圈 (A11-A12, A21-A22)
    ELECTRONIC = "ELECTRONIC" # 电子式 (A1-A2 + B1-B2)

def parse_coil_terminals(terminal_id):
    """解析线圈端子配置
    Args:
        terminal_id: 端子ID，如 "A1", "A11" 等
    Returns:
        dict: 线圈端子属性
    """
    coil_props = {
        'type': RelayTerminalType.COIL,
        'coil_type': RelayCoilType.STANDARD,
        'group': 1,
        'polarity': None
    }
    
    if not terminal_id.startswith('A'):
        return None
        
    # 处理不同形式的线圈端子
    if len(terminal_id) == 2:  # A1, A2
        num = int(terminal_id[1])
        coil_props.update({
            'polarity': 'positive' if num == 1 else 'negative',
            'terminal_number': num
        })
    elif len(terminal_id) == 3:  # A11, A12, A21, A22
        group = int(terminal_id[1])
        num = int(terminal_id[2])
        coil_props.update({
            'coil_type': RelayCoilType.DUAL,
            'group': group,
            'polarity': 'positive' if num == 1 else 'negative',
            'terminal_number': num
        })
    
    return coil_props

def parse_power_terminals(terminal_id):
    """解析功率端子配置
    Args:
        terminal_id: 端子ID，如 "L1", "T1" 等
    Returns:
        dict: 功率端子属性
    """
    if not (terminal_id.startswith('L') or terminal_id.startswith('T')):
        return None
        
    try:
        phase = int(terminal_id[1])
        return {
            'type': RelayTerminalType.POWER_IN if terminal_id.startswith('L') else RelayTerminalType.POWER_OUT,
            'role': RelayTerminalRole.LINE,
            'phase': phase,
            'terminal_number': phase
        }
    except (ValueError, IndexError):
        return None

def parse_contact_terminals(terminal_id):
    """解析触点端子配置
    Args:
        terminal_id: 端子ID，如 "11", "12", "14" 等
    Returns:
        dict: 触点端子属性
    """
    if not terminal_id.isdigit() or len(terminal_id) != 2:
        return None
        
    try:
        group = int(terminal_id[0])
        contact_type = int(terminal_id[1])
        
        # 标准触点编号规则：
        # x1: COM (公共端)
        # x2: NC (常闭端)
        # x4: NO (常开端)
        role_mapping = {
            1: RelayTerminalRole.COM,
            2: RelayTerminalRole.NC,
            4: RelayTerminalRole.NO
        }
        
        return {
            'type': RelayTerminalType.CONTACT,
            'role': role_mapping.get(contact_type, RelayTerminalRole.AUXILIARY),
            'group': group,
            'terminal_number': contact_type,
            'default_state': 'closed' if contact_type == 2 else 'open'
        }
    except (ValueError, IndexError):
        return None

def parse_terminal_id(terminal_id):
    """解析端子ID
    Args:
        terminal_id: 端子ID，如 "L1", "T1", "11", "14", "A1" 等
    Returns:
        dict: 端子属性字典
    """
    # 按优先级尝试不同的解析方式
    for parser in [parse_coil_terminals, parse_power_terminals, parse_contact_terminals]:
        result = parser(terminal_id)
        if result is not None:
            return result
            
    # 处理特殊端子（如诊断端子）
    if terminal_id.startswith('D'):
        try:
            number = int(terminal_id[1:])
            return {
                'type': RelayTerminalType.DIAGNOSTIC,
                'role': RelayTerminalRole.DIAGNOSTIC,
                'terminal_number': number
            }
        except ValueError:
            pass
            
    # 返回默认配置
    return {
        'type': RelayTerminalType.CONTACT,
        'role': RelayTerminalRole.AUXILIARY,
        'terminal_number': 0
    }

def get_terminal_voltage_state(terminal_type, terminal_role, coil_energized=False):
    """获取端子的电压状态
    Args:
        terminal_type: 端子类型（RelayTerminalType）
        terminal_role: 端子角色（RelayTerminalRole）
        coil_energized: 线圈是否励磁
    Returns:
        dict: 端子状态信息
    """
    if terminal_type == RelayTerminalType.COIL:
        return {
            'state': 'energized' if coil_energized else 'de-energized',
            'conducting': coil_energized
        }
    elif terminal_type == RelayTerminalType.CONTACT:
        if terminal_role == RelayTerminalRole.NC:
            return {
                'state': 'open' if coil_energized else 'closed',
                'conducting': not coil_energized
            }
        elif terminal_role == RelayTerminalRole.NO:
            return {
                'state': 'closed' if coil_energized else 'open',
                'conducting': coil_energized
            }
        elif terminal_role == RelayTerminalRole.COM:
            return {
                'state': 'connected',
                'conducting': True
            }
    elif terminal_type in [RelayTerminalType.POWER_IN, RelayTerminalType.POWER_OUT]:
        return {
            'state': 'connected',
            'conducting': True
        }
            
    return {
        'state': 'unknown',
        'conducting': False
    }

def validate_device_paths_match(source_path, target_path):
    """验证两个设备路径是否属于同一个继电器
    Args:
        source_path: 源设备路径，如 "=A01+K1.H2-Q1"
        target_path: 目标设备路径，如 "=A01+K1.H2-Q1"
    Returns:
        bool: 是否匹配
    """
    if not (source_path and target_path):
        return False
        
    # 去除端子部分进行比较
    source_base = source_path.split(':')[0] if ':' in source_path else source_path
    target_base = target_path.split(':')[0] if ':' in target_path else target_path
    
    return source_base == target_base

def create_relay_connection(source_device, target_device, connection_type, properties=None):
    """创建继电器连接关系
    Args:
        source_device: 源设备完整标识符，如 "=A02+K1.B1-K20:34"
        target_device: 目标设备完整标识符，如 "=A01+K1.H2-K1:A1"
        connection_type: 连接类型
        properties: 连接属性
    Returns:
        dict: 关系配置
    """
    # 解析设备信息
    validator = DevicePathValidator()
    source_info = validator.extract_device_info(source_device)
    target_info = validator.extract_device_info(target_device)
    
    if not (source_info and target_info):
        raise ValueError("设备标识符解析失败")
        
    # 验证连接有效性
    is_valid, message = validate_relay_connection(source_device, target_device)
    if not is_valid:
        raise ValueError(f"无效的连接: {message}")
    
    # 确定连接类型
    if source_info['sub_terminal'] and source_info['sub_terminal'].startswith('B'):
        connection_type = 'CONTROL_CONNECTION'
    elif target_info['sub_terminal'] and target_info['sub_terminal'].startswith('H'):
        connection_type = 'AUXILIARY_CONNECTION'
    elif source_info['terminal'].startswith('A') or target_info['terminal'].startswith('A'):
        connection_type = 'COIL_CONNECTION'
    elif source_info['terminal'].isdigit() and target_info['terminal'].isdigit():
        connection_type = 'CONTACT_CONNECTION'
    else:
        connection_type = 'GENERIC_CONNECTION'
    
    # 基本关系属性
    relationship = {
        'from': source_device,
        'to': target_device,
        'type': connection_type,
        'properties': {
            'source_path': source_info['normalized_path'],
            'target_path': target_info['normalized_path'],
            'source_terminal': source_info['terminal'],
            'target_terminal': target_info['terminal'],
            'source_location': source_info['location'],
            'target_location': target_info['location'],
            'source_device_id': source_info['device_id'],
            'target_device_id': target_info['device_id'],
            'connection_type': connection_type
        }
    }
    
    # 添加特殊端子信息
    if source_info['sub_terminal']:
        relationship['properties']['source_sub_terminal'] = source_info['sub_terminal']
    if target_info['sub_terminal']:
        relationship['properties']['target_sub_terminal'] = target_info['sub_terminal']
    
    # 添加设备引用信息
    if source_info['reference']:
        relationship['properties']['source_reference'] = source_info['reference']
    if target_info['reference']:
        relationship['properties']['target_reference'] = target_info['reference']
    
    # 添加其他传入的属性
    if properties:
        relationship['properties'].update(properties)
    
    return relationship

def create_internal_relay_connections(device_path, config):
    """创建继电器内部连接
    Args:
        device_path: 设备完整路径
        config: 继电器配置
    Returns:
        list: 内部连接列表
    """
    connections = []
    
    # 创建线圈内部连接
    coil_terminals = ['A1', 'A2']
    if config['type'] == RelayType.TIME_RELAY:
        coil_terminals.append('B1')
        
    for i in range(len(coil_terminals)-1):
        connections.append(create_relay_connection(
            create_terminal_id(device_path, coil_terminals[i]),
            create_terminal_id(device_path, coil_terminals[i+1]),
            'INTERNAL_CONNECTION',
            {'connection_type': 'COIL_CIRCUIT'}
        ))
    
    # 创建触点内部连接
    if 'contacts' in config:
        for contact_config in config['contacts']:
            for i in range(contact_config['count']):
                group = i + 1
                # 根据触点类型创建连接
                if contact_config['type'] == ContactType.CO:
                    # 转换触点的内部连接 (COM-NC, COM-NO)
                    com_terminal = create_terminal_id(device_path, f"{group}1")
                    nc_terminal = create_terminal_id(device_path, f"{group}2")
                    no_terminal = create_terminal_id(device_path, f"{group}4")
                    
                    connections.extend([
                        create_relay_connection(
                            com_terminal, nc_terminal,
                            'INTERNAL_CONNECTION',
                            {'connection_type': 'CONTACT_NC', 'contact_group': group}
                        ),
                        create_relay_connection(
                            com_terminal, no_terminal,
                            'INTERNAL_CONNECTION',
                            {'connection_type': 'CONTACT_NO', 'contact_group': group}
                        )
                    ])
                    
    return connections

class DevicePathValidator:
    """设备路径验证器"""
    
    @staticmethod
    def parse_reference_part(reference_str):
        """解析引用部分
        Args:
            reference_str: 引用字符串，如 "W5(-P2)"
        Returns:
            dict: 解析后的引用信息
        """
        references = []
        current_ref = ""
        nested_level = 0
        
        for char in reference_str:
            if char == '(':
                if nested_level > 0:
                    current_ref += char
                nested_level += 1
            elif char == ')':
                nested_level -= 1
                if nested_level > 0:
                    current_ref += char
                elif nested_level == 0 and current_ref:
                    references.append(current_ref)
                    current_ref = ""
            else:
                current_ref += char
                
        if current_ref:
            references.append(current_ref)
            
        return {
            'main_reference': references[0] if references else None,
            'sub_references': references[1:] if len(references) > 1 else []
        }
    
    @staticmethod
    def parse_terminal_part(terminal_str):
        """解析端子部分
        Args:
            terminal_str: 端子字符串，如 "P2:1"
        Returns:
            dict: 解析后的端子信息
        """
        parts = terminal_str.split(':')
        return {
            'main_terminal': parts[0],
            'sub_terminals': parts[1:] if len(parts) > 1 else []
        }

    @staticmethod
    def extract_device_info(path):
        """从设备路径中提取设备信息
        Args:
            path: 设备路径，如 "=A02+K1.B1-W5(-P2):P2:1"
        Returns:
            dict: 设备信息字典
        """
        try:
            # 处理基本部分和端子部分
            if ':' in path:
                base_path, *terminal_parts = path.split(':')
                terminal_info = DevicePathValidator.parse_terminal_part(':'.join(terminal_parts))
            else:
                base_path = path
                terminal_info = {'main_terminal': None, 'sub_terminals': []}
            
            # 移除前导等号
            if base_path.startswith('='):
                base_path = base_path[1:]
                
            # 分解位置和设备部分
            location, device_part = base_path.split('+')
            
            # 处理设备部分
            if '.' in device_part:
                device_id, remaining = device_part.split('.', 1)
            else:
                device_id = device_part
                remaining = None
                
            # 处理子端子和引用
            sub_terminal = None
            reference_info = {'main_reference': None, 'sub_references': []}
            
            if remaining:
                if '-' in remaining:
                    sub_term, ref_part = remaining.split('-', 1)
                    sub_terminal = sub_term
                    reference_info = DevicePathValidator.parse_reference_part(ref_part)
                else:
                    sub_terminal = remaining
            
            return {
                'location': location,
                'device_id': device_id,
                'sub_terminal': sub_terminal,
                'reference': reference_info['main_reference'],
                'sub_references': reference_info['sub_references'],
                'terminal': terminal_info['main_terminal'],
                'sub_terminals': terminal_info['sub_terminals'],
                'original_path': path,
                'normalized_path': f"{location}+{device_id}"
            }
            
        except Exception as e:
            raise ValueError(f"无法解析设备路径 '{path}': {str(e)}")
            
    @staticmethod
    def validate_device_path_format(path):
        """验证设备路径格式是否正确"""
        try:
            if not path:
                return False, "设备路径不能为空"
                
            # 检查基本格式
            if not any(c in path for c in ['=', '+']):
                return False, "设备路径必须包含 '=' 和 '+'"
                
            # 提取并验证各个部分
            info = DevicePathValidator.extract_device_info(path)
            
            # 验证位置格式
            if not info['location'].startswith('A'):
                return False, f"无效的位置标识: {info['location']}"
                
            # 验证设备ID格式 - 扩展支持的设备类型
            valid_device_prefixes = ('K', 'Q', 'W', 'P', 'S')
            if not any(info['device_id'].startswith(prefix) for prefix in valid_device_prefixes):
                return False, f"无效的设备ID: {info['device_id']}"
                
            # 如果有子端子，验证格式（扩展支持的端子类型）
            if info['sub_terminal']:
                valid_terminal_prefixes = ('H', 'B', 'D', 'P')
                if not any(info['sub_terminal'].startswith(prefix) for prefix in valid_terminal_prefixes):
                    return False, f"无效的子端子标识: {info['sub_terminal']}"
                    
            # 如果有引用设备，验证格式
            if info['reference']:
                if not any(info['reference'].startswith(prefix) for prefix in valid_device_prefixes):
                    return False, f"无效的引用设备ID: {info['reference']}"
                    
            return True, ""
        except ValueError as e:
            return False, str(e)
            
    @staticmethod
    def normalize_device_path(path):
        """标准化设备路径格式
        Args:
            path: 设备路径，如 "=A01+K1.H2-Q1" 或 "=A01+K1.H2-Q1:A1"
        Returns:
            str: 标准化的设备路径（移除端子部分）
        """
        # 移除前导等号（如果存在）
        if path.startswith('='):
            path = path[1:]
            
        # 移除端子部分（如果存在）
        base_path = path.split(':')[0]
        
        # 确保路径格式正确
        parts = base_path.split('+')
        if len(parts) != 2:
            raise ValueError(f"无效的设备路径格式: {path}")
            
        location = parts[0]
        device_part = parts[1]
        
        # 处理设备部分
        device_parts = device_part.split('.')
        if len(device_parts) > 1:
            device_id = device_parts[0]
            sub_parts = device_parts[1].split('-')
            sub_terminal = sub_parts[0]
            reference = sub_parts[1] if len(sub_parts) > 1 else None
            
            # 重建标准化路径
            if reference:
                return f"{location}+{device_id}.{sub_terminal}-{reference}"
            else:
                return f"{location}+{device_id}.{sub_terminal}"
        else:
            return f"{location}+{device_part}"
    
    @staticmethod
    def is_same_device(path1, path2):
        """判断两个路径是否指向同一个设备
        Args:
            path1: 第一个设备路径
            path2: 第二个设备路径
        Returns:
            bool: 是否是同一个设备
        """
        try:
            norm1 = DevicePathValidator.normalize_device_path(path1)
            norm2 = DevicePathValidator.normalize_device_path(path2)
            return norm1 == norm2
        except ValueError:
            return False
            
    @staticmethod
    def validate_connection(source_path, target_path, expected_same_device=False):
        """验证连接的有效性
        Args:
            source_path: 源设备路径
            target_path: 目标设备路径
            expected_same_device: 是否期望为同一设备的连接
        Returns:
            tuple: (是否有效, 错误信息)
        """
        try:
            is_same = DevicePathValidator.is_same_device(source_path, target_path)
            
            if expected_same_device and not is_same:
                return False, "内部连接必须在同一个设备内"
            elif not expected_same_device and is_same:
                return False, "外部连接不能在同一个设备内"
                
            return True, ""
        except ValueError as e:
            return False, str(e)
            
    @staticmethod
    def extract_device_info(path):
        """从设备路径中提取设备信息
        Args:
            path: 设备路径
        Returns:
            dict: 设备信息字典
        """
        try:
            # 处理端子部分
            base_path, *terminal_part = path.split(':')
            terminal = terminal_part[0] if terminal_part else None
            
            # 移除前导等号
            if base_path.startswith('='):
                base_path = base_path[1:]
                
            # 分解位置和设备部分
            location, device_part = base_path.split('+')
            
            # 处理设备部分
            device_parts = device_part.split('.')
            device_id = device_parts[0]
            
            if len(device_parts) > 1:
                sub_parts = device_parts[1].split('-')
                sub_terminal = sub_parts[0]
                reference = sub_parts[1] if len(sub_parts) > 1 else None
            else:
                sub_terminal = None
                reference = None
                
            return {
                'location': location,
                'device_id': device_id,
                'sub_terminal': sub_terminal,
                'reference': reference,
                'terminal': terminal,
                'original_path': path,
                'normalized_path': DevicePathValidator.normalize_device_path(base_path)
            }
        except Exception as e:
            raise ValueError(f"无法解析设备路径 '{path}': {str(e)}")
            
    @staticmethod
    def validate_device_path_format(path):
        """验证设备路径格式是否正确
        Args:
            path: 设备路径
        Returns:
            tuple: (是否有效, 错误信息)
        """
        try:
            if not path:
                return False, "设备路径不能为空"
                
            # 检查基本格式
            if not any(c in path for c in ['=', '+']):
                return False, "设备路径必须包含 '=' 和 '+'"
                
            # 提取并验证各个部分
            info = DevicePathValidator.extract_device_info(path)
            
            # 验证位置格式
            if not info['location'].startswith('A'):
                return False, f"无效的位置标识: {info['location']}"
                
            # 验证设备ID格式
            if not info['device_id'].startswith(('K', 'Q')):
                return False, f"无效的设备ID: {info['device_id']}"
                
            # 如果有子端子，验证格式
            if info['sub_terminal']:
                if not info['sub_terminal'].startswith(('H', 'B', 'D')):
                    return False, f"无效的子端子标识: {info['sub_terminal']}"
                    
            # 如果有引用设备，验证格式
            if info['reference']:
                if not info['reference'].startswith(('K', 'Q')):
                    return False, f"无效的引用设备ID: {info['reference']}"
                    
            return True, ""
        except ValueError as e:
            return False, str(e)
            
    @staticmethod
    def validate_device_paths_match(source_path, target_path):
        """验证两个设备路径是否属于同一个继电器
        Args:
            source_path: 源设备路径，如 "=A01+K1.H2-Q1"
            target_path: 目标设备路径，如 "=A01+K1.H2-Q1"
        Returns:
            bool: 是否匹配
        """
        if not (source_path and target_path):
            return False
            
        # 去除端子部分进行比较
        source_base = source_path.split(':')[0] if ':' in source_path else source_path
        target_base = target_path.split(':')[0] if ':' in target_path else target_path
        
        return source_base == target_base

def validate_connection_between_relays(source_info, target_info):
    """验证两个继电器之间的连接有效性
    Args:
        source_info: 源设备信息字典
        target_info: 目标设备信息字典
    Returns:
        tuple: (是否有效, 错误消息)
    """
    # 检查基本设备ID（不包含引用部分）
    source_base_device = source_info['device_id']
    target_base_device = target_info['device_id']
    
    # 获取引用的设备ID（如果存在）
    source_ref = source_info.get('reference')
    target_ref = target_info.get('reference')
    
    # 验证主设备和引用设备的关系
    if source_ref == target_base_device or target_ref == source_base_device:
        return True, "设备引用关系正确"
        
    return False, "设备之间没有有效的引用关系"

def validate_relay_connection(source_device, target_device):
    """验证继电器连接的有效性
    Args:
        source_device: 源设备完整标识符，如 "=A02+K1.B1-K20:34"
        target_device: 目标设备完整标识符，如 "=A01+K1.H2-K1:A1"
    Returns:
        tuple: (是否有效, 错误消息)
    """
    validator = DevicePathValidator()
    
    # 解析设备信息
    source_info = validator.extract_device_info(source_device)
    if not source_info:
        return False, f"无法解析源设备标识符: {source_device}"
        
    target_info = validator.extract_device_info(target_device)
    if not target_info:
        return False, f"无法解析目标设备标识符: {target_device}"
    
    # 验证设备引用关系
    is_valid, message = validate_connection_between_relays(source_info, target_info)
    if not is_valid:
        return False, message
    
    # 验证端子组合的有效性
    source_terminal = source_info['terminal']
    target_terminal = target_info['terminal']
    
    if source_terminal and target_terminal:
        # 特殊端子与常规端子的连接规则
        if source_info['sub_terminal'] and source_info['sub_terminal'].startswith('B'):
            # B1端子可以连接到其他继电器的线圈端子
            if not target_terminal.startswith('A'):
                return False, "B1端子只能连接到线圈端子"
        elif target_info['sub_terminal'] and target_info['sub_terminal'].startswith('H'):
            # H2端子可以连接到其他继电器的线圈端子
            if not source_terminal.isdigit():  # 源端必须是触点端子
                return False, "H2端子必须从触点端子连接"
    
    return True, "连接有效"

def analyze_relay_connection(source_device, target_device):
    """分析继电器连接类型和属性
    Args:
        source_device: 源设备完整标识符
        target_device: 目标设备完整标识符
    Returns:
        dict: 连接分析结果
    """
    validator = DevicePathValidator()
    source_info = validator.extract_device_info(source_device)
    target_info = validator.extract_device_info(target_device)
    
    result = {
        'source_path': source_info['normalized_path'],
        'target_path': target_info['normalized_path'],
        'source_terminal': source_info['terminal'],
        'target_terminal': target_info['terminal'],
        'is_same_device': validator.is_same_device(
            source_info['normalized_path'],
            target_info['normalized_path']
        )
    }
    
    # 确定连接类型
    if source_info['terminal'].startswith('A') or target_info['terminal'].startswith('A'):
        result['connection_type'] = 'COIL_CONNECTION'
    elif source_info['terminal'].isdigit() and target_info['terminal'].isdigit():
        result['connection_type'] = 'CONTACT_CONNECTION'
    elif source_info['terminal'].startswith('H') or target_info['terminal'].startswith('H'):
        result['connection_type'] = 'AUXILIARY_CONNECTION'
    else:
        result['connection_type'] = 'UNKNOWN_CONNECTION'
    
    # 添加连接属性
    result['properties'] = {
        'source_location': source_info['location'],
        'target_location': target_info['location'],
        'source_device': source_info['device_id'],
        'target_device': target_info['device_id']
    }
    
    # 如果有子端子或引用信息，也添加到属性中
    if source_info['sub_terminal']:
        result['properties']['source_sub_terminal'] = source_info['sub_terminal']
    if source_info['reference']:
        result['properties']['source_reference'] = source_info['reference']
    if target_info['sub_terminal']:
        result['properties']['target_sub_terminal'] = target_info['sub_terminal']
    if target_info['reference']:
        result['properties']['target_reference'] = target_info['reference']
        
    return result

def extract_relay_info(device_path):
    """从完整设备路径中提取继电器信息
    Args:
        device_path: 完整的设备路径，如 "=A02+K1.B1-K20:34"
    Returns:
        dict: 继电器信息，包含：
            - relay_path: 继电器本体路径 (=A02+K1)
            - special_terminal: 特殊端子 (B1)
            - reference: 引用设备 (K20)
            - terminal: 端子号 (34)
    """
    info = {
        'relay_path': None,
        'special_terminal': None,
        'reference': None,
        'terminal': None
    }
    
    try:
        # 去掉前导的等号
        if device_path.startswith('='):
            device_path = device_path[1:]
            
        # 分离端子部分
        base_path, *terminal_part = device_path.split(':')
        if terminal_part:
            info['terminal'] = terminal_part[0]
            
        # 分解位置和设备部分
        parts = base_path.split('+')
        if len(parts) != 2:
            raise ValueError(f"无效的设备路径格式: {device_path}")
            
        location = parts[0]
        device_part = parts[1]
        
        # 处理设备部分
        if '.' in device_part:
            # 有特殊端子
            device_id, remaining = device_part.split('.', 1)
            if '-' in remaining:
                # 有引用设备
                special_term, reference = remaining.split('-')
                info['special_terminal'] = special_term
                info['reference'] = reference
            else:
                info['special_terminal'] = remaining
        else:
            if '-' in device_part:
                # 只有引用设备
                device_id, reference = device_part.split('-')
                info['reference'] = reference
            else:
                device_id = device_part
                
        # 构建继电器本体路径
        info['relay_path'] = f"={location}+{device_id}"
        
        return info
        
    except Exception as e:
        raise ValueError(f"解析设备路径失败: {str(e)}")

def get_base_relay_path(device_path):
    """获取继电器的基本路径（不包含特殊端子和引用）
    Args:
        device_path: 完整的设备路径
    Returns:
        str: 继电器基本路径
    """
    try:
        info = extract_relay_info(device_path)
        return info['relay_path']
    except ValueError:
        return device_path

def create_relay_node(device_path, config):
    """创建继电器节点
    Args:
        device_path: 完整的设备路径
        config: 继电器配置
    Returns:
        dict: 节点配置
    """
    try:
        # 解析设备信息
        info = extract_relay_info(device_path)
        relay_path = info['relay_path']
        
        # 从继电器路径中提取基本信息
        base_path = relay_path[1:] if relay_path.startswith('=') else relay_path
        location, device_id = base_path.split('+')
        
        node = {
            'id': relay_path,
            'labels': ['Component', 'IntComp', 'Relay'],
            'properties': {
                'name': relay_path,
                'location': location,
                'device_id': device_id,
                'type': config['type'],
                'coil_voltage': config['coil_voltage']
            }
        }
        
        # 添加特殊端子信息（如果有）
        if info['special_terminal']:
            node['properties']['special_terminal'] = info['special_terminal']
            
        # 添加引用设备信息（如果有）
        if info['reference']:
            node['properties']['reference_device'] = info['reference']
            
        return node
        
    except Exception as e:
        raise ValueError(f"创建继电器节点失败: {str(e)}")

def create_relay_terminal(device_path, terminal_id, terminal_type, properties=None):
    """创建继电器端子节点
    Args:
        device_path: 设备完整路径
        terminal_id: 端子ID
        terminal_type: 端子类型
        properties: 额外属性
    Returns:
        dict: 端子节点配置
    """
    # 获取继电器基本路径
    relay_path = get_base_relay_path(device_path)
    
    # 创建端子的完整标识符
    terminal_path = f"{relay_path}:{terminal_id}"
    
    # 基本属性
    terminal = {
        'id': terminal_path,
        'labels': ['Component', 'Vertex', terminal_type],
        'properties': {
            'name': terminal_path,
            'device_path': relay_path,
            'terminal': terminal_id
        }
    }
    
    # 添加额外属性
    if properties:
        terminal['properties'].update(properties)
        
    return terminal

class RelayInterconnection:
    """继电器互连类 - 处理跨设备的连接"""
    
    def __init__(self, source_device, target_device):
        self.source = source_device
        self.target = target_device
        self.validator = DevicePathValidator()
        self.source_info = self.validator.extract_device_info(source_device)
        self.target_info = self.validator.extract_device_info(target_device)
        
    def get_connection_type(self):
        """确定连接类型"""
        if self.source_info['sub_terminal'] and self.source_info['sub_terminal'].startswith('B'):
            return 'CONTROL_CONNECTION'  # 控制连接 (如B1到A1)
        elif self.target_info['sub_terminal'] and self.target_info['sub_terminal'].startswith('H'):
            return 'AUXILIARY_CONNECTION'  # 辅助连接 (如触点到H2)
        elif (self.source_info['terminal'] and self.source_info['terminal'].startswith('A')) or \
             (self.target_info['terminal'] and self.target_info['terminal'].startswith('A')):
            return 'COIL_CONNECTION'  # 线圈连接
        elif (self.source_info['terminal'] and self.source_info['terminal'].isdigit()) and \
             (self.target_info['terminal'] and self.target_info['terminal'].isdigit()):
            return 'CONTACT_CONNECTION'  # 触点连接
        return 'GENERIC_CONNECTION'
        
    def validate(self):
        """验证连接的有效性"""
        if not (self.source_info and self.target_info):
            return False, "设备标识符解析失败"
            
        # 验证引用关系
        source_ref = self.source_info.get('reference')
        target_ref = self.target_info.get('reference')
        
        # 检查设备引用链
        if source_ref:
            # 源设备引用了其他设备
            if source_ref != self.target_info['device_id']:
                return False, f"源设备引用 {source_ref} 与目标设备 {self.target_info['device_id']} 不匹配"
                
        if target_ref:
            # 目标设备引用了其他设备
            if target_ref != self.source_info['device_id']:
                return False, f"目标设备引用 {target_ref} 与源设备 {self.source_info['device_id']} 不匹配"
                
        # 验证特殊端子的连接规则
        source_terminal = self.source_info['terminal']
        target_terminal = self.target_info['terminal']
        
        if self.source_info['sub_terminal']:
            if self.source_info['sub_terminal'].startswith('B'):
                # B1端子只能连接到线圈端子
                if not target_terminal.startswith('A'):
                    return False, "B1端子必须连接到线圈端子(A1/A2)"
                    
        if self.target_info['sub_terminal']:
            if self.target_info['sub_terminal'].startswith('H'):
                # H2端子只能从触点端子连接
                if not source_terminal.isdigit():
                    return False, "H2端子必须从触点端子连接"
                    
        return True, "连接有效"
        
    def create_connection(self, properties=None):
        """创建连接配置"""
        # 首先验证连接
        is_valid, message = self.validate()
        if not is_valid:
            raise ValueError(message)
            
        connection_type = self.get_connection_type()
        
        base_properties = {
            'source_path': self.source_info['normalized_path'],
            'target_path': self.target_info['normalized_path'],
            'source_terminal': self.source_info['terminal'],
            'target_terminal': self.target_info['terminal'],
            'source_location': self.source_info['location'],
            'target_location': self.target_info['location'],
            'source_device_id': self.source_info['device_id'],
            'target_device_id': self.target_info['device_id'],
            'connection_type': connection_type
        }
        
        # 添加特殊端子信息
        if self.source_info['sub_terminal']:
            base_properties['source_sub_terminal'] = self.source_info['sub_terminal']
        if self.target_info['sub_terminal']:
            base_properties['target_sub_terminal'] = self.target_info['sub_terminal']
            
        # 添加设备引用信息
        if self.source_info['reference']:
            base_properties['source_reference'] = self.source_info['reference']
        if self.target_info['reference']:
            base_properties['target_reference'] = self.target_info['reference']
            
        # 合并附加属性
        if properties:
            base_properties.update(properties)
            
        return {
            'from': self.source,
            'to': self.target,
            'type': connection_type,
            'properties': base_properties
        }
        
    @staticmethod
    def create(source_device, target_device, properties=None):
        """静态工厂方法创建连接
        Args:
            source_device: 源设备标识符
            target_device: 目标设备标识符
            properties: 额外的连接属性
        Returns:
            dict: 连接配置
        """
        interconnection = RelayInterconnection(source_device, target_device)
        return interconnection.create_connection(properties)

# 确保在继电器模型中添加这些端子
RELAY_CONFIGS['K']['contacts'].append({'type': ContactType.NO, 'count': 1, 'rating': '6A'})
RELAY_CONFIGS['K']['contacts'].append({'type': ContactType.NC, 'count': 1, 'rating': '6A'})
RELAY_CONFIGS['K']['contacts'].append({'type': ContactType.CO, 'count': 1, 'rating': '6A'})
RELAY_CONFIGS['3RT']['auxiliary_contacts'].append({'type': ContactType.NO, 'count': 1, 'rating': '10A'})
RELAY_CONFIGS['3RT']['auxiliary_contacts'].append({'type': ContactType.NC, 'count': 1, 'rating': '10A'})