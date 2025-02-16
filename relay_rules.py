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
    # 功率继电器
    "3RT": {
        "type": RelayType.POWER_RELAY,
        "coil_voltage": "230VAC",
        "contacts": [
            {"type": ContactType.POWER, "count": 3, "rating": "30A"},
            {"type": ContactType.NO, "count": 1, "rating": "10A"}
        ]
    },
    # 小型继电器
    "RY": {
        "type": RelayType.SIGNAL_RELAY,
        "coil_voltage": "24VDC",
        "contacts": [
            {"type": ContactType.CO, "count": 4, "rating": "6A"}
        ]
    },
    # 时间继电器
    "H3Y": {
        "type": RelayType.TIME_RELAY,
        "coil_voltage": "24VDC",
        "timing": "0.1-10s",
        "contacts": [
            {"type": ContactType.CO, "count": 2, "rating": "5A"}
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
    coil_a1 = {
        'id': f"{device_id}:A1",
        'labels': ['Component', 'Vertex', 'CoilTerminal'],
        'properties': {
            'name': f"{device_id}:A1",
            'terminal': 'A1',
            'polarity': 'positive',
            'voltage': 0.0
        }
    }
    coil_a2 = {
        'id': f"{device_id}:A2",
        'labels': ['Component', 'Vertex', 'CoilTerminal'],
        'properties': {
            'name': f"{device_id}:A2",
            'terminal': 'A2',
            'polarity': 'negative',
            'voltage': 0.0
        }
    }
    structure['nodes'].extend([coil_a1, coil_a2])
    
    # 3. 创建线圈关系
    coil_connection = {
        'from': coil_a1['id'],
        'to': coil_a2['id'],
        'type': 'COIL_CONNECTION',
        'properties': {
            'impedance': config.get('coil_impedance', '100Ω'),
            'rated_voltage': config['coil_voltage']
        }
    }
    structure['relationships'].append(coil_connection)
    
    # 4. 为每个触点组创建节点和关系
    for contact_config in config['contacts']:
        for group in range(1, contact_config['count'] + 1):
            # 创建COM端子
            com_node = {
                'id': f"{device_id}:{group}1",
                'labels': ['Component', 'Vertex', 'ContactTerminal'],
                'properties': {
                    'name': f"{device_id}:{group}1",
                    'terminal': f"{group}1",
                    'role': 'COM',
                    'group': group,
                    'rating': contact_config['rating']
                }
            }
            
            # 创建NC端子
            nc_node = {
                'id': f"{device_id}:{group}2",
                'labels': ['Component', 'Vertex', 'ContactTerminal'],
                'properties': {
                    'name': f"{device_id}:{group}2",
                    'terminal': f"{group}2",
                    'role': 'NC',
                    'group': group,
                    'rating': contact_config['rating']
                }
            }
            
            # 创建NO端子
            no_node = {
                'id': f"{device_id}:{group}4",
                'labels': ['Component', 'Vertex', 'ContactTerminal'],
                'properties': {
                    'name': f"{device_id}:{group}4",
                    'terminal': f"{group}4",
                    'role': 'NO',
                    'group': group,
                    'rating': contact_config['rating']
                }
            }
            
            structure['nodes'].extend([com_node, nc_node, no_node])
            
            # 创建触点切换关系
            structure['relationships'].extend([
                {
                    'from': com_node['id'],
                    'to': nc_node['id'],
                    'type': 'SWITCH_TO',
                    'properties': {
                        'state': 'closed',  # 默认NC闭合
                        'group': group
                    }
                },
                {
                    'from': com_node['id'],
                    'to': no_node['id'],
                    'type': 'SWITCH_TO',
                    'properties': {
                        'state': 'open',    # 默认NO断开
                        'group': group
                    }
                }
            ])
            
            # 创建继电器本体到端子的从属关系
            for node in [com_node, nc_node, no_node]:
                structure['relationships'].append({
                    'from': relay_node['id'],
                    'to': node['id'],
                    'type': 'HAS_TERMINAL',
                    'properties': {'group': group}
                })
    
    # 5. 创建线圈到触点的控制关系
    for group in range(1, len(config['contacts']) + 1):
        structure['relationships'].extend([
            {
                'from': coil_a1['id'],
                'to': f"{device_id}:{group}1",  # COM
                'type': 'CONTROLS',
                'properties': {
                    'control_type': 'electromagnetic',
                    'group': group
                }
            }
        ])
    
    return structure

def parse_relay_model(device_id):
    """解析继电器型号
    Args:
        device_id: 设备ID，如 "Q1", "K5" 等
    Returns:
        tuple: (继电器类型, 配置字典)
    """
    # 提取型号前缀（前3-4个字符）
    model_prefix = device_id[:3]
    
    # 查找匹配的配置
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
    if terminal_props['type'] == 'CONTROL' and terminal_props.get('role') == 'COIL':
        # 线圈端子
        properties.update({
            "coil_voltage": config["coil_voltage"],
            "polarity": "positive" if terminal_id.endswith('1') else "negative"
        })
        return "RelayCoilTerm", properties
    elif terminal_props['type'] in ['CONTACT', 'POWER']:
        # 触点端子
        properties.update({
            "state": "open",
            "contact_role": terminal_props['role'],
            "contact_group": terminal_props.get('group', 1)
        })
        
        # 添加触点配置
        for contact_config in config["contacts"]:
            if properties["contact_group"] <= contact_config["count"]:
                properties["contact_type"] = contact_config["type"]
                properties["rating"] = contact_config["rating"]
                break
                
        return "RelayContactTerm", properties
    else:
        # 未知端子类型，使用默认配置
        properties.update({
            "state": "unknown",
            "contact_role": terminal_props['role'],
            "contact_group": 1
        })
        return "RelayContactTerm", properties

def parse_terminal_id(terminal_id):
    """解析端子ID，处理特殊的端子命名
    Args:
        terminal_id: 端子ID，如 "L1", "T1", "13", "14", "D1" 等
    Returns:
        dict: 端子属性字典
    """
    # 标准化端子命名规则
    TERMINAL_MAPPING = {
        # 电源端子
        'L': {'role': 'LINE', 'type': 'POWER'},
        'N': {'role': 'NEUTRAL', 'type': 'POWER'},
        'T': {'role': 'LINE_OUT', 'type': 'POWER'},
        # 控制端子
        'A': {'role': 'COIL', 'type': 'CONTROL'},
        'B': {'role': 'AUXILIARY', 'type': 'CONTROL'},
        # 继电器端子
        'D': {'role': 'DIAGNOSTIC', 'type': 'CONTACT'},
    }
    
    # 尝试解析前缀和数字
    prefix = ''.join(c for c in terminal_id if c.isalpha())
    number = ''.join(c for c in terminal_id if c.isdigit())
    
    try:
        if prefix in TERMINAL_MAPPING:
            base_props = TERMINAL_MAPPING[prefix].copy()
            if number:
                base_props['number'] = int(number)
                if base_props['type'] == 'POWER':
                    base_props['phase'] = f"L{number}"
            return base_props
        elif terminal_id.isdigit():
            num = int(terminal_id)
            # 标准触点端子命名规则：第一位是组号，第二位是触点类型
            group = num // 10
            contact_type = num % 10
            return {
                'type': 'CONTACT',
                'group': group if group > 0 else 1,
                'role': {
                    1: 'COM',
                    2: 'NC',
                    4: 'NO'
                }.get(contact_type, 'UNKNOWN')
            }
    except (ValueError, AttributeError):
        pass
        
    return {
        'type': 'UNKNOWN',
        'role': 'UNKNOWN'
    }