def get_vertex_type(function, location, device):
    """确定节点类型的规则
    Args:
        function: 功能标识，例如 'A01'
        location: 位置标识，例如 'K1.H2'
        device: 设备标识，例如 'X1', 'Q1'
    Returns:
        str: 节点类型 ('panel', 'PLC', 'other')
    """
    # 1. 根据位置判断
    if 'K1.H2' in location:
        return 'panel'
    elif 'K1.B1' in location:
        return 'panel'
    elif 'S1' in location:
        return 'panel'
    
    # 2. 根据功能标识判断
    if function.startswith('A'):
        return 'panel'
        
    # 3. 根据设备类型判断
    if 'PLC' in device.upper():
        return 'PLC'
    elif any(x in device for x in ['X1', 'X2', 'X20']):
        return 'panel'
        
    return 'other'
