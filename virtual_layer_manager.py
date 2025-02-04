from neo4j import GraphDatabase

class VirtualLayerManager:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def cleanup_virtual_layer(self):
        """清理虚拟层节点和关系"""
        with self.driver.session() as session:
            session.execute_write(self._cleanup_virtual_layer_tx)

    def create_virtual_layer(self):
        """创建新的虚拟层节点"""
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
        # 创建唯一性约束
        tx.run("""
            CREATE CONSTRAINT IF NOT EXISTS
            FOR (vl:VirtualLayer) REQUIRE vl.name IS UNIQUE
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

    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()