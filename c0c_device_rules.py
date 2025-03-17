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

    def match(self, device_name: str, terminals: Set[str]) -> bool:
        """
        判断设备是否为KS类型
        规则：设备名称以K开头，且端子集合中包含A11和A12
        """
        return (device_name.startswith('K') and 
                'A11' in terminals and 'A12' in terminals)

    def get_connections(self, points: List[Dict]) -> List[Dict]:
        """生成所有连接"""
        connections = []
        # R001-1: 主线圈连接
        coil_connections = self._create_coil_connections(points)
        if coil_connections:
            connections.extend(coil_connections)

        # R001-2: NC触点连接
        nc_connections = self._create_nc_contact_connections(points)
        if nc_connections:
            connections.extend(nc_connections)

        # R001-3: NO触点连接
        no_connections = self._create_no_contact_connections(points)
        if no_connections:
            connections.extend(no_connections)

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

    def _create_coil_connections(self, points: List[Dict]) -> List[Dict]:
        """规则R001-1: 线圈连接处理"""
        connections = []
        coil_pairs = [
            ('A11', 'A12'),  # 主线圈
            ('A1', 'A2'),    # 辅助线圈
            ('S11', 'S12'),  # S11-S12
            ('S21', 'S22')   # S21-S22
        ]
        
        for term1, term2 in coil_pairs:
            point1 = self._find_terminal_points(points, term1)
            point2 = self._find_terminal_points(points, term2)
            if point1 and point2:
                connections.append(
                    self._create_connection(point1, point2, "coil")
                )
                
        return connections

    def _create_nc_contact_connections(self, points: List[Dict]) -> List[Dict]:
        """规则R001-2: NC触点连接 (*1-*2规则)"""
        connections = []
        terminals_dict = {}
        
        # 建立端子号字典
        for point in points:
            terminals_dict[point['Terminal']] = point

        # 处理NC触点对（*1-*2模式）
        for terminal in terminals_dict:
            if terminal.endswith('1'):
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

        return connections

    def _create_no_contact_connections(self, points: List[Dict]) -> List[Dict]:
        """规则R001-3: NO触点连接 (*3-*4规则)"""
        connections = []
        terminals_dict = {}
        
        # 建立端子号字典
        for point in points:
            terminals_dict[point['Terminal']] = point

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