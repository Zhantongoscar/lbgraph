"""
继电器规则处理模块 - 基于图论的继电器建模
"""

class RelayType:
    """继电器类型定义"""
    POWER_RELAY = "POWER_RELAY"  # 功率继电器
    SIGNAL_RELAY = "SIGNAL_RELAY"  # 信号继电器
    TIME_RELAY = "TIME_RELAY"    # 时间继电器
    SAFETY_RELAY = "SAFETY_RELAY"  # 安全继电器

class ContactType:
    """触点类型定义"""
    NO = "NO"  # 常开触点
    NC = "NC"  # 常闭触点
    CO = "CO"  # 转换触点
    DM = "DM"  # 双断点触点
    POWER = "POWER"  # 功率触点

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

def create_relay_structure(device_id, config):
    """创建继电器的完整图结构
    Args:
        device_id: 继电器标识
        config: 继电器配置
    Returns:
        dict: 节点和关系的配置
    """
    structure = {
        'nodes': [],
        'relationships': []
    }
    
    # 1. 创建继电器本体节点
    relay_node = {
        'id': device_id,
        'labels': ['Component', 'IntComp', 'Relay'],
        'properties': {
            'name': device_id,
            'type': config['type'],
            'coil_voltage': config['coil_voltage']
        }
    }
    structure['nodes'].append(relay_node)
    
    # 2. 创建线圈端子节点
    coil_terminals = []
    if config['type'] == RelayType.POWER_RELAY:
        # 功率继电器使用标准线圈
        coil_terminals.extend([
            {
                'id': f"{device_id}:A1",
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': f"{device_id}:A1",
                    'terminal': 'A1',
                    'coil_type': RelayCoilType.STANDARD,
                    'polarity': 'positive',
                    'voltage': 0.0
                }
            },
            {
                'id': f"{device_id}:A2",
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': f"{device_id}:A2",
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
                'id': f"{device_id}:A1",
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': f"{device_id}:A1",
                    'terminal': 'A1',
                    'coil_type': RelayCoilType.ELECTRONIC,
                    'polarity': 'positive',
                    'voltage': 0.0
                }
            },
            {
                'id': f"{device_id}:A2",
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': f"{device_id}:A2",
                    'terminal': 'A2',
                    'coil_type': RelayCoilType.ELECTRONIC,
                    'polarity': 'negative',
                    'voltage': 0.0
                }
            },
            {
                'id': f"{device_id}:B1",
                'labels': ['Component', 'Vertex', 'CoilTerminal'],
                'properties': {
                    'name': f"{device_id}:B1",
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
                    'id': f"{device_id}:A1{group_suffix}",
                    'labels': ['Component', 'Vertex', 'CoilTerminal'],
                    'properties': {
                        'name': f"{device_id}:A1{group_suffix}",
                        'terminal': f"A1{group_suffix}",
                        'coil_type': RelayCoilType.DUAL if group_suffix else RelayCoilType.STANDARD,
                        'coil_group': i,
                        'polarity': 'positive',
                        'voltage': 0.0
                    }
                },
                {
                    'id': f"{device_id}:A2{group_suffix}",
                    'labels': ['Component', 'Vertex', 'CoilTerminal'],
                    'properties': {
                        'name': f"{device_id}:A2{group_suffix}",
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
                'id': f"{device_id}:{term['input']}",
                'labels': ['Component', 'Vertex', 'PowerTerminal'],
                'properties': {
                    'name': f"{device_id}:{term['input']}",
                    'terminal': term['input'],
                    'terminal_type': 'POWER_IN',
                    'phase': term['input'][-1],
                    'rating': poles['rating']
                }
            }
            
            # 创建输出端子(T1,T2,T3)
            output_node = {
                'id': f"{device_id}:{term['output']}",
                'labels': ['Component', 'Vertex', 'PowerTerminal'],
                'properties': {
                    'name': f"{device_id}:{term['output']}",
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
                        'id': f"{device_id}:{terminal_id}",
                        'labels': ['Component', 'Vertex', 'ContactTerminal'],
                        'properties': {
                            'name': f"{device_id}:{terminal_id}",
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
                    'id': f"{device_id}:{terminal_id}",
                    'labels': ['Component', 'Vertex', 'DiagnosticTerminal'],
                    'properties': {
                        'name': f"{device_id}:{terminal_id}",
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

def parse_relay_model(device_id):
    """解析继电器型号
    Args:
        device_id: 设备ID，如 "Q1", "K5" 等
    Returns:
        tuple: (继电器类型, 配置字典)
    """
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
    
    # 创建配置副本并返回
    config = base_config.copy()
    
    # 确保配置中包含 'contacts' 字段
    if 'contacts' not in config:
        config['contacts'] = []
    
    return config["type"], config

class RelayCoil:
    """继电器线圈类"""
    def __init__(self, voltage, connections=None):
        self.voltage = voltage
        self.connections = connections or {'A1': None, 'A2': None}
        self.state = 'de-energized'
        
    def calculate_voltage_difference(self):
        """计算线圈两端电压差"""
        if self.connections['A1'] and self.connections['A2']:
            return abs(self.connections['A1'].voltage - self.connections['A2'].voltage)
        return 0

class RelayContact:
    """继电器触点类"""
    def __init__(self, contact_type, group_number=1):
        self.type = contact_type
        self.group = group_number
        self.state = 'open'
        self.connections = {}
        
    def update_state(self, coil_energized):
        """根据线圈状态更新触点状态"""
        if self.type == ContactType.NO:
            self.state = 'closed' if coil_energized else 'open'
        elif self.type == ContactType.NC:
            self.state = 'open' if coil_energized else 'closed'

class Relay:
    """继电器类"""
    def __init__(self, device_id, config):
        self.device_id = device_id
        self.config = config
        self.coil = RelayCoil(config['coil_voltage'])
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
                        'COM': RelayContact(ContactType.CO, group_number),
                        'NO': RelayContact(ContactType.NO, group_number),
                        'NC': RelayContact(ContactType.NC, group_number)
                    }
                else:
                    # 创建单个触点
                    self.contacts[f'{group_number}'] = {
                        'MAIN': RelayContact(contact_config['type'], group_number)
                    }

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

def analyze_terminal(device_id, terminal_id):
    """分析端子类型和属性
    Args:
        device_id: 设备ID，如 "Q1", "K5" 等
        terminal_id: 端子ID，如 "L1", "T1", "13", "14", "A1" 等
    Returns:
        tuple: (端子类型, 属性字典)
    """
    # 获取继电器配置
    relay_type, config = parse_relay_model(device_id)
    
    # 解析端子ID
    terminal_props = parse_terminal_id(terminal_id)
    
    # 基本属性
    properties = {
        "terminal": terminal_id,
        "terminal_type": terminal_props['type'],
        "is_connection": True
    }
    
    # 根据端子类型处理
    if terminal_props['type'] == RelayTerminalType.POWER_IN:
        # 电源输入端子
        properties.update({
            "role": "power_input",
            "phase": terminal_props['phase'],
            "state": "open"
        })
        if 'power_poles' in config:
            properties["rating"] = config['power_poles']['rating']
        return "PowerTerminal", properties
        
    elif terminal_props['type'] == RelayTerminalType.POWER_OUT:
        # 负载输出端子
        properties.update({
            "role": "power_output",
            "phase": terminal_props['phase'],
            "state": "open"
        })
        if 'power_poles' in config:
            properties["rating"] = config['power_poles']['rating']
        return "PowerTerminal", properties
        
    elif terminal_props['type'] == RelayTerminalType.COIL:
        # 线圈端子
        properties.update({
            "coil_voltage": config["coil_voltage"],
            "polarity": "positive" if terminal_props['role'] == RelayTerminalRole.COIL_PLUS else "negative"
        })
        return "RelayCoilTerm", properties
        
    elif terminal_props['type'] in [RelayTerminalType.CONTACT, RelayTerminalType.POWER_IN, RelayTerminalType.POWER_OUT]:
        # 触点或电源端子
        properties.update({
            "state": "open" if terminal_props['role'] == RelayTerminalRole.NO else "closed",
            "contact_role": terminal_props['role'],
            "contact_group": terminal_props.get('group', 1)
        })
        
        # 添加触点配置
        if terminal_props['type'] == RelayTerminalType.CONTACT:
            for contact_config in config["contacts"]:
                if properties["contact_group"] <= contact_config["count"]:
                    properties["contact_type"] = contact_config["type"]
                    properties["rating"] = contact_config["rating"]
                    break
                    
        return "RelayContactTerm", properties
        
    elif terminal_props['type'] == RelayTerminalType.DIAGNOSTIC:
        # 诊断端子
        properties.update({
            "state": "unknown",
            "diagnostic_type": "status",
            "contact_role": RelayTerminalRole.DIAGNOSTIC
        })
        return "RelayDiagnosticTerm", properties
        
    else:
        # 未知端子类型
        properties.update({
            "state": "unknown",
            "contact_role": terminal_props['role'],
            "contact_group": 1
        })
        return "RelayTerminal", properties

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
    
    # 首先检查是否为电源端子
    if terminal_id in POWER_TERMINAL_MAPPING:
        return POWER_TERMINAL_MAPPING[terminal_id]
    
    # 如果不是电源端子，按之前的逻辑处理
    prefix = ''.join(c for c in terminal_id if c.isalpha())
    number = ''.join(c for c in terminal_id if c.isdigit())
    
    try:
        if prefix in TERMINAL_MAPPING:
            base_props = TERMINAL_MAPPING[prefix].copy()
            if number:
                base_props['number'] = int(number)
                # 线圈端子特殊处理
                if prefix == 'A':
                    base_props['role'] = (
                        RelayTerminalRole.COIL_PLUS if number == '1'
                        else RelayTerminalRole.COIL_MINUS
                    )
            return base_props
            
        elif terminal_id.isdigit():
            num = int(terminal_id)
            group = num // 10 if num >= 10 else 1
            contact_type = num % 10
            
            return {
                'type': RelayTerminalType.CONTACT,
                'group': group,
                'role': {
                    1: RelayTerminalRole.COM,
                    2: RelayTerminalRole.NC,
                    4: RelayTerminalRole.NO
                }.get(contact_type, RelayTerminalRole.AUXILIARY)
            }
            
    except (ValueError, AttributeError):
        pass
        
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