# 完整的设备名称映射关系
DEVICE_MAPPING = {
    # 标准映射
    'B1': 'A1',
    'H2': 'A2', 
    'H1': 'A3',
    'G1': 'A4',
    'D2': 'A5',
    
    # 新增映射
    'G2': 'A6',
    'E1': 'A7',
    'I1': 'A8',
    'A1': 'A1',  # 自身映射
    'A2': 'A2',
    'A3': 'A3',
    'A4': 'A4',
    'A5': 'A5',
    
    # 特殊设备映射
    'T1': 'T1',
    'T2': 'T2'
}

def get_plc_device(csv_device):
    """将CSV设备名称映射为PLC设备名称"""
    return DEVICE_MAPPING.get(csv_device, csv_device)