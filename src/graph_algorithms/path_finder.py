"""路径搜索算法模块"""
from typing import List, Dict, Set, Optional
from collections import defaultdict, deque

class PathFinder:
    """路径搜索类"""
    def __init__(self, nodes: List[Dict], edges: List[Dict]):
        """
        初始化路径搜索器
        
        Args:
            nodes: 节点列表，每个节点是一个字典，包含id等属性
            edges: 边列表，每个边是一个字典，包含source、target等属性
        """
        self.nodes = {node['id']: node for node in nodes}
        self.edges = edges
        self.graph = self._build_graph()
        
    def _build_graph(self) -> Dict[str, Set[str]]:
        """构建邻接表表示的图"""
        graph = defaultdict(set)
        for edge in self.edges:
            source = edge['source']
            target = edge['target']
            graph[source].add(target)
            # 如果是无向图，取消下面的注释
            # graph[target].add(source)
        return graph
        
    def find_path(self, start: str, end: str) -> Optional[List[str]]:
        """
        使用广度优先搜索查找从起点到终点的路径
        
        Args:
            start: 起点节点ID
            end: 终点节点ID
            
        Returns:
            如果找到路径，返回节点ID列表；否则返回None
        """
        if start not in self.nodes or end not in self.nodes:
            return None
            
        # 使用队列进行BFS
        queue = deque([[start]])
        visited = {start}
        
        while queue:
            path = queue.popleft()
            node = path[-1]
            
            # 找到目标节点
            if node == end:
                return path
                
            # 遍历相邻节点
            for next_node in self.graph.get(node, []):
                if next_node not in visited:
                    visited.add(next_node)
                    new_path = list(path)
                    new_path.append(next_node)
                    queue.append(new_path)
                    
        return None
        
    def find_all_paths(self, start: str, end: str, max_depth: int = 10) -> List[List[str]]:
        """
        使用深度优先搜索查找所有可能的路径
        
        Args:
            start: 起点节点ID
            end: 终点节点ID
            max_depth: 最大搜索深度，防止路径过长
            
        Returns:
            所有可能路径的列表，每个路径是节点ID的列表
        """
        def dfs(current: str, path: List[str], paths: List[List[str]], visited: Set[str]):
            if len(path) > max_depth:
                return
                
            if current == end:
                paths.append(list(path))
                return
                
            for next_node in self.graph[current]:
                if next_node not in visited:
                    visited.add(next_node)
                    path.append(next_node)
                    dfs(next_node, path, paths, visited)
                    path.pop()
                    visited.remove(next_node)
                    
        if start not in self.graph or end not in self.graph:
            return []
            
        paths = []
        dfs(start, [start], paths, {start})
        return paths