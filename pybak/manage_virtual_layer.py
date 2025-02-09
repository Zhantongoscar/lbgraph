from virtual_layer_manager import VirtualLayerManager
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def main():
    """管理虚拟层"""
    manager = VirtualLayerManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # 1. 清理现有虚拟层
        print("清理现有虚拟层...")
        manager.cleanup_virtual_layer()
        
        # 2. 创建新的虚拟层
        print("\n创建新的虚拟层...")
        manager.create_virtual_layer()
        
        # 3. 创建测试单元
        print("\n创建测试单元...")
        # 创建B单元(输出单元)
        manager.create_simulation_unit(
            unit_type='B',
            position='=Q01+K1.B1-X20:2:2',  # 使用已存在的节点名称
            layer_name='Simulation',
            params={'voltage_output': 24.0}
        )
        
        # 创建D单元(输入单元)
        manager.create_simulation_unit(
            unit_type='D',
            position='=Q01+K1.H2-Q1:T2',  # 使用已存在的节点名称
            layer_name='Simulation',
            params={'voltage_threshold': 20.0}
        )
        
        # 4. 创建测试连接
        print("\n创建测试连接...")
        manager.create_test_connection(
            source_unit='B_=Q01+K1.B1-X20:2:2',
            target_unit='D_=Q01+K1.H2-Q1:T2',
            layer_name='Simulation',
            expected_voltage=24.0
        )
        
        # 5. 获取虚拟层信息
        print("\n虚拟层信息:")
        layers = manager.get_virtual_layer_info()
        for layer in layers:
            print(f"- 名称: {layer['name']}")
            print(f"  描述: {layer['description']}")
            print(f"  创建时间: {layer['created_at']}")
        
        # 6. 获取连接到虚拟层的节点
        print("\n连接到虚拟层的节点:")
        nodes = manager.get_connected_nodes()
        if nodes:
            for node in nodes:
                print(f"- 节点: {node['node_name']}")
                print(f"  层: {node['layer']}")
                print(f"  单元类型: {node['unit_type']}")
                print(f"  虚拟层: {node['virtual_layer']}")
        else:
            print("当前没有节点连接到虚拟层")
            
    finally:
        manager.close()

if __name__ == "__main__":
    main()