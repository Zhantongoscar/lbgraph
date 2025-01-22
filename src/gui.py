from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QGraphicsView,
                             QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                             QGraphicsLineItem, QMenuBar, QMenu, QAction, QStatusBar)
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QBrush, QColor, QPen, QPainter
import json
import os
from datetime import datetime

class GraphNode(QGraphicsEllipseItem):
    def __init__(self, node_id, x, y, radius=20):
        super().__init__(-radius, -radius, 2*radius, 2*radius)
        self.node_id = node_id
        self.setPos(x, y)
        self.setBrush(QBrush(QColor(100, 150, 255)))
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)  # 启用悬浮事件
        self.setToolTip(f"节点ID: {node_id}")  # 添加工具提示
        
    def mousePressEvent(self, event):
        """单击事件"""
        if event.button() == Qt.LeftButton:
            # 在状态栏显示节点信息
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                if hasattr(view, 'window'):
                    window = view.window()
                    if hasattr(window, 'statusBar'):
                        window.statusBar().showMessage(f"选中节点: {self.node_id}")
        super().mousePressEvent(event)
        
    def hoverEnterEvent(self, event):
        """鼠标进入事件"""
        self.setBrush(QBrush(QColor(150, 200, 255)))  # 高亮显示
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """鼠标离开事件"""
        self.setBrush(QBrush(QColor(100, 150, 255)))  # 恢复原色
        super().hoverLeaveEvent(event)
        
    def itemChange(self, change, value):
        """处理节点位置变化"""
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # 更新连接到此节点的所有边
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
        self.setAcceptHoverEvents(True)  # 启用悬浮事件
        self.adjust()  # 初始化边的位置
        
    def adjust(self):
        """更新边的位置"""
        if not self.source_node or not self.target_node:
            return
            
        # 获取源节点和目标节点的中心点
        source_pos = self.source_node.pos()
        target_pos = self.target_node.pos()
        
        # 设置线段的起点和终点
        self.setLine(source_pos.x(), source_pos.y(),
                    target_pos.x(), target_pos.y())
                    
    def hoverEnterEvent(self, event):
        """鼠标进入事件"""
        self.setPen(QPen(Qt.blue, 3))  # 高亮显示
        # 显示连接信息
        if self.scene() and self.scene().views():
            view = self.scene().views()[0]
            if hasattr(view, 'window'):
                window = view.window()
                if hasattr(window, 'statusBar'):
                    window.statusBar().showMessage(
                        f"连接: {self.source_node.node_id} -> {self.target_node.node_id}")
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """鼠标离开事件"""
        self.setPen(QPen(Qt.black, 2))  # 恢复原色
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
        self.setDragMode(QGraphicsView.ScrollHandDrag)  # 允许拖拽移动视图
        self.setMouseTracking(True)  # 启用鼠标追踪，用于悬浮事件

    def add_node(self, node_id, x, y):
        node = GraphNode(node_id, x, y)
        self.scene.addItem(node)
        return node

    def add_edge(self, source, target):
        line = GraphEdge(source, target)
        self.scene.addItem(line)
        return line

    def wheelEvent(self, event):
        """实现鼠标滚轮缩放"""
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)

    def fit_scene(self):
        """调整视图以适应场景内容"""
        self.setSceneRect(self.scene.itemsBoundingRect())
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图论配置工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # 设备树
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabel("设备单元")
        layout.addWidget(self.device_tree, 1)
        
        # 图论视图
        self.graph_view = GraphView()
        layout.addWidget(self.graph_view, 3)
        
        # 创建菜单栏
        self.create_menus()
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 初始化空项目
        self.device_tree.clear()
        self.graph_view.scene.clear()
        if hasattr(self, 'device_processor'):
            self.device_processor.devices = []
        self.setWindowTitle("图论配置工具 - 新项目")
        
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 导入数据
        import_menu = file_menu.addMenu("导入数据")
        
        # 导入图书json
        import_book_action = QAction("导入图书json", self)
        import_book_action.triggered.connect(self.import_book_json)
        import_menu.addAction(import_book_action)
        
        # 导入设备json
        import_device_action = QAction("导入设备json", self)
        import_device_action.triggered.connect(self.import_device_json)
        import_menu.addAction(import_device_action)
        
        # 新建项目
        new_project_action = QAction("新建项目", self)
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)

        # 读取项目
        load_project_action = QAction("读取项目", self)
        load_project_action.triggered.connect(self.load_project)
        file_menu.addAction(load_project_action)

        # 保存项目
        # 保存项目
        save_project_action = QAction("保存项目", self)
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)

        # 删除项目
        delete_project_action = QAction("删除项目", self)
        delete_project_action.triggered.connect(self.delete_project)
        file_menu.addAction(delete_project_action)

        # 工具菜单
        # 工具菜单
        tool_menu = menubar.addMenu("工具")
        
        # Excel转换
        excel_convert_action = QAction("Excel转换", self)
        excel_convert_action.triggered.connect(self.convert_excel)
        tool_menu.addAction(excel_convert_action)
        
        # 设备管理菜单
        device_menu = menubar.addMenu("设备管理")
        
        # 设备操作
        add_device_action = QAction("添加设备", self)
        add_device_action.triggered.connect(self.add_device)
        device_menu.addAction(add_device_action)

        edit_device_action = QAction("编辑设备", self)
        edit_device_action.triggered.connect(self.edit_device)
        device_menu.addAction(edit_device_action)

        delete_device_action = QAction("删除设备", self)
        delete_device_action.triggered.connect(self.delete_device)
        device_menu.addAction(delete_device_action)

        # 设备配置（从原工具菜单迁移）
        device_config_action = QAction("设备配置", self)
        device_config_action.triggered.connect(self.configure_devices)
        device_menu.addAction(device_config_action)

        # 管理单元子菜单
        unit_submenu = device_menu.addMenu("单元管理")
        manage_units_action = QAction("单元配置", self)
        manage_units_action.triggered.connect(self.manage_units)
        unit_submenu.addAction(manage_units_action)

        monitor_units_action = QAction("单元监控", self)
        monitor_units_action.triggered.connect(self.monitor_units)
        unit_submenu.addAction(monitor_units_action)

        # 测试管理菜单
        test_menu = menubar.addMenu("测试管理")
        
        new_test_action = QAction("新建测试", self)
        new_test_action.triggered.connect(self.new_test)
        test_menu.addAction(new_test_action)

        open_test_action = QAction("打开测试", self)
        open_test_action.triggered.connect(self.open_test)
        test_menu.addAction(open_test_action)

        delete_test_action = QAction("删除测试", self)
        delete_test_action.triggered.connect(self.delete_test)
        test_menu.addAction(delete_test_action)
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # 用户手册
        manual_action = QAction("用户手册", self)
        manual_action.triggered.connect(self.show_manual)
        help_menu.addAction(manual_action)
        
    def load_sample_data(self):
        """加载示例数据并初始化图论视图"""
        # 清空现有数据
        self.device_tree.clear()
        self.graph_view.scene.clear()
        
        # 添加示例设备
        root = QTreeWidgetItem(self.device_tree, ["设备组1"])
        for i in range(3):
            item = QTreeWidgetItem(root, [f"设备{i+1}"])
            for j in range(2):
                QTreeWidgetItem(item, [f"单元{j+1}"])
                
        # 添加示例图论节点
        node1 = self.graph_view.add_node("Node1", 100, 100)
        node2 = self.graph_view.add_node("Node2", 300, 200)
        node3 = self.graph_view.add_node("Node3", 200, 300)
        
        # 添加示例边
        self.graph_view.add_edge(node1, node2)
        self.graph_view.add_edge(node2, node3)
        self.graph_view.add_edge(node3, node1)
        
        # 调整视图以适应内容
        self.graph_view.fit_scene()
        
    def get_row_count(self, file_path):
        """获取Excel文件的行数"""
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            return len(df)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取Excel文件失败: {str(e)}")
            return None
            
    def convert_excel(self):
        """将Excel文件转换为JSON"""
        import json
        import os
        from gui_data_processor import GuiDataProcessor
        from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox
        
        # 选择Excel文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel文件 (*.xlsx *.xls)")
            
        if not file_path:
            return
            
        # 获取文件基本信息
        file_name = os.path.basename(file_path)
        base_name = os.path.splitext(file_name)[0]
        
        # 设置默认保存路径
        os.makedirs('output', exist_ok=True)
        default_save_path = os.path.join('output', f'{base_name}.json')
        
        # 选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存JSON文件", default_save_path, "JSON文件 (*.json)")
            
        if not save_path:
            return
            
        # 获取总行数
        row_count = self.get_row_count(file_path)
        if row_count is None:
            return
            
        # 弹出对话框选择行数
        row_count, ok = QInputDialog.getInt(
            self,
            "选择转换行数",
            f"请输入要转换的行数 (1-{row_count}):",
            row_count,  # 默认值
            1,  # 最小值
            row_count,  # 最大值
            1  # 步长
        )
        
        if not ok:
            return
            
        # 处理数据
        processor = GuiDataProcessor()
        if processor.load_data(file_path, self):
            # 获取列名
            columns = processor.get_columns()
            
            # 选择必要的列
            required_columns = {
                'serial': 'Consecutive number',
                'color': 'Connection color / number',
                'source': 'Device (source)',
                'target': 'Device (target)'
            }
            
            selected_columns = {}
            for col_type, col_name in required_columns.items():
                # 尝试自动匹配列名
                matched_cols = [col for col in columns if col_name.lower() in col.lower()]
                if matched_cols:
                    default_col = matched_cols[0]
                    idx = columns.index(default_col)
                else:
                    default_col = columns[0]
                    idx = 0
                    
                col, ok = QInputDialog.getItem(
                    self,
                    f"选择{col_name}列",
                    f"请选择对应的列:",
                    columns,
                    idx,
                    False
                )
                
                if ok and col:
                    selected_columns[col_type] = col
                else:
                    self.statusBar().showMessage("取消转换")
                    return
                    
            # 处理数据
            graph_data = processor.process_data(selected_columns, self, row_count)
            if graph_data:
                # 保存处理后的数据
                if processor.save_data(graph_data, save_path, self):
                    self.statusBar().showMessage(f"成功保存JSON文件: {save_path}")
                else:
                    self.statusBar().showMessage("保存失败")
        
        # 选择Excel文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel文件 (*.xlsx *.xls)")
            
        if not file_path:
            return
            
        # 获取文件基本信息
        file_name = os.path.basename(file_path)
        base_name = os.path.splitext(file_name)[0]
        
        # 设置默认保存路径
        default_save_path = os.path.join('output', f'{base_name}.json')
        
        # 选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存JSON文件", default_save_path, "JSON文件 (*.json)")
            
        if not save_path:
            return
            
        # 选择转换行数
        row_count = self.get_row_count(file_path)
        if row_count is None:
            return
            
        # 弹出对话框选择行数
        row_count, ok = QInputDialog.getInt(
            self,
            "选择转换行数",
            f"请输入要转换的行数 (1-{row_count}):",
            row_count,  # 默认值
            1,  # 最小值
            row_count,  # 最大值
            1  # 步长
        )
        
        if not ok:
            return
            
        if file_path:
            processor = GuiDataProcessor()
            if processor.load_data(file_path, self):
                # 获取列名
                columns = processor.get_columns()
                
                # 选择必要的列
                required_columns = {
                    'serial': 'Consecutive number',
                    'color': 'Connection color / number',
                    'source': 'Device (source)',
                    'target': 'Device (target)'
                }
                
                selected_columns = {}
                for col_type, col_name in required_columns.items():
                    # 尝试自动匹配列名
                    matched_cols = [col for col in columns if col_name.lower() in col.lower()]
                    if matched_cols:
                        default_col = matched_cols[0]
                        idx = columns.index(default_col)
                    else:
                        default_col = columns[0]
                        idx = 0
                        
                    col, ok = QInputDialog.getItem(
                        self,
                        f"选择{col_name}列",
                        f"请选择对应的列:",
                        columns,
                        idx,
                        False
                    )
                    
                    if ok and col:
                        selected_columns[col_type] = col
                    else:
                        self.statusBar().showMessage("取消转换")
                        return
                        
                # 处理数据
                graph_data = processor.process_data(selected_columns, self)
                if graph_data:
                    # 保存处理后的数据
                    save_path, _ = QFileDialog.getSaveFileName(
                        self, "保存JSON文件", "", "JSON文件 (*.json)")
                    
                    if save_path:
                        if processor.save_data(graph_data, save_path, self):
                            self.statusBar().showMessage(f"成功保存JSON文件: {save_path}")
                        else:
                            self.statusBar().showMessage("保存失败")
                    else:
                        self.statusBar().showMessage("取消保存")
                        
    def configure_devices(self):
        """设备配置"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("设备配置")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # 设备表格
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["设备ID", "类型", "位置", "状态"])
        
        # TODO: 加载现有设备数据
        table.setRowCount(0)
        
        # 操作按钮
        btn_add = QPushButton("添加设备")
        btn_remove = QPushButton("删除设备")
        btn_save = QPushButton("保存配置")
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addWidget(btn_save)
        
        layout.addWidget(table)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def import_book_json(self):
        """导入图书json数据"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图书json文件", "", "JSON文件 (*.json)")
            
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    book_data = json.load(f)
                    # TODO: 处理图书数据
                    self.statusBar().showMessage(f"成功导入图书数据: {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"导入图书数据失败: {str(e)}")
                
    def import_device_json(self):
        """导入设备json数据"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择设备json文件", "", "JSON文件 (*.json)")
            
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    device_data = json.load(f)
                    # 清空现有设备数据
                    self.device_tree.clear()
                    # 加载新设备数据
                    self.device_processor = GuiDeviceProcessor()
                    self.device_processor.devices = device_data
                    self.update_device_tree()
                    self.statusBar().showMessage(f"成功导入设备数据: {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"导入设备数据失败: {str(e)}")
                
    def add_device(self):
        """添加设备"""
        from gui_device_processor import GuiDeviceProcessor
        
        if not hasattr(self, 'device_processor'):
            self.device_processor = GuiDeviceProcessor()
            
        device_id = self.device_processor.add_device_interactive(self)
        if device_id:
            # 更新设备树
            self.update_device_tree()
            # 更新状态栏
            self.statusBar().showMessage(f"已添加设备: {device_id}")
            
    def edit_device(self):
        """编辑设备"""
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        
        if not hasattr(self, 'device_processor'):
            self.device_processor = GuiDeviceProcessor()
            
        # 获取当前选中的设备
        current_item = self.device_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要编辑的设备")
            return
            
        # 从设备项文本中提取设备ID
        device_text = current_item.text(0)
        if "(" in device_text and ")" in device_text:
            device_id = device_text.split("(")[1].split(")")[0]
            
            # 获取设备信息
            device = next((d for d in self.device_processor.get_devices() if d['id'] == device_id), None)
            if device:
                # 编辑设备属性
                new_name, ok = QInputDialog.getText(self, "编辑设备", "设备名称:", text=device['name'])
                if ok and new_name:
                    device['name'] = new_name
                    # 更新设备树
                    self.update_device_tree()
                    self.statusBar().showMessage(f"已更新设备: {device_id}")
            else:
                QMessageBox.warning(self, "错误", "未找到设备信息")
        else:
            QMessageBox.warning(self, "错误", "无效的设备项")
            
    def delete_device(self):
        """删除设备"""
        from PyQt5.QtWidgets import QMessageBox
        
        if not hasattr(self, 'device_processor'):
            self.device_processor = GuiDeviceProcessor()
            
        # 获取当前选中的设备
        current_item = self.device_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要删除的设备")
            return
            
        # 从设备项文本中提取设备ID
        device_text = current_item.text(0)
        if "(" in device_text and ")" in device_text:
            device_id = device_text.split("(")[1].split(")")[0]
            
            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除设备 {device_text} 吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 从设备处理器中删除设备
                devices = self.device_processor.get_devices()
                devices = [d for d in devices if d['id'] != device_id]
                self.device_processor.devices = devices  # 更新设备列表
                
                # 更新设备树
                self.update_device_tree()
                self.statusBar().showMessage(f"已删除设备: {device_id}")
        else:
            QMessageBox.warning(self, "错误", "无效的设备项")
            
    def update_device_tree(self):
        """更新设备树"""
        if hasattr(self, 'device_processor'):
            # 清空现有设备树
            self.device_tree.clear()
            
            # 添加设备到树
            devices = self.device_processor.get_devices()
            for device in devices:
                # 创建设备项
                device_item = QTreeWidgetItem(self.device_tree)
                device_item.setText(0, f"{device['name']} ({device['id']})")
                
                # 添加设备属性
                if device['properties'].get('location'):
                    location_item = QTreeWidgetItem(device_item)
                    location_item.setText(0, f"位置: {device['properties']['location']}")
                    
                if device['properties'].get('description'):
                    desc_item = QTreeWidgetItem(device_item)
                    desc_item.setText(0, f"描述: {device['properties']['description']}")
                    
                # 添加输入/输出点
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
            
    def manage_units(self):
        """管理单元"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QMessageBox
        
        if not hasattr(self, 'device_processor'):
            self.device_processor = GuiDeviceProcessor()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("管理单元")
        layout = QVBoxLayout()
        
        # 单元列表
        unit_list = QListWidget()
        devices = self.device_processor.get_devices()
        for device in devices:
            if device['type'] == 'A_UNIT':
                unit_list.addItem(f"{device['name']} ({device['id']})")
        layout.addWidget(unit_list)
        
        # 操作按钮
        btn_add = QPushButton("添加单元")
        btn_remove = QPushButton("删除单元")
        btn_edit = QPushButton("编辑单元")
        
        def add_unit():
            device_id = self.device_processor.add_device_interactive(self)
            if device_id:
                self.update_device_tree()
                unit_list.addItem(f"{device_id}")
                
        def remove_unit():
            current = unit_list.currentItem()
            if current:
                reply = QMessageBox.question(
                    dialog,
                    "确认删除",
                    f"确定要删除选中的单元吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    unit_list.takeItem(unit_list.row(current))
                    # TODO: 实现从 device_processor 中删除单元
                    self.update_device_tree()
            else:
                QMessageBox.warning(dialog, "警告", "请先选择要删除的单元")
                
        def edit_unit():
            current = unit_list.currentItem()
            if current:
                # TODO: 实现单元编辑功能
                QMessageBox.information(dialog, "提示", "单元编辑功能开发中")
            else:
                QMessageBox.warning(dialog, "警告", "请先选择要编辑的单元")
        
        btn_add.clicked.connect(add_unit)
        btn_remove.clicked.connect(remove_unit)
        btn_edit.clicked.connect(edit_unit)
        
        layout.addWidget(btn_add)
        layout.addWidget(btn_remove)
        layout.addWidget(btn_edit)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def monitor_units(self):
        """监控单元状态"""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget,
                                   QTableWidgetItem, QPushButton, QLabel)
        from PyQt5.QtCore import QTimer
        
        dialog = QDialog(self)
        dialog.setWindowTitle("单元监控")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        
        # 状态标签
        status_label = QLabel("监控状态: 运行中")
        layout.addWidget(status_label)
        
        # 单元状态表格
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["单元ID", "名称", "类型", "状态"])
        layout.addWidget(table)
        
        def update_status():
            """更新单元状态"""
            if hasattr(self, 'device_processor'):
                devices = self.device_processor.get_devices()
                table.setRowCount(len(devices))
                for row, device in enumerate(devices):
                    # ID
                    id_item = QTableWidgetItem(device['id'])
                    table.setItem(row, 0, id_item)
                    # 名称
                    name_item = QTableWidgetItem(device['name'])
                    table.setItem(row, 1, name_item)
                    # 类型
                    type_item = QTableWidgetItem(device.get('type', 'Unknown'))
                    table.setItem(row, 2, type_item)
                    # 状态 (模拟状态)
                    import random
                    status = random.choice(['正常', '忙碌', '离线'])
                    status_item = QTableWidgetItem(status)
                    table.setItem(row, 3, status_item)
        
        # 创建定时器定期更新状态
        timer = QTimer(dialog)
        timer.timeout.connect(update_status)
        timer.start(5000)  # 每5秒更新一次
        
        # 初始更新
        update_status()
        
        # 控制按钮
        btn_refresh = QPushButton("立即刷新")
        btn_refresh.clicked.connect(update_status)
        layout.addWidget(btn_refresh)
        
        dialog.setLayout(layout)
        
        # 清理定时器
        def cleanup():
            timer.stop()
        dialog.finished.connect(cleanup)
        
        dialog.exec_()
        
    def new_test(self):
        """新建测试"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("新建测试")
        layout = QVBoxLayout()
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 测试名称输入
        test_name = QLineEdit()
        form_layout.addRow("测试名称:", test_name)
        
        # 测试描述输入
        test_desc = QLineEdit()
        form_layout.addRow("测试描述:", test_desc)
        
        layout.addLayout(form_layout)
        
        # 确认按钮
        btn_confirm = QPushButton("创建")
        def create_test():
            name = test_name.text().strip()
            desc = test_desc.text().strip()
            
            if not name:
                QMessageBox.warning(dialog, "警告", "请输入测试名称")
                return
                
            # TODO: 保存测试数据
            test_data = {
                'name': name,
                'description': desc,
                'created_at': str(datetime.now()),
                'devices': []  # 初始设备列表为空
            }
            
            self.statusBar().showMessage(f"已创建测试: {name}")
            dialog.accept()
            
        btn_confirm.clicked.connect(create_test)
        layout.addWidget(btn_confirm)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def open_test(self):
        """打开测试"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("打开测试")
        layout = QVBoxLayout()
        
        # 测试列表
        test_list = QListWidget()
        # TODO: 加载已有测试列表
        test_list.addItem("测试功能开发中")
        layout.addWidget(test_list)
        
        # 打开按钮
        btn_open = QPushButton("打开")
        def open_selected():
            current = test_list.currentItem()
            if current:
                QMessageBox.information(dialog, "提示", "测试打开功能开发中")
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "警告", "请先选择要打开的测试")
                
        btn_open.clicked.connect(open_selected)
        layout.addWidget(btn_open)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def delete_test(self):
        """删除测试"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("删除测试")
        layout = QVBoxLayout()
        
        # 测试列表
        test_list = QListWidget()
        # TODO: 加载已有测试列表
        test_list.addItem("测试功能开发中")
        layout.addWidget(test_list)
        
        # 删除按钮
        btn_delete = QPushButton("删除")
        def delete_selected():
            current = test_list.currentItem()
            if current:
                reply = QMessageBox.question(
                    dialog,
                    "确认删除",
                    "确定要删除选中的测试吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    # TODO: 实现测试删除功能
                    QMessageBox.information(dialog, "提示", "测试删除功能开发中")
                    dialog.accept()
            else:
                QMessageBox.warning(dialog, "警告", "请先选择要删除的测试")
                
        btn_delete.clicked.connect(delete_selected)
        layout.addWidget(btn_delete)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def open_file(self):
        """打开配置文件"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开配置文件", "", "JSON文件 (*.json)")
            
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # TODO: 加载配置数据
                self.statusBar().showMessage(f"成功加载配置文件: {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"加载失败: {str(e)}")
                
    def new_project(self):
        """新建项目"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 确认是否保存当前项目
        reply = QMessageBox.question(
            self,
            "新建项目",
            "是否保存当前项目？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Cancel:
            return
            
        if reply == QMessageBox.Yes:
            self.save_project()
            
    def load_project(self):
        """读取项目"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "读取项目", "", "JSON文件 (*.json)")
            
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                    
                # 清空当前数据
                self.device_tree.clear()
                self.graph_view.scene.clear()
                
                # 加载设备数据
                if 'devices' in project_data:
                    self.device_processor = GuiDeviceProcessor()
                    self.device_processor.devices = project_data['devices']
                    self.update_device_tree()
                
                # 加载图论数据
                if 'graph' in project_data:
                    nodes = {}
                    # 创建节点
                    for node_data in project_data['graph']['nodes']:
                        node = self.graph_view.add_node(
                            node_data['id'],
                            node_data['x'],
                            node_data['y']
                        )
                        nodes[node_data['id']] = node
                    
                    # 创建边
                    for edge_data in project_data['graph']['edges']:
                        source = nodes.get(edge_data['source'])
                        target = nodes.get(edge_data['target'])
                        if source and target:
                            self.graph_view.add_edge(source, target)
                    
                    # 调整视图
                    self.graph_view.fit_scene()
                
                self.statusBar().showMessage(f"成功读取项目: {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"读取项目失败: {str(e)}")
                    
    def delete_project(self):
        """删除当前项目"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除当前项目吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 清空设备数据
            self.device_tree.clear()
            if hasattr(self, 'device_processor'):
                self.device_processor.devices = []
            
            # 清空图形数据
            self.graph_view.scene.clear()
            
            # 重置状态栏
            self.statusBar().showMessage("项目已删除")
            
            # 重置窗口标题
            self.setWindowTitle("图论配置工具 - 新项目")

    def save_project(self):
            """保存项目"""
            from PyQt5.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存项目", "", "JSON文件 (*.json)")
                
            if file_path:
                try:
                    # 获取当前项目数据
                    project_data = {
                        'devices': self.device_processor.get_devices() if hasattr(self, 'device_processor') else [],
                        'graph': {
                            'nodes': [{
                                'id': item.node_id,
                                'x': item.pos().x(),
                                'y': item.pos().y()
                            } for item in self.graph_view.scene.items() if isinstance(item, GraphNode)],
                            'edges': [{
                                'source': item.source_node.node_id,
                                'target': item.target_node.node_id
                            } for item in self.graph_view.scene.items() if isinstance(item, GraphEdge)]
                        }
                    }
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(project_data, f, ensure_ascii=False, indent=2)
                    self.statusBar().showMessage(f"成功保存项目: {file_path}")
                except Exception as e:
                    self.statusBar().showMessage(f"保存失败: {str(e)}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                self.statusBar().showMessage(f"成功保存项目: {file_path}")
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                self.statusBar().showMessage(f"成功保存项目: {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"保存失败: {str(e)}")
                
    def show_about(self):
        """显示关于对话框"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(self,
            "关于图论配置工具",
            """<h3>图论配置工具 v1.0</h3>
            <p>一个用于配置和管理设备连接关系的图形化工具。</p>
            <p>基于PyQt5开发。</p>
            <p>Copyright © 2025 Leybold. All rights reserved.</p>""")
            
    def show_manual(self):
        """显示用户手册对话框"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self,
            "用户手册",
            """<h3>图论配置工具使用说明</h3>
            <p><b>基本操作：</b></p>
            <ul>
                <li>导入数据：通过"文件"菜单导入Excel或JSON格式的设备数据</li>
                <li>设备管理：使用"工具"菜单中的设备管理功能添加和配置设备</li>
                <li>图形操作：可以拖拽节点、缩放视图，鼠标悬停可查看详细信息</li>
            </ul>
            <p><b>快捷操作：</b></p>
            <ul>
                <li>鼠标滚轮：缩放视图</li>
                <li>左键拖拽：移动节点</li>
                <li>右键拖拽：平移视图</li>
            </ul>""")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())