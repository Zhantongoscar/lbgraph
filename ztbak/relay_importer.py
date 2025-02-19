"""
继电器导入处理模块
"""
from neo4j import GraphDatabase
from relay_rules import create_relay_structure, parse_relay_model

class RelayImporter:
    def __init__(self, driver):
        self.driver = driver
        self.created_relays = set()  # 跟踪已创建的继电器
        self._ensure_indices()  # 创建必要的索引
        self.device_terminals = {}  # 存储设备及其端子信息

    def _ensure_indices(self):
        """确保必要的索引存在"""
        with self.driver.session() as session:
            # 为各种节点类型创建索引
            indices = [
                "CREATE INDEX relay_name IF NOT EXISTS FOR (n:Relay) ON (n.name)",
                "CREATE INDEX vertex_name IF NOT EXISTS FOR (n:Vertex) ON (n.name)",
                "CREATE INDEX coil_name IF NOT EXISTS FOR (n:CoilTerminal) ON (n.name)",
                "CREATE INDEX contact_name IF NOT EXISTS FOR (n:ContactTerminal) ON (n.name)"
            ]
            
            for query in indices:
                try:
                    session.run(query)
                except Exception as e:
                    print(f"Warning: Failed to create index: {str(e)}")

    def collect_device_terminals(self, device_id, terminal_id):
        """收集设备的端子信息
        Args:
            device_id: 设备ID
            terminal_id: 端子ID
        """
        if device_id not in self.device_terminals:
            self.device_terminals[device_id] = set()
        self.device_terminals[device_id].add(terminal_id)

    def process_relay(self, device_id):
        """处理继电器，如果需要则创建完整结构"""
        if device_id in self.created_relays:
            return

        try:
            with self.driver.session() as session:
                # 使用收集的端子信息进行特征分析
                terminals = self.device_terminals.get(device_id, set())
                relay_type, config = parse_relay_model(device_id, terminals)
                
                # 创建继电器结构
                structure = create_relay_structure(device_id, config)
                
                # 创建节点
                for node in structure['nodes']:
                    query = (
                        "MERGE (n:%s {name: $name}) "
                        "SET n += $properties "
                        "RETURN n" % ':'.join(node['labels'])
                    )
                    session.run(query,
                        name=node['id'],
                        properties=node['properties']
                    )
                
                # 创建关系
                for rel in structure['relationships']:
                    query = (
                        "MATCH (a {name: $source_name}), (b {name: $target_name}) "
                        f"MERGE (a)-[r:{rel['type']}]->(b) "
                        "SET r += $properties "
                        "RETURN r"
                    )
                    result = session.run(query,
                        source_name=rel['from'],
                        target_name=rel['to'],
                        properties=rel.get('properties', {})
                    )
                    if not result.single():
                        print(f"Warning: Failed to create relationship: {rel['from']} -> {rel['to']}")
                        
                self.created_relays.add(device_id)
                        
        except Exception as e:
            print(f"Error creating relay structure for {device_id}: {str(e)}")
            self._diagnose_relay_creation(session, device_id, structure)

    def _diagnose_relay_creation(self, session, device_id, structure):
        """诊断继电器创建问题"""
        print("\nDiagnosing relay creation issues:")
        
        # 检查继电器本体
        query = """
        MATCH (n:Relay {name: $name}) 
        RETURN n.name, labels(n)
        """
        result = session.run(query, name=device_id).single()
        print(f"Relay node exists: {bool(result)}")
        
        # 检查端子节点
        for node in structure['nodes'][1:]:
            query = """
            MATCH (n {name: $name}) 
            RETURN n.name, labels(n)
            """
            result = session.run(query, name=node['id']).single()
            print(f"Terminal node {node['id']} exists: {bool(result)}")
            
    def connect_terminals(self, source_device, source_terminal, target_device, target_terminal, wire_props):
        """连接两个端子"""
        with self.driver.session() as session:
            # 构建完整的端子名称
            source_name = f"{source_device}:{source_terminal}"
            target_name = f"{target_device}:{target_terminal}"
            
            print(f"Connecting: {source_name} -> {target_name}")
            print(f"Wire properties: {wire_props}")
            
            try:
                # 首先确保两个端子都存在
                for name in [source_name, target_name]:
                    check_query = """
                    MERGE (n:Vertex {name: $name})
                    ON CREATE SET n.created = timestamp()
                    RETURN n
                    """
                    session.run(check_query, name=name)
                
                # 创建连接关系
                query = """
                MATCH (s:Vertex {name: $source_name})
                MATCH (t:Vertex {name: $target_name})
                MERGE (s)-[r:CONNECTED_TO]->(t)
                SET r += $wire_props
                RETURN r
                """
                result = session.run(
                    query,
                    source_name=source_name,
                    target_name=target_name,
                    wire_props=wire_props
                )
                
                if not result.single():
                    raise Exception("Failed to create connection relationship")
                    
            except Exception as e:
                print(f"Error connecting terminals: {str(e)}")
                self._diagnose_connection(session, source_name, target_name)
                
    def _diagnose_connection(self, session, source_name, target_name):
        """诊断连接问题"""
        print("\nDiagnosing connection issues:")
        
        # 检查端子节点是否存在
        for name in [source_name, target_name]:
            query = """
            MATCH (n:Vertex {name: $name})
            RETURN n.name, labels(n)
            """
            result = session.run(query, name=name).single()
            print(f"Terminal {name} exists: {bool(result)}")
            if result:
                print(f"Labels: {result['labels(n)']}")