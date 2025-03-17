#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设备规则定义模块
包含设备内部连接规则的定义和实现
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

class DeviceRule:
    """基础规则类"""

    def __init__(self, rule_id: str, name: str, description: str, priority: int = 999):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.priority = priority
        self.enabled = True

    @property
    def default_properties(self) -> Dict:
        """默认连接属性"""
        return {
            "voltage": 24.0,
            "current": 0.1,
            "resistance": 240.0,
            "isCable": False,
            "isInPanel": True
        }

class KSRule(DeviceRule):
    """KS安全继电器规则 R001"""

    def __init__(self):
        super().__init__(
            "R001",
            "KS安全继电器规则",
            "安全继电器的识别和连接规则",
            priority=1
        )
        # 定义线圈端子对
        self.coil_terminals = {
            'A1', 'A2',  # 标准线圈
            'A11', 'A12',  # 安全继电器主线圈
            'S11', 'S12',  # 安全线圈1
            'S21', 'S22'   # 安全线圈2
        }

    def match(self, device_name: str, terminals: Set[str]) -> bool:
        """
        判断设备是否为KS类型
        规则：设备名称以K开头
        """
        return device_name.startswith('K')

    def get_connections(self, points: List[Dict]) -> List[Dict]:
        """生成所有连接"""
        connections = []
        
        # 检查是否为安全继电器（有A11-A12）
        is_safety_relay = False
        terminal_set = {p['Terminal'].split(':')[-1] for p in points}
        if 'A11' in terminal_set and 'A12' in terminal_set:
            is_safety_relay = True
        
        # 如果是安全继电器，处理安全继电器特有的连接
        if is_safety_relay:
            safety_connections = self._create_safety_connections(points)
            if safety_connections:
                connections.extend(safety_connections)
        
        # 处理标准连接（对所有K类设备都适用）
        standard_connections = self._create_standard_connections(points)
        if standard_connections:
            connections.extend(standard_connections)

        # 处理触点连接
        contact_connections = self._create_contact_connections(points)
        if contact_connections:
            connections.extend(contact_connections)

        return connections

    def _find_terminal_points(self, points: List[Dict], terminal: str) -> Optional[Dict]:
        """查找指定端子的点位"""
        for point in points:
            if point['Terminal'].endswith(terminal):
                return point
        return None

    def _create_connection(self, point1: Dict, point2: Dict, conn_type: str) -> Dict:
        """创建一个连接对象"""
        props = self.default_properties.copy()
        props.update({
            "connType": conn_type
        })
        
        return {
            'source': point1['ftid'],
            'target': point2['ftid'],
            'sourceTerminal': point1['Terminal'],
            'targetTerminal': point2['Terminal'],
            'properties': props
        }

    def _create_safety_connections(self, points: List[Dict]) -> List[Dict]:
        """创建安全继电器特有的连接"""
        connections = []
        safety_coil_pairs = [
            ('A11', 'A12'),   # 主线圈
            ('S11', 'S12'),   # S11-S12
            ('S21', 'S22')    # S21-S22
        ]
        
        for term1, term2 in safety_coil_pairs:
            point1 = self._find_terminal_points(points, term1)
            point2 = self._find_terminal_points(points, term2)
            if point1 and point2:
                connections.append(
                    self._create_connection(point1, point2, "coil")
                )
                
        return connections

    def _create_standard_connections(self, points: List[Dict]) -> List[Dict]:
        """创建标准K类设备的连接"""
        connections = []
        
        # A1-A2 coil连接
        point_a1 = self._find_terminal_points(points, 'A1')
        point_a2 = self._find_terminal_points(points, 'A2')
        if point_a1 and point_a2:
            connections.append(
                self._create_connection(point_a1, point_a2, "coil")
            )
        
        # A-0 NC连接
        point_a = self._find_terminal_points(points, 'A')
        point_0 = self._find_terminal_points(points, '0')
        if point_a and point_0:
            connections.append(
                self._create_connection(point_a, point_0, "NC")
            )
        
        # A-+ NO连接
        point_plus = self._find_terminal_points(points, '+')
        if point_a and point_plus:
            connections.append(
                self._create_connection(point_a, point_plus, "NO")
            )
        
        return connections

    def _is_coil_terminal(self, terminal: str) -> bool:
        """判断是否为线圈端子"""
        return terminal in self.coil_terminals

    def _create_contact_connections(self, points: List[Dict]) -> List[Dict]:
        """创建触点连接"""
        connections = []
        terminals_dict = {}
        
        # 建立端子号字典
        for point in points:
            terminal = point['Terminal']
            if ':' in terminal:
                terminal = terminal.split(':')[-1]
            terminals_dict[terminal] = point

        # 处理NC触点对（*1-*2模式）
        for terminal in terminals_dict:
            if terminal.endswith('1'):
                # 跳过线圈端子
                if self._is_coil_terminal(terminal):
                    continue
                    
                base = terminal[:-1]
                other = base + '2'
                if other in terminals_dict:
                    connections.append(
                        self._create_connection(
                            terminals_dict[terminal],
                            terminals_dict[other],
                            "NC"
                        )
                    )
                    
        # 处理NO触点对（*3-*4模式）
        for terminal in terminals_dict:
            if terminal.endswith('3'):
                base = terminal[:-1]
                other = base + '4'
                if other in terminals_dict:
                    connections.append(
                        self._create_connection(
                            terminals_dict[terminal],
                            terminals_dict[other],
                            "NO"
                        )
                    )

        return connections

def create_ks_rule() -> KSRule:
    """创建KS规则实例"""
    return KSRule()

if __name__ == "__main__":
    # 测试代码
    ks_rule = create_ks_rule()
    print(f"规则ID: {ks_rule.rule_id}")
    print(f"规则名称: {ks_rule.name}")
    print(f"规则描述: {ks_rule.description}")
    print(f"规则优先级: {ks_rule.priority}")