from dataclasses import dataclass
from typing import Dict, List

@dataclass
class DeviceType:
    id: str
    name: str
    point_count: int
    description: str
    input_points: List[str]
    output_points: List[str]
    properties: Dict = None

# 设备类型定义
# 设备类型定义
DEVICE_TYPES = {
    'EDB': DeviceType(
        id='EDB',
        name='增强模块 EDB',
        point_count=20,
        description='20点（7DI + 3DO + 10DI）',
        input_points=[f'D{i}' for i in range(1, 18)],
        output_points=[f'B{i}' for i in range(1, 4)]
    ),
    'EBD': DeviceType(
        id='EBD',
        name='增强模块 EBD',
        point_count=20,
        description='20点（8DO + 4DI + 8DO）',
        input_points=[f'D{i}' for i in range(1, 5)],
        output_points=[f'B{i}' for i in range(1, 17)]
    ),
    'A': DeviceType(
        id='A',
        name='普通模块 A',
        point_count=20,
        description='20点（14DO + 6DI）',
        input_points=[f'D{i}' for i in range(1, 7)],
        output_points=[f'B{i}' for i in range(1, 15)]
    ),
    'C': DeviceType(
        id='C',
        name='普通模块 C',
        point_count=20,
        description='20点（14DO + 6DI）',
        input_points=[f'D{i}' for i in range(1, 7)],
        output_points=[f'B{i}' for i in range(1, 15)]
    ),
    'F': DeviceType(
        id='F',
        name='普通模块 F',
        point_count=20,
        description='20点（20DI）',
        input_points=[f'D{i}' for i in range(1, 21)],
        output_points=[]
    ),
    'W': DeviceType(
        id='W',
        name='普通模块 W',
        point_count=20,
        description='20点（6DI + 2DO + 12DI）',
        input_points=[f'D{i}' for i in range(1, 19)],
        output_points=[f'B{i}' for i in range(1, 3)]
    ),
    'PDI': DeviceType(
        id='PDI',
        name='PLC模块 PDI',
        point_count=16,
        description='16点（16DI）',
        input_points=[f'DI{i}' for i in range(1, 17)] + [f'D{i}' for i in range(1, 17)],
        output_points=[]
    ),
    'PDO': DeviceType(
        id='PDO',
        name='PLC模块 PDO',
        point_count=16,
        description='16点（16DO）',
        input_points=[],
        output_points=[f'DO{i}' for i in range(1, 17)] + [f'B{i}' for i in range(1, 17)]
    ),
    'PAI': DeviceType(
        id='PAI',
        name='PLC模块 PAI',
        point_count=16,
        description='16点（16AI）',
        input_points=[f'AI{i}' for i in range(1, 17)],
        output_points=[]
    ),
    'PAO': DeviceType(
        id='PAO',
        name='PLC模块 PAO',
        point_count=16,
        description='16点（16AO）',
        input_points=[],
        output_points=[f'AO{i}' for i in range(1, 17)]
    ),
    'HI': DeviceType(
        id='HI',
        name='人工模块 HI',
        point_count=20,
        description='20点（20AI）',
        input_points=[f'AI{i}' for i in range(1, 21)],
        output_points=[]
    ),
    'HO': DeviceType(
        id='HO',
        name='人工模块 HO',
        point_count=20,
        description='20点（20AO）',
        input_points=[],
        output_points=[f'AO{i}' for i in range(1, 21)]
    ),
    'D': DeviceType(
        id='D',
        name='普通模块 D',
        point_count=6,
        description='6点（6DI）',
        input_points=[f'DI{i}' for i in range(1, 7)] + [f'D{i}' for i in range(1, 7)],
        output_points=[]
    ),
    'B': DeviceType(
        id='B',
        name='普通模块 B',
        point_count=6,
        description='6点（6DO）',
        input_points=[],
        output_points=[f'DO{i}' for i in range(1, 7)] + [f'B{i}' for i in range(1, 7)]
    ),
    'A': DeviceType(
        id='A',
        name='普通模块 A',
        point_count=6,
        description='6点（6DO）',
        input_points=[],
        output_points=[f'DO{i}' for i in range(1, 7)] + [f'B{i}' for i in range(1, 7)]
    ),
    'C': DeviceType(
        id='C',
        name='普通模块 C',
        point_count=6,
        description='6点（6DO）',
        input_points=[],
        output_points=[f'DO{i}' for i in range(1, 7)] + [f'B{i}' for i in range(1, 7)]
    ),
    'F': DeviceType(
        id='F',
        name='普通模块 F',
        point_count=6,
        description='6点（6DI）',
        input_points=[f'DI{i}' for i in range(1, 7)] + [f'D{i}' for i in range(1, 7)],
        output_points=[]
    ),
    'W': DeviceType(
        id='W',
        name='普通模块 W',
        point_count=6,
        description='6点（6DI）',
        input_points=[f'DI{i}' for i in range(1, 7)] + [f'D{i}' for i in range(1, 7)],
        output_points=[]
    )
}
def get_device_type(device_id: str) -> DeviceType:
    """根据ID获取设备类型"""
    if device_id not in DEVICE_TYPES:
        raise ValueError(f"未知的设备类型: {device_id}")
    return DEVICE_TYPES[device_id]

def list_device_types() -> List[DeviceType]:
    """获取所有设备类型"""
    return list(DEVICE_TYPES.values())