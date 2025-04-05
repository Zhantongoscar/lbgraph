"""Test relay rules functionality"""
from relay_rules import DevicePathValidator

def test_device_path_validation():
    """测试设备路径验证"""
    validator = DevicePathValidator()
    
    # 测试用例
    test_cases = [
        # 有效的设备路径
        ("=A01+K1.H2-Q1", True),
        ("=A02+K1.B1-K20:34", True),
        ("=A01+K1.H2-K1:A1", True),
        
        # 无效的设备路径
        ("K1.H2", False),
        ("=+K1", False),
        ("=A01K1", False),
        ("=A01+K1.X2-M1", False),  # X2不是有效的子端子
        
        # 特殊情况
        ("=A01+K1", True),
        ("=A01+Q1.H2", True),
        ("=A01+K1.H2-K1", True)
    ]
    
    results = []
    for path, expected in test_cases:
        is_valid, error_msg = validator.validate_device_path_format(path)
        results.append({
            'path': path,
            'expected': expected,
            'actual': is_valid,
            'error': error_msg if not is_valid else None
        })
        
    return results

def test_device_path_matching():
    """测试设备路径匹配"""
    validator = DevicePathValidator()
    
    # 测试用例
    test_cases = [
        # 应该匹配的路径对
        ("=A01+K1.H2-Q1:A1", "=A01+K1.H2-Q1:A2", True),
        ("=A01+K1.H2-Q1", "=A01+K1.H2-Q1:14", True),
        
        # 不应该匹配的路径对
        ("=A01+K1.H2-Q1", "=A01+K2.H2-Q1", False),
        ("=A01+K1.H2-Q1", "=A02+K1.H2-Q1", False),
        ("=A01+K1.H1-Q1", "=A01+K1.H2-Q1", False),
        
        # 特殊情况
        ("=A01+K1", "=A01+K1:A1", True),
        ("=A01+K1.H2-Q1", "=A01+K1.H2-Q2", False)
    ]
    
    results = []
    for path1, path2, expected in test_cases:
        is_same = validator.is_same_device(path1, path2)
        results.append({
            'path1': path1,
            'path2': path2,
            'expected': expected,
            'actual': is_same
        })
        
    return results

if __name__ == "__main__":
    # 运行测试
    print("\n测试设备路径验证:")
    for result in test_device_path_validation():
        status = "通过" if result['expected'] == result['actual'] else "失败"
        print(f"路径: {result['path']}")
        print(f"预期: {result['expected']}, 实际: {result['actual']}")
        print(f"状态: {status}")
        if result['error']:
            print(f"错误: {result['error']}")
        print()
        
    print("\n测试设备路径匹配:")
    for result in test_device_path_matching():
        status = "通过" if result['expected'] == result['actual'] else "失败"
        print(f"路径1: {result['path1']}")
        print(f"路径2: {result['path2']}")
        print(f"预期: {result['expected']}, 实际: {result['actual']}")
        print(f"状态: {status}")
        print()