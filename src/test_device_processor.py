import json
from typing import Dict, List
import os

class TestDeviceProcessor:
    def __init__(self):
        self.devices = []
        self.connections = []
        
    def add_device(self, device_type_id: str, properties: Dict = None):
        """添加测试设备"""
        from device_types import get_device_type
        
        if properties is None:
            properties = {}
            
        # 获取设备类型定义
        device_type = get_device_type(device_type_id)
        device_id = f"TEST_{device_type_id}_{len(self.devices) + 1}"
        
        # 合并属性
        device_properties = {
            'description': device_type.description,
            'point_count': device_type.point_count,
            'input_points': device_type.input_points,
            'output_points': device_type.output_points,
            **properties
        }
        
        # 添加设备节点
        device = {
            'id': device_id,
            'type': device_type_id,
            'name': device_type.name,
            'properties': device_properties,
            'is_test_device': True
        }
        self.devices.append(device)
        
        # 添加所有点作为独立节点
        for point in device_type.input_points + device_type.output_points:
            self.devices.append({
                'id': f"{device_id}_{point}",
                'type': f"{device_type_id}_POINT",
                'parent_device': device_id,
                'properties': {
                    'point_type': 'input' if point in device_type.input_points else 'output'
                }
            })
            
        device = {
            'id': device_id,
            'type': device_type,
            'properties': properties,
            'is_test_device': True
        }
        self.devices.append(device)
        return device_id

    def set_a_unit_state(self, device_id: str, state: str):
        """设置A单元连接状态"""
        device = next((d for d in self.devices if d['id'] == device_id), None)
        if not device or device['type'] != 'A_UNIT':
            raise ValueError("无效的A单元设备ID")
            
        if state not in ['connected', 'disconnected']:
            raise ValueError("状态必须是 'connected' 或 'disconnected'")
            
        # 更新状态
        device['properties']['connection_state'] = state
        
        # 管理连接边
        point1 = device['properties']['point1']
        point2 = device['properties']['point2']
        
        # 移除旧的连接
        self.connections = [c for c in self.connections
                          if not (c['source'] == point1 and c['target'] == point2)]
        
        # 添加新的连接
        if state == 'connected':
            self.add_connection(point1, point2, {
                'type': 'A_UNIT_CONNECTION',
                'state': 'active'
            })
        
    def add_connection(self, source: str, target: str, properties: Dict = None):
        """添加测试连接"""
        if properties is None:
            properties = {}
            
        connection = {
            'source': source,
            'target': target,
            'properties': properties,
            'is_test_connection': True
        }
        self.connections.append(connection)
        
    def save_to_json(self, file_path: str):
        """保存为JSON文件"""
        graph_data = {
            'nodes': self.devices,
            'edges': self.connections,
            'metadata': {
                'type': 'test_devices',
                'version': '1.0'
            }
        }
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)

def display_menu():
    print("\n==== 测试设备管理系统 ====")
    print("1. 添加设备")
    print("2. 查看设备列表")
    print("3. 保存配置")
    print("4. 退出")
    return input("请选择操作（1-4）：")

def add_device_interactive(processor):
    from device_types import list_device_types
    
    print("\n可用设备类型：")
    for i, device_type in enumerate(list_device_types(), 1):
        print(f"{i}. {device_type.name} ({device_type.description})")
    
    choice = input("请选择设备类型编号：")
    try:
        device_type = list_device_types()[int(choice) - 1]
        properties = {}
        
        # 添加自定义属性
        print(f"\n添加 {device_type.name} 设备")
        for key, value in device_type.properties.items():
            properties[key] = input(f"请输入 {key}（默认：{value}）：") or value
        
        # 添加位置信息
        location = input("请输入设备位置（如 K1.01）：")
        if location:
            properties['location'] = location
            
        device_id = processor.add_device(device_type.id, properties)
        print(f"设备添加成功，ID: {device_id}")
    except (IndexError, ValueError):
        print("无效的选择，请重试")

def list_devices(processor):
    print("\n当前设备列表：")
    for device in processor.devices:
        if device.get('is_test_device'):
            print(f"- {device['id']} ({device['type']})")
            print(f"  位置: {device['properties'].get('location', '未指定')}")
            print(f"  描述: {device['properties'].get('description', '')}")

if __name__ == "__main__":
    processor = TestDeviceProcessor()
    
    while True:
        choice = display_menu()
        
        if choice == '1':
            add_device_interactive(processor)
        elif choice == '2':
            list_devices(processor)
        elif choice == '3':
            file_name = input("请输入保存文件名（不带扩展名）：")
            if file_name:
                processor.save_to_json(f'output/{file_name}.json')
                print(f"配置已保存到 output/{file_name}.json")
            else:
                print("文件名不能为空")
        elif choice == '4':
            print("退出系统")
            break
        else:
            print("无效的选择，请重试")