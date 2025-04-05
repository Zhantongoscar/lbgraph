#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys

def print_rules(rules_file='c0c_inner_rules.json'):
    """打印规则文件内容"""
    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = json.load(f)
            
        # 打印Q类设备规则
        if 'deviceRules' in rules and 'Q' in rules['deviceRules']:
            print("Q类设备规则:")
            q_rules = rules['deviceRules']['Q']
            print(json.dumps(q_rules, indent=2, ensure_ascii=False))
        else:
            print("未找到Q类设备规则")
            
    except Exception as e:
        print(f"读取规则文件失败: {str(e)}")

if __name__ == "__main__":
    print_rules()
