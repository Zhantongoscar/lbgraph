import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List
from dataclasses import asdict
from device_types import DeviceType, get_device_type, list_device_types

class GraphElement:
    """图论元素类"""
    def __init__(self, device_type: DeviceType, device_id: str,
                 location: str = None, is_test_device: bool = False):
        self.device_type = device_type
        self.device_id = device_id
        self.location = location
        self.is_test_device = is_test_device
        self.points = []
    
    def add_point(self, point_id: str, point_type: str):
        """添加设备单元点"""
        self.points.append({
            'id': f"{self.device_id}_{point_id}",
            'type': f"{self.device_type.id}_POINT",
            'parent_device': self.device_id,
            'properties': {
                'point_type': point_type
            }
        })
    
    def to_dict(self):
        """转换为节点和单元点"""
        nodes = [{
            'id': self.device_id,
            'type': self.device_type.id,
            'name': self.device_type.name,
            'description': self.device_type.description,
            'point_count': self.device_type.point_count,
            'input_points': self.device_type.input_points,
            'output_points': self.device_type.output_points,
            'properties': {
                'location': self.location
            },
            'is_test_device': self.is_test_device
        }]
        
        # 添加输入输出点
        for point in self.device_type.input_points:
            self.add_point(point, 'input')
        for point in self.device_type.output_points:
            self.add_point(point, 'output')
            
        nodes.extend(self.points)
        return nodes

class DataPreprocessorApp:
    """数据预处理应用程序"""
    def __init__(self, root):
        self.root = root
        self.root.title("图论数据预处理")
        self.root.geometry("800x600")
        
        # 初始化变量
        self.graph_elements: List[GraphElement] = []
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 设备类型选择（第一行）
        type_frame = ttk.Frame(main_frame)
        type_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(type_frame, text="选择设备类型:").pack(side=tk.LEFT, padx=(0, 5))
        self.device_type_var = tk.StringVar()
        self.device_type_combobox = ttk.Combobox(
            type_frame, textvariable=self.device_type_var
        )
        self.device_type_combobox['values'] = [dt.id for dt in list_device_types()]
        self.device_type_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.device_type_combobox.bind("<<ComboboxSelected>>", self.update_device_id)
        
        # 设备ID输入（第二行）
        id_frame = ttk.Frame(main_frame)
        id_frame.pack(fill=tk.X, pady=5)
        ttk.Label(id_frame, text="设备ID:").pack(side=tk.LEFT, padx=(0, 5))
        self.device_id_var = tk.StringVar()
        self.device_id_entry = ttk.Entry(id_frame, textvariable=self.device_id_var)
        self.device_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 设备位置输入和测试设备标记（第三行）
        loc_frame = ttk.Frame(main_frame)
        loc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(loc_frame, text="位置:").pack(side=tk.LEFT, padx=(0, 5))
        self.location_var = tk.StringVar(value="K1S1")  # 设置默认值
        self.location_entry = ttk.Entry(loc_frame, textvariable=self.location_var)
        self.location_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 默认位置按钮
        self.default_loc_btn = ttk.Button(
            loc_frame, text="默认位置", command=self.set_default_location
        )
        self.default_loc_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 添加设备按钮
        self.add_device_btn = ttk.Button(
            type_frame, text="添加设备", command=self.add_device
        )
        self.add_device_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 设备列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.device_listbox = tk.Listbox(list_frame)
        self.device_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 保存按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        self.save_btn = ttk.Button(
            btn_frame, text="保存项目", command=self.save_project
        )
        self.save_btn.pack(fill=tk.X)
        
    def add_device(self):
        """添加设备"""
        device_id = self.device_id_var.get()
        device_type_id = self.device_type_var.get()
        location = self.location_var.get()
        if not device_id or not device_type_id:
            messagebox.showwarning("警告", "请填写设备ID并选择设备类型")
            return
            
        try:
            device_type = get_device_type(device_type_id)
            element = GraphElement(
                device_type=device_type,
                device_id=device_id,
                location=location,
                is_test_device=False
            )
            self.graph_elements.append(element)
            self.device_listbox.insert(tk.END, f"{device_id} - {device_type.name}")
            
            # 清空输入
            self.device_id_var.set('')
            self.location_var.set('')
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            
    def set_default_location(self):
        """设置默认位置K1S1"""
        self.location_var.set("K1S1")
        
    def update_device_id(self, event=None):
        """当设备类型改变时更新设备ID"""
        device_type = self.device_type_var.get()
        if device_type:
            # 设置默认ID格式：类型_
            self.device_id_var.set(f"{device_type}_")
            # 将光标定位到末尾，方便用户输入数字
            self.device_id_entry.icursor(tk.END)
            
    def save_project(self):
        """保存项目"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if not file_path:
            return
            
        # 生成节点和边
        nodes = []
        edges = []
        
        for element in self.graph_elements:
            nodes.extend(element.to_dict())
            
        # 构建完整数据结构
        data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "type": "test_devices",
                "version": "1.0"
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        messagebox.showinfo("成功", f"项目已保存到 {file_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DataPreprocessorApp(root)
    root.mainloop()