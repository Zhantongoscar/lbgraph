from voltage_propagation import VoltagePropagator
from hardware.scpi_controller import PowerSupplyController
from neo4j import GraphDatabase
from config import NEO4J_CONFIG, HARDWARE_CONFIG
import time
import csv

class TestExecutor:
    def __init__(self):
        self.vp = VoltagePropagator()
        self.ps = PowerSupplyController(HARDWARE_CONFIG['power_supply'])
        self.driver = GraphDatabase.driver(**NEO4J_CONFIG)
        
    def load_test_cases(self, csv_path):
        """加载测试用例"""
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return [{
                'source': row['source_node'],
                'targets': row['target_nodes'].split(';'),
                'expected': float(row['expected_voltage'])
            } for row in reader]

    def execute_test_case(self, test_case):
        """执行单个测试用例"""
        results = []
        
        # 设置激励电压
        with self.ps:
            self.ps.set_voltage(24.0)
            self.ps.enable_output()
            
            # 获取预期路径
            predicted = self.vp.find_propagation_paths(test_case['source'])
            
            # 执行实际测量
            for target in test_case['targets']:
                measured = self._measure_voltage(target)
                results.append({
                    'target': target,
                    'expected': test_case['expected'],
                    'measured': measured,
                    'status': 'PASS' if abs(measured - test_case['expected']) < 0.5 else 'FAIL'
                })
        
        return results

    def _measure_voltage(self, node_id):
        """模拟实际电压测量(待接入真实硬件)"""
        # 当前模拟随机值,实际应调用万用表接口
        import random
        return round(random.uniform(23.5, 24.5), 2)

    def generate_report(self, results, output_path):
        """生成测试报告"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Target Node', 'Expected (V)', 'Measured (V)', 'Status'])
            for res in results:
                writer.writerow([
                    res['target'],
                    res['expected'],
                    res['measured'],
                    res['status']
                ])

if __name__ == "__main__":
    tester = TestExecutor()
    test_cases = tester.load_test_cases('test_cases/test_scenarios.csv')
    
    all_results = []
    for idx, case in enumerate(test_cases, 1):
        print(f"执行测试用例 #{idx}: {case['source']} -> {case['targets']}")
        results = tester.execute_test_case(case)
        all_results.extend(results)
    
    tester.generate_report(all_results, 'reports/test_report.csv')
    print("测试完成,报告已生成")