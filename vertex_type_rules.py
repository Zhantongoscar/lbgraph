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
    elif device.startswith('Q'):
        types.extend(['IntComp', 'Relay'])
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
    if device.startswith('Q'):  # 继电器
        properties['coil_voltage'] = '24VDC'
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

def get_relationship_type(source_types, target_types, has_cable=False):
    """确定连接关系类型
    Args:
        source_types: 源节点的类型列表
        target_types: 目标节点的类型列表
        has_cable: 是否通过电缆连接
    Returns:
        str: 连接关系类型
    """
    # 第一阶段保持简单的连接关系
    return 'conn'
