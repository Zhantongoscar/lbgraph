from neo4j import GraphDatabase

class VirtualLayerManager:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def ensure_constraints(self):
        """确保必要的约束存在"""
        with self.driver.session() as session:
            session.run("""
                CREATE CONSTRAINT IF NOT EXISTS
                FOR (vl:VirtualLayer) REQUIRE vl.name IS UNIQUE
            """)

    def cleanup_virtual_layer(self):
        """清理虚拟层节点和关系"""
        # 首先确保约束存在
        self.ensure_constraints()
        
        with self.driver.session() as session:
            session.execute_write(self._cleanup_virtual_layer_tx)

    def create_virtual_layer(self):
        """创建新的虚拟层节点"""
        # 首先确保约束存在
        self.ensure_constraints()
        
        with self.driver.session() as session:
            session.execute_write(self._create_virtual_layer_tx)

    @staticmethod
    def _cleanup_virtual_layer_tx(tx):
        # 删除相关关系
        tx.run("""
            MATCH (vl:VirtualLayer {name: 'voltage_virtual_layer'})-[r]->()
            DELETE r
        """)
        # 删除节点
        tx.run("""
            MATCH (vl:VirtualLayer {name: 'voltage_virtual_layer'})
            DETACH DELETE vl
        """)

    @staticmethod
    def _create_virtual_layer_tx(tx):
        tx.run("""
            CREATE (vl:VirtualLayer {
                name: 'voltage_virtual_layer',
                description: '电压传递虚拟层',
                created_at: datetime()
            })
        """)

    def get_virtual_layer_info(self):
        """获取虚拟层信息"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (vl:VirtualLayer)
                RETURN vl.name as name, 
                       vl.description as description,
                       vl.created_at as created_at
            """)
            return [dict(record) for record in result]

    def get_connected_nodes(self):
        """获取与虚拟层相连的节点信息"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (v:Vertex)-[:USES]->(vl:VirtualLayer)
                RETURN v.name as node_name,
                       v.NodeLayer as layer,
                       v.UnitType as unit_type,
                       vl.name as virtual_layer
                ORDER BY v.NodeLayer, v.name
            """)
            return [dict(record) for record in result]

    def create_simulation_unit(self, unit_type, position, layer_name, params):
        """创建仿真测试单元(D/B单元)
        
        参数:
        unit_type: 单元类型 (D/B)
        position: 连接位置 (外设层节点名称)
        layer_name: 所属虚拟层
        params: 单元参数字典
        """
        with self.driver.session() as session:
            session.execute_write(self._create_simulation_unit_tx,
                                unit_type, position, layer_name, params)

    @staticmethod
    def _create_simulation_unit_tx(tx, unit_type, position, layer_name, params):
        """创建仿真单元事务方法"""
        tx.run("""
            MATCH (ext:Vertex {name: $position})
            CREATE (u:Vertex:SimulationUnit {
                name: $unit_name,
                NodeLayer: $layer_name,
                UnitType: $unit_type,
                voltage_output: $voltage_output,
                voltage_threshold: $voltage_threshold,
                created_at: datetime()
            })
            CREATE (u)-[:CONNECTS {via: 'simulation', voltage: 0.0}]->(ext)
            WITH u
            MATCH (vl:VirtualLayer {name: 'voltage_virtual_layer'})
            CREATE (u)-[:USES]->(vl)
        """, {
            "position": position,
            "unit_name": f"{unit_type}_{position}",
            "layer_name": layer_name,
            "unit_type": unit_type,
            "voltage_output": params.get('voltage_output', 0.0),
            "voltage_threshold": params.get('voltage_threshold', 0.0)
        })

    def create_test_connection(self, source_unit, target_unit, layer_name, expected_voltage):
        """创建测试连接关系
        参数:
        source_unit: B单元名称
        target_unit: D单元名称
        expected_voltage: 预期电压值
        """
        with self.driver.session() as session:
            session.execute_write(self._create_test_connection_tx,
                                source_unit, target_unit, layer_name, expected_voltage)

    @staticmethod
    def _create_test_connection_tx(tx, source_unit, target_unit, layer_name, expected_voltage):
        """创建测试连接事务方法"""
        tx.run("""
            MATCH (b:SimulationUnit {name: $source_unit})
            MATCH (d:SimulationUnit {name: $target_unit})
            CREATE (b)-[:TEST_CIRCUIT {
                layer: $layer_name,
                expected: $expected_voltage,
                actual: 0.0,
                status: 'pending',
                created_at: datetime()
            }]->(d)
        """, {
            "source_unit": source_unit,
            "target_unit": target_unit,
            "layer_name": layer_name,
            "expected_voltage": expected_voltage
        })

    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()