import json
import os
from typing import Dict, List, Optional
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QWidget
from device_types import get_device_type, list_device_types

class GuiDeviceProcessor:
    def __init__(self):
        self.devices = []
        self.connections = []
        
    def add_device(self, device_type_id: str, properties: Dict = None) -> Optional[str]:
        """添加测试设备
        
        Args:
            device_type_id: 设备类型ID
            properties: 设备属性
            
        Returns:
            Optional[str]: 设备ID，失败返回None
        """
        try:
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
                
            return device_id
            
        except Exception as e:
            return None
            
    def add_device_interactive(self, parent_widget: QWidget) -> Optional[str]:
        """交互式添加设备
        
        Args:
            parent_widget: 父窗口部件
            
        Returns:
            Optional[str]: 设备ID，取消或失败返回None
        """
        try:
            # 获取设备类型列表
            device_types = list(list_device_types())
            type_names = [f"{dt.name} ({dt.description})" for dt in device_types]
            
            # 选择设备类型
            type_name, ok = QInputDialog.getItem(
                parent_widget,
                "选择设备类型",
                "请选择设备类型:",
                type_names,
                0,
                False
            )
            
            if not ok:
                return None
                
            # 获取选中的设备类型
            selected_type = device_types[type_names.index(type_name)]
            properties = {}
            
            # 添加自定义属性
            if selected_type.properties:
                for key, value in selected_type.properties.items():
                    prop_value, ok = QInputDialog.getText(
                        parent_widget,
                        f"设置{key}",
                        f"请输入 {key}（默认：{value}）:",
                        text=str(value)
                    )
                    
                    if ok:
                        properties[key] = prop_value
                    else:
                        properties[key] = value
                        
            # 添加位置信息
            location, ok = QInputDialog.getText(
                parent_widget,
                "设置位置",
                "请输入设备位置（如 K1.01）:"
            )
            
            if ok and location:
                properties['location'] = location
                
            # 添加设备
            device_id = self.add_device(selected_type.id, properties)
            if device_id:
                QMessageBox.information(
                    parent_widget,
                    "成功",
                    f"设备添加成功，ID: {device_id}"
                )
                return device_id
            else:
                QMessageBox.critical(
                    parent_widget,
                    "错误",
                    "添加设备失败"
                )
                return None
                
        except Exception as e:
            QMessageBox.critical(
                parent_widget,
                "错误",
                f"添加设备时发生错误: {str(e)}"
            )
            return None
            
    def load_from_json(self, file_path: str, parent_widget: QWidget = None) -> bool:
        """从JSON文件加载设备配置
        
        Args:
            file_path: JSON文件路径
            parent_widget: 父窗口部件
            
        Returns:
            bool: 是否成功加载
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
                
            # 清空现有数据
            self.devices.clear()
            self.connections.clear()
            
            # 重建设备树结构
            point_map = {}
            for node in graph_data['nodes']:
                if node.get('is_test_device'):
                    # 主设备
                    self.devices.append(node)
                elif node.get('parent_device'):
                    # 连接点
                    point_map[node['id']] = node
                    self.devices.append(node)
            
            # 重建连接关系
            for edge in graph_data['edges']:
                self.connections.append({
                    'source': edge['source'],
                    'target': edge['target'],
                    'properties': edge.get('properties', {}),
                    'is_test_connection': True
                })
            
            return True
            
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(
                    parent_widget,
                    "错误",
                    f"加载配置文件失败: {str(e)}"
                )
            return False

    def set_a_unit_state(self, device_id: str, state: str, parent_widget: QWidget = None) -> bool:
        """设置A单元连接状态
        
        Args:
            device_id: 设备ID
            state: 连接状态
            parent_widget: 父窗口部件
            
        Returns:
            bool: 是否成功设置状态
        """
        try:
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
                
            return True
            
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(
                    parent_widget,
                    "错误",
                    f"设置状态失败: {str(e)}"
                )
            return False
            
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
        
    def get_devices(self) -> List[Dict]:
        """获取所有测试设备"""
        return [d for d in self.devices if d.get('is_test_device')]
        
    def save_to_json(self, file_path: str, parent_widget: QWidget = None) -> bool:
        """保存为JSON文件
        
        Args:
            file_path: 保存路径
            parent_widget: 父窗口部件
            
        Returns:
            bool: 是否成功保存
        """
        try:
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
                
            return True
            
        except Exception as e:
            if parent_widget:
                QMessageBox.critical(
                    parent_widget,
                    "错误",
                    f"保存失败: {str(e)}"
                )
            return False