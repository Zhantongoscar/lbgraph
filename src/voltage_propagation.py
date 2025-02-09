from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
import math

class VoltagePropagator:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD),
            connection_timeout=30
        )
        
    def find_propagation_paths(self, start_id, max_depth=10):
        """电压传播路径发现算法"""
        with self.driver.session() as session:
            query = (
                "MATCH path=(start:Vertex)-[:conn*1..%d]->(end:Vertex) "
                "WHERE start.id = $start_id AND end.type IN ['PLC', 'sim'] "
                "WITH relationships(path) AS rels, nodes(path) AS nodes "
                "WHERE ALL(r IN rels WHERE r.resistance IS NOT NULL) "
                "RETURN nodes, reduce(v = start.voltage, r IN rels | v * exp(-r.resistance)) AS expected_voltage"
            ) % max_depth
            result = session.run(query, start_id=start_id)
            return [(record["nodes"], record["expected_voltage"]) for record in result]

    def calculate_expected_voltage(self, paths):
        """带衰减模型的电压计算"""
        results = []
        for nodes, base_voltage in paths:
            path_length = len(nodes)
            path_resistance = sum(rel.get("resistance", 0) for rel in self._get_relationships(nodes))
            decay_factor = math.exp(-path_resistance * 0.1)  # 衰减系数模型
            results.append({
                "path": [node.id for node in nodes],
                "expected_voltage": round(base_voltage * decay_factor, 2),
                "confidence": max(0, 1 - 0.1 * path_length)  # 路径置信度系数
            })
        return sorted(results, key=lambda x: -x["confidence"])

    def _get_relationships(self, nodes):
        """获取节点间关系链"""
        with self.driver.session() as session:
            rels = []
            for i in range(len(nodes)-1):
                result = session.run(
                    "MATCH (a)-[r:conn]->(b) "
                    "WHERE a.id = $a_id AND b.id = $b_id "
                    "RETURN r",
                    a_id=nodes[i].id, b_id=nodes[i+1].id
                )
                rels.extend(record["r"] for record in result)
            return rels

    def close(self):
        self.driver.close()

if __name__ == "__main__":
    vp = VoltagePropagator()
    test_paths = vp.find_propagation_paths("PLC_001")
    expected = vp.calculate_expected_voltage(test_paths)
    print("电压传播预测结果:")
    for item in expected[:3]:  # 显示置信度最高的前3条路径
        print(f"路径: {item['path']} | 预期电压: {item['expected_voltage']}V | 置信度: {item['confidence']*100}%")