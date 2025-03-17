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

    def detect_features(self, device_name: str, terminals: Set[str]) -> str:
        """
        检测设备特征
        返回: 设备特征描述
        """
        if device_name.startswith('K'):
            # 检查是否存在安全继电器特征端子对
            has_s11_s12 = {'S11', 'S12'}.issubset(terminals)
            has_s21_s22 = {'S21', 'S22'}.issubset(terminals)
            has_a11_a12 = {'A11', 'A12'}.issubset(terminals)
            
            if has_s11_s12 or has_s21_s22 or has_a11_a12:
                reason = []
                if has_a11_a12:
                    reason.append("包含主线圈端子对: A11-A12")
                if has_s11_s12:
                    reason.append("包含安全端子对: S11-S12")
                if has_s21_s22:
                    reason.append("包含安全端子对: S21-S22")
                
                return "KS安全继电器"
        return "标准设备"

    def match(self, device_name: str, terminals: Set[str]) -> bool:
        """
        判断设备是否为K类型
        规则：设备名称以K开头
        """
        return device_name.startswith('K')

    def get_connections(self, points: List[Dict]) -> List[Dict]:
        """生成所有连接"""
        connections = []
        
        # 检查是否为安全继电器（通过端子对判断）
        is_safety_relay = False
        terminal_set = {p['Terminal'].split(':')[-1] for p in points}
        
        # 检查特征端子对
        has_a11_a12 = {'A11', 'A12'}.issubset(terminal_set)
        has_s11_s12 = {'S11', 'S12'}.issubset(terminal_set)
        has_s21_s22 = {'S21', 'S22'}.issubset(terminal_set)
        
        # 检查是否有任何S*1-S*2对
        has_s_pattern = False
        s_terminals = [t for t in terminal_set if t.startswith('S')]
        for term in s_terminals:
            if term.endswith('1'):
                other = term[:-1] + '2'
                if other in terminal_set:
                    has_s_pattern = True
                    break
        
        is_safety_relay = has_a11_a12 or has_s11_s12 or has_s21_s22 or has_s_pattern
        
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

    def _create_safety_connections(self, points: List[Dict]) -> List[Dict]:
        """创建安全继电器特有的连接"""
        connections = []
        terminals_dict = {}
        
        # 建立端子号字典
        for point in points:
            terminal = point['Terminal']
            if ':' in terminal:
                terminal = terminal.split(':')[-1]
            terminals_dict[terminal] = point

        # 处理固定的安全线圈对
        if 'A11' in terminals_dict and 'A12' in terminals_dict:
            connections.append(
                self._create_connection(
                    terminals_dict['A11'],
                    terminals_dict['A12'],
                    "coil"
                )
            )

        # 处理所有S开头的安全线圈（S*1-S*2）
        for terminal in terminals_dict:
            if terminal.startswith('S') and terminal.endswith('1'):
                base = terminal[:-1]  # 去掉最后的1
                other = base + '2'
                if other in terminals_dict:
                    connections.append(
                        self._create_connection(
                            terminals_dict[terminal],
                            terminals_dict[other],
                            "coil"
                        )
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
            
        # 0-1 coil连接
        point_0 = self._find_terminal_points(points, '0')
        point_1 = self._find_terminal_points(points, '1')
        if point_0 and point_1:
            connections.append(
                self._create_connection(point_0, point_1, "coil")
            )

        # A-0 NC连接
        point_a = self._find_terminal_points(points, 'A')
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

    def _find_terminal_points(self, points: List[Dict], terminal: str) -> Optional[Dict]:
        """查找指定端子的点位"""
        for point in points:
            if point['Terminal'].endswith(terminal):
                return point
        return None

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

        # 处理标准端子（11-12为NC，11-14为NO）
        if '11' in terminals_dict:
            # 处理NC连接（11-12）
            if '12' in terminals_dict:
                connections.append(
                    self._create_connection(
                        terminals_dict['11'],
                        terminals_dict['12'],
                        "NC"
                    )
                )
            # 处理NO连接（11-14）
            if '14' in terminals_dict:
                connections.append(
                    self._create_connection(
                        terminals_dict['11'],
                        terminals_dict['14'],
                        "NO"
                    )
                )

        # 处理NC触点对（*1-*2模式）
        for terminal in terminals_dict:
            if terminal.endswith('1') and terminal != '11':  # 跳过11，因为已经单独处理
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
                    
        # 处理NO触点对（*3-*4模式、*1-*4模式和*5-*6模式）
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
            elif terminal.endswith('1') and terminal != '11':  # 跳过11，因为已经单独处理
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
            # 处理5-6连接
            elif terminal == '5' and '6' in terminals_dict:
                connections.append(
                    self._create_connection(
                        terminals_dict['5'],
                        terminals_dict['6'],
                        "NO"
                    )
                )

        return connections

class QRule(DeviceRule):
    """Q类设备规则 R002"""

    def __init__(self):
        super().__init__(
            "R002",
            "Q类设备规则",
            "Q类设备的连接规则",
            priority=2
        )

    def match(self, device_name: str, terminals: Set[str]) -> bool:
        """
        判断设备是否为Q类型
        规则：设备名称以Q开头
        """
        return device_name.startswith('Q')

    def get_connections(self, points: List[Dict]) -> List[Dict]:
        """生成所有连接"""
        connections = []
        terminals_dict = {}
        
        # 建立端子号字典
        for point in points:
            terminal = point['Terminal']
            if ':' in terminal:
                terminal = terminal.split(':')[-1]
            terminals_dict[terminal] = point

        # D1-D2 coil连接
        if 'D1' in terminals_dict and 'D2' in terminals_dict:
            connections.append(
                self._create_connection(
                    terminals_dict['D1'],
                    terminals_dict['D2'],
                    "coil"
                )
            )

        # L*-T*对的NO连接
        for i in range(1, 4):  # 处理L1-T1, L2-T2, L3-T3
            l_term = f'L{i}'
            t_term = f'T{i}'
            if l_term in terminals_dict and t_term in terminals_dict:
                connections.append(
                    self._create_connection(
                        terminals_dict[l_term],
                        terminals_dict[t_term],
                        "NO"
                    )
                )

        # 标准NO连接对
        no_pairs = [
            ('3.13', '3.14'),  # 3.13-3.14
            ('13', '14'),      # 13-14
            ('1', '2'),        # 1-2
            ('3', '4'),        # 3-4
            ('5', '6')         # 5-6
        ]
        
        for first, second in no_pairs:
            if first in terminals_dict and second in terminals_dict:
                connections.append(
                    self._create_connection(
                        terminals_dict[first],
                        terminals_dict[second],
                        "NO"
                    )
                )

        return connections

class SRule(DeviceRule):
    """S类设备规则 R003"""

    def __init__(self):
        super().__init__(
            "R003",
            "S类设备规则",
            "S类设备的连接规则",
            priority=2
        )

    def match(self, device_name: str, terminals: Set[str]) -> bool:
        """
        判断设备是否为S类型
        规则：设备名称以S开头
        """
        return device_name.startswith('S')

    def get_connections(self, points: List[Dict]) -> List[Dict]:
        """生成所有连接"""
        connections = []
        terminals_dict = {}
        
        # 建立端子号字典
        for point in points:
            terminal = point['Terminal']
            if ':' in terminal:
                terminal = terminal.split(':')[-1]
            terminals_dict[terminal] = point

        # 处理NO连接（*3-*4模式）
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

        # 处理NO连接（*1-*2模式）
        for terminal in terminals_dict:
            if terminal.endswith('1'):
                base = terminal[:-1]
                other = base + '2'
                if other in terminals_dict:
                    connections.append(
                        self._create_connection(
                            terminals_dict[terminal],
                            terminals_dict[other],
                            "NO"
                        )
                    )

        return connections

def create_device_rule(device_name: str) -> Optional[DeviceRule]:
    """根据设备名称创建对应的规则实例"""
    if device_name.startswith('K'):
        return KSRule()
    elif device_name.startswith('S'):
        return SRule()
    elif device_name.startswith('Q'):
        return QRule()
    return None

if __name__ == "__main__":
    # 测试代码
    ks_rule = KSRule()
    print(f"规则ID: {ks_rule.rule_id}")
    print(f"规则名称: {ks_rule.name}")
    print(f"规则描述: {ks_rule.description}")
    print(f"规则优先级: {ks_rule.priority}")

    s_rule = SRule()
    print(f"\n规则ID: {s_rule.rule_id}")
    print(f"规则名称: {s_rule.name}")
    print(f"规则描述: {s_rule.description}")
    print(f"规则优先级: {s_rule.priority}")