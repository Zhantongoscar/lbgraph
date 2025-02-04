import argparse
from virtual_layer_manager import VirtualLayerManager
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def main():
    """
    虚拟层管理工具

    用法示例:
    1. 创建虚拟层:
       python manage_virtual_layer.py --action create
    
    2. 查看虚拟层信息:
       python manage_virtual_layer.py --action info
    
    3. 查看连接的节点:
       python manage_virtual_layer.py --action nodes
    
    4. 清理虚拟层:
       python manage_virtual_layer.py --action cleanup
    """
    parser = argparse.ArgumentParser(description='虚拟层管理工具')
    parser.add_argument('--action', required=True, 
                       choices=['create', 'info', 'nodes', 'cleanup'],
                       help='要执行的操作: create(创建), info(信息), nodes(节点), cleanup(清理)')

    args = parser.parse_args()

    # 创建虚拟层管理器实例
    manager = VirtualLayerManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        if args.action == 'create':
            print("创建虚拟层...")
            manager.create_virtual_layer()
            print("虚拟层创建成功")

        elif args.action == 'info':
            print("获取虚拟层信息...")
            info = manager.get_virtual_layer_info()
            for layer in info:
                print(f"\n虚拟层: {layer['name']}")
                print(f"描述: {layer['description']}")
                print(f"创建时间: {layer['created_at']}")

        elif args.action == 'nodes':
            print("获取连接的节点信息...")
            nodes = manager.get_connected_nodes()
            current_layer = None
            for node in nodes:
                if current_layer != node['layer']:
                    current_layer = node['layer']
                    print(f"\n{current_layer}层节点:")
                print(f"  - {node['node_name']} ({node['unit_type']}类型)")

        elif args.action == 'cleanup':
            print("清理虚拟层...")
            manager.cleanup_virtual_layer()
            print("虚拟层清理完成")

    finally:
        manager.close()

if __name__ == "__main__":
    main()