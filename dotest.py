from virtual_layer_manager import VirtualLayerManager

def main():
    # 初始化虚拟层管理器
    from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    vlm = VirtualLayerManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    # 清理已存在的虚拟层
    vlm.cleanup_virtual_layer()
    print("虚拟层清理成功")
    
    # 创建新的虚拟层
    vlm.create_virtual_layer()
    print("虚拟层创建成功")
    
    # 测试查询虚拟层
    layers = vlm.get_virtual_layer_info()
    print("当前虚拟层信息:", layers)
    
    # 测试清理虚拟层
    vlm.cleanup_virtual_layer()
    print("虚拟层清理成功")

if __name__ == "__main__":
    main()
