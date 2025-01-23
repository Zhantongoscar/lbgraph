from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QGraphicsView,
                             QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                             QGraphicsLineItem, QMenuBar, QMenu, QAction, QStatusBar,
                             QDialog, QTableWidget, QTableWidgetItem, QPushButton,
                             QMessageBox, QFileDialog, QGroupBox, QSplitter)
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QBrush, QColor, QPen, QPainter
import json
import os
from datetime import datetime

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图论分析工具")
        self.setMinimumSize(1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建设备管理器
        self.device_manager = TestDeviceManager(self)
        main_layout.addWidget(self.device_manager)
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menu_bar()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 添加文件菜单项
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.device_manager.load_data)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.device_manager.save_data)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

class GraphNode(QGraphicsEllipseItem):
    def __init__(self, node_id, x, y, radius=20):
        super().__init__(-radius, -radius, 2*radius, 2*radius)
        self.node_id = node_id
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(100, 150, 255)))
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setToolTip(f"节点ID: {node_id}")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                if hasattr(view, 'window'):
                    window = view.window()
                    if hasattr(window, 'statusBar'):
                        window.statusBar().showMessage(f"选中节点: {self.node_id}")
        super().mousePressEvent(event)
        
    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor(150, 200, 255)))
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(QColor(100, 150, 255)))
        super().hoverLeaveEvent(event)
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            for item in self.scene().items():
                if isinstance(item, GraphEdge):
                    if item.source_node == self or item.target_node == self:
                        item.adjust()
        return super().itemChange(change, value)

class GraphEdge(QGraphicsLineItem):
    def __init__(self, source_node, target_node):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.setPen(QPen(Qt.black, 2))
        self.setAcceptHoverEvents(True)
        self.adjust()
        
    def adjust(self):
        if not self.source_node or not self.target_node:
            return
            
        source_pos = self.source_node.pos()
        target_pos = self.target_node.pos()
        
        self.setLine(source_pos.x(), source_pos.y(),
                    target_pos.x(), target_pos.y())
                    
    def hoverEnterEvent(self, event):
        self.setPen(QPen(Qt.blue, 3))
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if hasattr(view, 'window'):
                window = view.window()
                if hasattr(window, 'statusBar'):
                    window.statusBar().showMessage(
                        f"连接: {self.source_node.node_id} -> {self.target_node.node_id}")
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        self.setPen(QPen(Qt.black, 2))
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if hasattr(view, 'window'):
                window = view.window()
                if hasattr(window, 'statusBar'):
                    window.statusBar().showMessage("")
        super().hoverLeaveEvent(event)

class GraphView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setMouseTracking(True)

    def add_node(self, node_id, x, y):
        node = GraphNode(node_id, x, y)
        self.scene.addItem(node)
        return node

    def add_edge(self, source, target):
        line = GraphEdge(source, target)
        self.scene.addItem(line)
        return line

    def wheelEvent(self, event):
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)

    def fit_scene(self):
        self.setSceneRect(self.scene.itemsBoundingRect())
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

class TestDeviceManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("测试设备管理")
        self.setMinimumSize(1000, 800)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建分割布局
        splitter_layout = QHBoxLayout()
        
        # 左侧：表格显示设备
        left_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "类型", "状态"])
        self.table.itemClicked.connect(self.on_device_selected)
        left_layout.addWidget(self.table)
        
        # 右侧：图形显示和单元管理
        right_layout = QVBoxLayout()
        
        # 图形显示区域
        self.graph_view = GraphView()
        right_layout.addWidget(self.graph_view)
        
        # 单元管理区域
        unit_group = QGroupBox("单元管理")
        unit_layout = QVBoxLayout()
        
        # 单元列表
        self.unit_list = QTreeWidget()
        self.unit_list.setHeaderLabel("设备单元")
        unit_layout.addWidget(self.unit_list)
        
        # 单元操作按钮
        unit_btn_layout = QHBoxLayout()
        btn_add_unit = QPushButton("添加单元")
        btn_add_unit.clicked.connect(self.add_unit)
        btn_delete_unit = QPushButton("删除单元")
        btn_delete_unit.clicked.connect(self.delete_unit)
        unit_btn_layout.addWidget(btn_add_unit)
        unit_btn_layout.addWidget(btn_delete_unit)
        unit_layout.addLayout(unit_btn_layout)
        
        unit_group.setLayout(unit_layout)
        right_layout.addWidget(unit_group)
        
        # 添加左右布局到分割布局
        splitter_layout.addLayout(left_layout, 1)
        splitter_layout.addLayout(right_layout, 2)
        
        main_layout.addLayout(splitter_layout)
        
        # 底部按钮布局
        btn_layout = QHBoxLayout()
        
        # 添加设备
        btn_add = QPushButton("添加设备")
        btn_add.clicked.connect(self.add_device)
        btn_layout.addWidget(btn_add)
        
        # 删除设备
        btn_delete = QPushButton("删除设备")
        btn_delete.clicked.connect(self.delete_device)
        btn_layout.addWidget(btn_delete)
        
        # 保存数据
        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self.save_data)
        btn_layout.addWidget(btn_save)
        
        # 加载数据
        btn_load = QPushButton("加载")
        btn_load.clicked.connect(self.load_data)
        btn_layout.addWidget(btn_load)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)
        
        # 初始化设备数据
        self.devices = []
        self.load_sample_data()
    
    def load_sample_data(self):
        """加载示例数据"""
        self.devices = []
        self.update_table()
        
    def on_device_selected(self, item):
        """处理设备选择事件"""
        row = item.row()
        device = self.devices[row]
        self.update_unit_list(device)
        self.update_graph_view(device)
        
    def update_unit_list(self, device):
        """更新单元列表"""
        self.unit_list.clear()
        
        # 创建设备项
        device_item = QTreeWidgetItem(self.unit_list)
        device_item.setText(0, f"{device['name']} ({device['id']})")
        
        # 添加输入/输出点
        if 'properties' in device:
            if device['properties'].get('input_points'):
                input_item = QTreeWidgetItem(device_item)
                input_item.setText(0, "输入点")
                for point in device['properties']['input_points']:
                    point_item = QTreeWidgetItem(input_item)
                    point_item.setText(0, point)
                    
            if device['properties'].get('output_points'):
                output_item = QTreeWidgetItem(device_item)
                output_item.setText(0, "输出点")
                for point in device['properties']['output_points']:
                    point_item = QTreeWidgetItem(output_item)
                    point_item.setText(0, point)
                    
    def update_graph_view(self, device):
        """更新图形视图"""
        self.graph_view.scene.clear()
        
        # 添加设备节点
        device_node = self.graph_view.add_node(device['id'], 100, 100)
        
        # 添加输入/输出点节点
        if 'properties' in device:
            y = 50
            # 添加输入点
            for i, point in enumerate(device['properties'].get('input_points', [])):
                node = self.graph_view.add_node(point, 50, y)
                self.graph_view.add_edge(node, device_node)
                y += 50
                
            y = 50
            # 添加输出点
            for i, point in enumerate(device['properties'].get('output_points', [])):
                node = self.graph_view.add_node(point, 150, y)
                self.graph_view.add_edge(device_node, node)
                y += 50
        
        self.graph_view.fit_scene()
        
    def add_unit(self):
        """添加单元"""
        selected = self.table.currentRow()
        if selected >= 0:
            device = self.devices[selected]
            
            # 获取设备类型信息
            from device_types import get_device_type
            try:
                device_type = get_device_type(device['type'].split(' - ')[0])
                
                # 添加单元属性
                if 'properties' not in device:
                    device['properties'] = {}
                
                # 根据设备类型添加输入/输出点
                device['properties']['input_points'] = device_type.input_points
                device['properties']['output_points'] = device_type.output_points
                
                # 更新显示
                self.update_unit_list(device)
                self.update_graph_view(device)
                
            except ValueError as e:
                QMessageBox.warning(self, "错误", str(e))
        else:
            QMessageBox.warning(self, "警告", "请先选择一个设备")
            
    def delete_unit(self):
        """删除单元"""
        selected = self.table.currentRow()
        if selected >= 0:
            device = self.devices[selected]
            
            # 清除单元属性
            if 'properties' in device:
                device['properties'] = {}
            
            # 更新显示
            self.update_unit_list(device)
            self.update_graph_view(device)
        else:
            QMessageBox.warning(self, "警告", "请先选择一个设备")
            
    def update_table(self):
        """更新表格显示"""
        self.table.setRowCount(len(self.devices))
        for row, device in enumerate(self.devices):
            self.table.setItem(row, 0, QTableWidgetItem(device["id"]))
            self.table.setItem(row, 1, QTableWidgetItem(device["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(device["type"]))
            self.table.setItem(row, 3, QTableWidgetItem(device["status"]))
    
    def add_device(self):
        """添加新设备"""
        from PyQt5.QtWidgets import QInputDialog
        from device_types import DEVICE_TYPES
        
        # 获取设备信息
        name, ok = QInputDialog.getText(self, "添加设备", "请输入设备名称:")
        if ok and name:
            device_types = [f"{dt.id} - {dt.name}" for dt in DEVICE_TYPES.values()]
            device_type, ok = QInputDialog.getItem(
                self, "选择类型", "请选择设备类型:", device_types, 0, False)
            
            if ok and device_type:
                # 生成唯一ID
                new_id = f"{len(self.devices)+1:03d}"
                new_device = {
                    "id": new_id,
                    "name": name,
                    "type": device_type,
                    "status": "正常",
                    "properties": {}
                }
                self.devices.append(new_device)
                self.update_table()
    
    def delete_device(self):
        """删除选中设备"""
        selected = self.table.currentRow()
        if selected >= 0:
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除设备 {self.devices[selected]['name']} 吗？",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                del self.devices[selected]
                self.update_table()
                self.unit_list.clear()
                self.graph_view.scene.clear()
    
    def save_data(self):
        """保存设备数据到JSON文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存设备数据", "", "JSON文件 (*.json)")
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.devices, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "成功", "设备数据已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def load_data(self):
        """从JSON文件加载设备数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载设备数据", "", "JSON文件 (*.json)")
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.devices = json.load(f)
                self.update_table()
                self.unit_list.clear()
                self.graph_view.scene.clear()
                QMessageBox.information(self, "成功", "设备数据已加载")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")
