from virtual_layer_manager import VirtualLayerManager

def main():
    # Neo4j连接信息
    from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    uri = NEO4J_URI
    user = NEO4J_USER
    password = NEO4J_PASSWORD

    # 初始化VirtualLayerManager
    manager = VirtualLayerManager(uri, user, password)

    try:
        # 执行复制操作
        virtual_layer_name = "MyVirtualLayer"
        print(f"开始复制元素到虚拟层 '{virtual_layer_name}'...")
        manager.copy_elements_to_virtual_layer(virtual_layer_name)
        print("复制操作完成！")
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 确保关闭连接
        manager.close()
        print("数据库连接已关闭。")

if __name__ == "__main__":
    main()
