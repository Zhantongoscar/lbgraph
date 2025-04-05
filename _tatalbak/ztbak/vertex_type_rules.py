from relay_rules import analyze_terminal, parse_relay_model, RelayType

def get_vertex_type(function, location, device):
    """确定节点类型的规则
    Args:
        function: 功能标识，例如 'A01'
        location: 位置标识，例如 'K1.H2'
        device: 设备标识，例如 'X1', 'Q1'
    Returns:
        list: 返回节点类型列表，包含基类和具体类型
    """
    types = ['Component']  # 基类标签
    
    # 1. 分析设备类型和位置来确定具体类型
    if any(x in device for x in ['X1', 'X2', 'X20']):
        types.extend(['IntComp', 'CableSock'])
    elif device.startswith(('Q', 'K')):  # 扩展继电器识别范围
        # 判断继电器类型
        relay_type, _ = parse_relay_model(device)
        types.extend(['IntComp', 'Relay'])
        if relay_type == RelayType.SAFETY_RELAY:
            types.append('SafetyRelay')
        elif relay_type == RelayType.TIME_RELAY:
            types.append('TimeRelay')
    elif device.startswith('G'):
        types.extend(['IntComp', 'PowerSupply'])
    elif 'PLC' in device.upper():
        types.extend(['IntComp', 'PLC'])
    
    # 2. 根据位置判断是否为内部组件
    if any(loc in location for loc in ['K1.H2', 'K1.B1', 'S1']):
        if 'IntComp' not in types:
            types.append('IntComp')
    
    # 3. 判断是否为外部设备
    if location.startswith('S') and not any(t in types for t in ['IntComp', 'CableSock']):
        types.append('ExtDev')
    
    return types

def get_vertex_properties(function, location, device, terminal):
    """根据节点信息确定其属性
    Args:
        function: 功能标识
        location: 位置标识
        device: 设备标识
        terminal: 端子标识
    Returns:
        dict: 节点属性字典
    """
    properties = {
        'status': 'unknown',  # Component基类属性
    }
    
    # 1. 解析位置信息
    if location:
        properties['location'] = location
        
    # 2. 根据设备类型添加特定属性
    if device.startswith(('Q', 'K')):  # 继电器
        if terminal:
            # 使用 relay_rules 进行端子分析
            term_type, term_props = analyze_terminal(device, terminal)
            properties.update(term_props)
            if 'type' not in properties:
                properties['type'] = term_type
    elif device.startswith('G'):  # 电源
        properties['output_voltage'] = '24VDC'
        properties['max_current'] = '10A'
    elif 'X20' in device:  # 插座
        properties['socket_type'] = 'industrial'
        
    # 3. 端子特殊属性
    if terminal:
        if terminal.startswith('PE') or terminal == 'N':
            properties['voltage'] = '0V'
        elif ':' in terminal:  # 复杂端子标识，如 SEC:31
            term_parts = terminal.split(':')
            if term_parts[0] in ['SEC', 'PRI']:
                properties['terminal_type'] = term_parts[0]
                
    return properties

def get_relationship_type(source_types, target_types, wire_properties):
    """确定连接关系类型和属性
    Args:
        source_types: 源节点的类型列表
        target_types: 目标节点的类型列表
        wire_properties: 连接属性字典
    Returns:
        tuple: (关系类型, 额外属性字典)
    """
    # 初始化返回值
    rel_type = 'CONNECTED_TO'  # 默认关系类型
    extra_props = {}
    
    # 判断是否有电缆相关信息
    has_cable = bool(wire_properties.get('cable_type') or wire_properties.get('length'))
    
    # 处理继电器特殊关系
    if 'Relay' in source_types:
        source_terminal = wire_properties.get('source_terminal', '')
        if source_terminal.startswith('A'):
            rel_type = 'CONTROLS'  # 线圈控制关系
            extra_props['control_type'] = 'electromagnetic'
            if 'TimeRelay' in source_types:
                extra_props['timing_control'] = True
                
    # 如果涉及到电缆，使用CONNECTED_VIA
    if has_cable:
        rel_type = 'CONNECTED_VIA'
        # 添加电缆相关属性
        if wire_properties.get('cable_type'):
            extra_props['cable_spec'] = wire_properties['cable_type']
        if wire_properties.get('length'):
            extra_props['cable_length'] = wire_properties['length']
            
    # 根据端子类型判断
    if any('CableSock' in types for types in [source_types, target_types]):
        rel_type = 'TERMINATES_AT'
        if wire_properties.get('color'):
            extra_props['wire_color'] = wire_properties['color']
            
    # 设备与其端子之间的关系
    if ('IntComp' in source_types and 'Vertex' in target_types) or \
       ('IntComp' in target_types and 'Vertex' in source_types):
        rel_type = 'HAS_TERMINAL'
            
    return rel_type, extra_props
