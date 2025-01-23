import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional
from dataclasses import asdict
import json
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches
import matplotlib.collections
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import mplcursors

class GraphEditor:
    """图论编辑器主界面"""
    def __init__(self, root):
        self.root = root
        self.root.title("图论编辑器")
        self.root.geometry("1200x800")
        
        # 初始化数据
        self.cabinet_data: List[Dict] = []
        self.device_data: List[Dict] = []
        self.current_project: Optional[Dict] = None
        
        # 高亮显示相关
        self.highlighted_nodes = []
        self.highlighted_edge = None
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧工作区
        self.workspace = ttk.Frame(main_frame)
        self.workspace.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 图形显示区域
        self.figure = plt.Figure(figsize=(6, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, self.workspace)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 初始化图形
        self.graph = nx.Graph()
        
        # 右侧素材区
        self.material_panel = ttk.Frame(main_frame, width=300)
        self.material_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # 素材区选项卡
        self.material_notebook = ttk.Notebook(self.material_panel)
        self.material_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 电柜素材
        self.cabinet_frame = ttk.Frame(self.material_notebook)
        self.material_notebook.add(self.cabinet_frame, text="电柜")
        
        # 设备素材
        self.device_frame = ttk.Frame(self.material_notebook)
        self.material_notebook.add(self.device_frame, text="设备")
        
        # 创建菜单栏
        self.create_menu()
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新建", command=self.new_project)
        file_menu.add_command(label="打开...", command=self.open_project)
        file_menu.add_command(label="保存", command=self.save_project)
        file_menu.add_command(label="关闭", command=self.close_project)
        file_menu.add_command(label="删除", command=self.delete_project)
        file_menu.add_separator()
        file_menu.add_command(label="导入电柜数据...", command=self.import_cabinet_data)
        file_menu.add_command(label="导入仿真设备...", command=self.import_device_data)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        self.root.config(menu=menubar)
        
    def import_cabinet_data(self):
        """导入电柜数据"""
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if file_path:
            self.load_cabinet_data(file_path)
            
    def import_device_data(self):
        """导入仿真设备"""
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if file_path:
            self.load_device_data(file_path)
        
    def new_project(self):
        """新建项目"""
        self.current_project = {
            'name': '未命名项目',
            'cabinets': [],
            'devices': [],
            'connections': []
        }
        self.update_title()
        messagebox.showinfo("成功", "已创建新项目")
        
    def open_project(self):
        """打开项目"""
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.current_project = json.load(f)
                    if 'name' not in self.current_project:
                        self.current_project['name'] = '未命名项目'
                    self.update_title()
                    messagebox.showinfo("成功", f"已打开项目: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"打开项目失败: {str(e)}")
                
    def save_project(self):
        """保存项目"""
        if not self.current_project:
            messagebox.showwarning("警告", "没有可保存的项目")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_project, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", f"项目已保存到: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存项目失败: {str(e)}")
                
    def update_title(self):
        """更新窗口标题"""
        base_title = "图论编辑器"
        if self.current_project:
            if hasattr(self.current_project, 'name'):
                self.root.title(f"{base_title} - {self.current_project['name']}")
            else:
                self.root.title(f"{base_title} - 未命名项目")
        else:
            self.root.title(base_title)
            
    def close_project(self):
        """关闭项目"""
        if self.current_project:
            self.current_project = None
            self.graph.clear()
            self.update_graph()
            self.update_title()
            messagebox.showinfo("成功", "已关闭当前项目")
        else:
            messagebox.showwarning("警告", "没有打开的项目")
            
    def delete_project(self):
        """删除项目"""
        if self.current_project:
            self.current_project = None
            self.graph.clear()
            self.update_graph()
            self.update_title()
            messagebox.showinfo("成功", "已删除当前项目")
        else:
            messagebox.showwarning("警告", "没有可删除的项目")
            
    def load_cabinet_data(self, file_path: str):
        """加载电柜数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 添加节点
                for node in data['nodes']:
                    if 'id' in node:
                        node_attrs = node.copy()
                        node_attrs['node_type'] = 'cabinet'
                        self.graph.add_node(node['id'], **node_attrs)
                    else:
                        print(f"警告: 跳过无ID的节点: {node}")
                
                # 添加边
                for edge in data['edges']:
                    if 'source' in edge and 'target' in edge:
                        edge_attrs = edge.get('properties', {})
                        self.graph.add_edge(edge['source'], edge['target'], **edge_attrs)
                    else:
                        print(f"警告: 跳过无效的边: {edge}")
                        
                self.update_graph()
                self.update_material_panel()
                messagebox.showinfo("成功", f"已加载电柜数据: {file_path}")
        except json.JSONDecodeError as e:
            messagebox.showerror("错误", f"JSON格式错误: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"加载电柜数据失败: {str(e)}\n\n详细信息: {type(e).__name__}")
            print(f"详细错误: {e}")
            
    def load_device_data(self, file_path: str):
        """加载设备数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查数据格式
                if 'nodes' in data:
                    self.device_data = data['nodes']
                else:
                    self.device_data = data
                
                # 将设备数据添加到图中
                for device in self.device_data:
                    if 'id' in device:
                        node_attrs = device.copy()
                        node_attrs['node_type'] = 'device'  # 使用node_type而不是type
                        self.graph.add_node(device['id'], **node_attrs)
                    else:
                        print(f"警告: 跳过无ID的节点: {device}")
                        
                self.update_graph()
                self.update_material_panel()
                messagebox.showinfo("成功", f"已加载设备数据: {file_path}")
        except json.JSONDecodeError as e:
            messagebox.showerror("错误", f"JSON格式错误: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"加载设备数据失败: {str(e)}\n\n详细信息: {type(e).__name__}")
            print(f"详细错误: {e}")
            
    def update_graph(self):
        """更新图形显示"""
        self.ax.clear()
        
        # 设置节点颜色
        colors = []
        labels = {}
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('node_type', 'unknown')
            if node_type == 'cabinet':
                colors.append('lightblue')
            elif node_type == 'device':
                colors.append('lightgreen')
            else:
                colors.append('gray')
            # 收集节点信息
            labels[node] = f"ID: {node}\nType: {node_type}"
        
        # 绘制图形
        pos = nx.spring_layout(self.graph, k=0.15, iterations=50)  # 调整布局参数
        nx.draw(self.graph, pos, ax=self.ax, with_labels=False,
                node_size=50 if len(self.graph.nodes) > 100 else 200,  # 动态调整节点大小
                node_color=colors, edge_color='gray', width=1, alpha=0.8,
                linewidths=0.5)
        
        # 添加缩放功能
        def on_scroll(event):
            scale = 1.1 if event.button == 'up' else 0.9
            self.ax.set_xlim(self.ax.get_xlim()[0]*scale, self.ax.get_xlim()[1]*scale)
            self.ax.set_ylim(self.ax.get_ylim()[0]*scale, self.ax.get_ylim()[1]*scale)
            self.canvas.draw()
            
        self.canvas.mpl_connect('scroll_event', on_scroll)
        
        # 添加鼠标悬停显示信息
        import mplcursors
        cursor = mplcursors.cursor(self.ax, hover=True)
        
        # 存储当前高亮的节点和边
        self.highlighted_nodes = []
        self.highlighted_edge = None
        
        @cursor.connect("add")
        def on_add(sel):
            try:
                if isinstance(sel.artist, matplotlib.collections.PathCollection):  # 处理节点
                    nodes = list(self.graph.nodes(data=True))
                    node_idx = int(sel.target[0])
                    if 0 <= node_idx < len(nodes):
                        node, data = nodes[node_idx]
                        # 显示节点的所有属性
                        text = f"Node: {node}\n"
                        if data:
                            text += "\n".join(f"{k}: {v}" for k, v in data.items())
                        sel.annotation.set_text(text)
                        
                elif isinstance(sel.artist, matplotlib.collections.LineCollection):  # 处理边
                    edges = list(self.graph.edges(data=True))
                    edge_idx = int(sel.target[0])
                    if 0 <= edge_idx < len(edges):
                        u, v, d = edges[edge_idx]
                        # 高亮显示相连的节点和边
                        self.highlighted_nodes = [u, v]
                        self.highlighted_edge = (u, v)
                        # 更新节点和边的颜色
                        colors = []
                        for node in self.graph.nodes():
                            if node in self.highlighted_nodes:
                                colors.append('red')
                            else:
                                node_type = self.graph.nodes[node].get('node_type', 'unknown')
                                if node_type == 'cabinet':
                                    colors.append('lightblue')
                                elif node_type == 'device':
                                    colors.append('lightgreen')
                                else:
                                    colors.append('gray')
                        
                        nx.draw_networkx_nodes(self.graph, pos, node_color=colors, ax=self.ax)
                        edge_colors = ['red' if (e[0], e[1]) == self.highlighted_edge else 'gray'
                                     for e in self.graph.edges()]
                        nx.draw_networkx_edges(self.graph, pos, edge_color=edge_colors, ax=self.ax)
                        self.canvas.draw()
                        
                        # 显示边的信息
                        text = f"Edge: {u} -> {v}\n"
                        if d:
                            text += "\n".join(f"{k}: {v}" for k, v in d.items())
                        sel.annotation.set_text(text)
                        
            except (AttributeError, TypeError, IndexError, ValueError) as e:
                print(f"Error in on_add: {e}")
                return
            
            sel.annotation.get_bbox_patch().set(fc="white", alpha=0.9)
        
        # 刷新画布
        self.canvas.draw()
        
    def update_material_panel(self):
        """更新素材面板"""
        # TODO: 实现素材面板更新逻辑
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = GraphEditor(root)
    root.mainloop()