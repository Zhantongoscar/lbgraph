"""
继电器类型分析测试脚本
"""
from relay_type_system import RelayTypeAnalyzer
import json

def print_relay_type_info(type_id: str, analyzer: RelayTypeAnalyzer):
    """打印继电器类型信息"""
    relay_type = analyzer.relay_types.get(type_id)
    if not relay_type:
        print(f"未找到型号: {type_id}")
        return 
        
    print(f"\n===== 继电器型号: {type_id} =====")
    print(f"类别: {relay_type.category}")
    print(f"制造商: {relay_type.manufacturer}")
    print(f"线圈电压: {relay_type.coil_voltage}")
    print(f"功率等级: {relay_type.power_rating}")
    
    print("\n端子模式:")
    pattern = relay_type.terminal_pattern
    print(f"  线圈端子: {pattern.coil_terminals}")
    print(f"  功率端子: {pattern.power_terminals}")
    print(f"  辅助触点: {pattern.auxiliary_terminals}")
    print(f"  诊断端子: {pattern.diagnostic_terminals}")
    
    instances = analyzer.get_instances_of_type(type_id)
    print(f"\n该型号的实例: {instances}")
    
    config = analyzer.get_relay_type_config(type_id)
    print("\n配置数据:")
    print(json.dumps(config, indent=2, ensure_ascii=False))

def main():
    """主测试函数"""
    analyzer = RelayTypeAnalyzer()
    
    # 分析CSV文件
    print("开始分析CSV文件中的继电器数据...")
    analyzer.analyze_csv('data/SmartWiringzta.csv')
    
    # 打印发现的所有继电器型号
    print("\n发现的继电器型号:")
    for type_id in analyzer.relay_types:
        print_relay_type_info(type_id, analyzer)
        
    # 打印统计信息
    print("\n\n===== 统计信息 =====")
    print(f"发现的继电器型号数量: {len(analyzer.relay_types)}")
    print(f"继电器实例总数: {sum(len(instances) for instances in analyzer.relay_instances.values())}")
    
    # 端子模式分析
    print("\n端子模式分布:")
    pattern_stats = {}
    for type_id, relay_type in analyzer.relay_types.items():
        pattern = relay_type.terminal_pattern
        key = (
            len(pattern.coil_terminals),
            len(pattern.power_terminals),
            len(pattern.auxiliary_terminals)
        )
        if key not in pattern_stats:
            pattern_stats[key] = []
        pattern_stats[key].append(type_id)
    
    for (coil, power, aux), types in pattern_stats.items():
        print(f"\n端子组合 (线圈:{coil}, 功率:{power}, 辅助:{aux}):")
        print(f"  型号: {types}")

if __name__ == "__main__":
    main()