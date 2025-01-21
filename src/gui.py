from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTreeWidget, QTreeWidgetItem, QGraphicsView,
                            QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                            QGraphicsLineItem, QMenuBar, QMenu, QAction, QStatusBar)
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QBrush, QColor, QPen, QPainter
import json
import os

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
        
        # 加载示例数据
        self.load_sample_data()
        
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 导入数据
        import_menu = file_menu.addMenu("导入数据")
        
        # 导入Excel
        import_excel_action = QAction("导入Excel", self)
        import_excel_action.triggered.connect(self.import_excel)
        import_menu.addAction(import_excel_action)
        
        # 导入JSON
        import_json_action = QAction("导入JSON", self)
        import_json_action.triggered.connect(self.open_file)
        import_menu.addAction(import_json_action)
        
        # 保存配置
        save_action = QAction("保存配置", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        # 工具菜单
        tool_menu = menubar.addMenu("工具")
        
        # Excel转换
        excel_convert_action = QAction("Excel转换", self)
        excel_convert_action.triggered.connect(self.convert_excel)
        tool_menu.addAction(excel_convert_action)
        
        # 设备配置
        device_config_action = QAction("设备配置", self)
        device_config_action.triggered.connect(self.configure_devices)
        tool_menu.addAction(device_config_action)
        
        # 设备菜单
        device_menu = menubar.addMenu("设备")
        
        # 添加设备
        add_device_action = QAction("添加设备", self)
        add_device_action.triggered.connect(self.add_device)
        device_menu.addAction(add_device_action)
        
        # 管理单元
        manage_units_action = QAction("管理单元", self)
        manage_units_action.triggered.connect(self.manage_units)
        device_menu.addAction(manage_units_action)
        
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
        
    def import_excel(self):
        """导入Excel数据"""
        from gui_data_processor import GuiDataProcessor
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel文件 (*.xlsx *.xls)")
            
        if file_path:
            processor = GuiDataProcessor()
            if processor.load_data(file_path, self):
                # 加载处理后的数据
                graph_data = processor.process_data({}, self)
                if graph_data:
                    # 清空现有数据
                    self.graph_view.scene.clear()
                    
                    # 创建节点
                    nodes = {}
                    x, y = 100, 100
                    for node in graph_data['nodes']:
                        node_item = self.graph_view.add_node(node['id'], x, y)
                        nodes[node['id']] = node_item
                        x = (x + 150) % 800  # 避免节点重叠
                        if x < 150:
                            y += 150
                            
                    # 创建边
                    for edge in graph_data['edges']:
                        source = nodes.get(edge['source'])
                        target = nodes.get(edge['target'])
                        if source and target:
                            self.graph_view.add_edge(source, target)
                            
                    # 调整视图以适应所有内容
                    self.graph_view.fit_scene()
                            
                    self.statusBar().showMessage(f"成功导入Excel文件: {file_path}")
                
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
                
    def save_file(self):
        """保存配置文件"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存配置文件", "", "JSON文件 (*.json)")
            
        if file_path:
            try:
                data = {}  # TODO: 获取当前配置数据
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.statusBar().showMessage(f"成功保存配置文件: {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"保存失败: {str(e)}")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())