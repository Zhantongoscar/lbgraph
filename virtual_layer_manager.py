from neo4j import GraphDatabase

class VirtualLayerManager:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def copy_elements_to_virtual_layer(self, virtual_layer_name):
        with self.driver.session() as session:
            # 在一个事务中执行所有操作
            session.write_transaction(self._create_virtual_layer, virtual_layer_name)
            session.write_transaction(self._copy_nodes, virtual_layer_name)
            session.write_transaction(self._copy_relationships, virtual_layer_name)

    @staticmethod
    def _create_virtual_layer(tx, virtual_layer_name):
        # 创建虚拟层
        tx.run(f"CREATE (:{virtual_layer_name} {{name: $name}})", name=virtual_layer_name)

    @staticmethod
    def _copy_nodes(tx, virtual_layer_name):
        # 复制符合条件的节点
        query = """
        MATCH (n)
        WHERE n.Location STARTS WITH 'K1.' 
        AND NOT n.Terminal IN ['PE', 'N']
        CREATE (v:{virtual_layer_name})
        SET v = properties(n)
        """.format(virtual_layer_name=virtual_layer_name)
        result = tx.run(query)
        print(f"复制了 {result.summary().counters.nodes_created} 个节点到虚拟层 '{virtual_layer_name}'")

    @staticmethod
    def _copy_relationships(tx, virtual_layer_name):
        # 复制符合条件的边
        query = """
        MATCH (a)-[r]->(b)
        WHERE a.Location STARTS WITH 'K1.' AND b.Location STARTS WITH 'K1.'
        AND NOT a.Terminal IN ['PE', 'N'] AND NOT b.Terminal IN ['PE', 'N']
        WITH a, r, b
        MATCH (va:{virtual_layer_name}), (vb:{virtual_layer_name})
        WHERE va.id = a.id AND vb.id = b.id
        CREATE (va)-[vr:{virtual_layer_name}]->(vb)
        SET vr = properties(r)
        """.format(virtual_layer_name=virtual_layer_name)
        tx.run(query)