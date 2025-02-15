def get_vertex_type(function, location, device):
    """
    根据 function、location 和 device 参数判断 Vertex 的 type。
    规则示例：
      - 如果 device 以 "A" 开头，则认为类型为 PLC。
      - 如果 location 不以 "K1." 开头，则认为类型为 field。
      - 否则类型为 panel。
    """
    if device.startswith('A'):
        return 'PLC'
    elif not location.startswith('K1.'):
        return 'field'
    return 'panel'

def get_vertex_details(function, location, device):
    """
    新增示例函数，用于返回包含 type、position 和 role 的节点属性。
    - type：面板(panel)、PLC、field 等
    - position：inside（柜内）或 outside（柜外）
    - role：可根据解析后的逻辑来区分 RelayCoil、RelayContact、CableTerminal 等
    """
    base_type = get_vertex_type(function, location, device)
    
    # position
    if location.startswith('K1.'):
        position = 'inside'
    else:
        position = 'outside'
    
    # role（根据需求添加更细的判断逻辑）
    if 'X20' in device or 'X21' in device or 'X22' in device:
        role = 'CableTerminal'
    elif base_type == 'PLC':
        role = 'PLC_IO'
    else:
        role = 'Generic'
    
    return {
        'type': base_type,
        'position': position,
        'role': role
    }

# 若后续有更多规则，可在此扩展...
