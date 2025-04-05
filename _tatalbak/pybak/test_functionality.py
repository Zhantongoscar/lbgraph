from import_csv_data import DataImporter
from virtual_layer_manager import VirtualLayerManager
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def test_virtual_layer():
    # 创建虚拟层管理器
    vlm = VirtualLayerManager(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # 创建一个测试虚拟层
        print("创建测试虚拟层...")
        vlm.copy_elements_to_virtual_layer("TestVirtualLayer")
        print("虚拟层创建完成")
        
    finally:
        vlm.close()

if __name__ == "__main__":
    print("开始测试...")
    test_virtual_layer()
    print("测试完成")