#!/usr/bin/env python3
"""
Vibe-Trading 批量分析脚本
用法: python3 run_all.py          # 分析预设列表
      python3 run_all.py 000001   # 分析单个
"""

import os, sys, subprocess

DIR = os.path.dirname(__file__)

# 预设股票池
DEFAULT_STOCKS = ["300750", "600900", "00700"]

def analyze_code(code):
    print(f"\n{'='*50}")
    print(f"  🧬 分析: {code}")
    print(f"{'='*50}")
    
    # 采集数据
    ret = subprocess.run(["python3", os.path.join(DIR, "analyze.py"), code], 
                         capture_output=False, text=True)
    if ret.returncode != 0:
        print(f"  ❌ 采集失败: {code}")
        return False
    
    # 生成HTML
    ret = subprocess.run(["python3", os.path.join(DIR, "gen_unified.py"), code],
                         capture_output=False, text=True)
    if ret.returncode != 0:
        print(f"  ❌ 生成失败: {code}")
        return False
    
    return True


def main():
    if len(sys.argv) > 1:
        stocks = [sys.argv[1]]
    else:
        stocks = DEFAULT_STOCKS
    
    success = 0
    for code in stocks:
        if analyze_code(code):
            success += 1
    
    print(f"\n{'='*50}")
    print(f"  ✅ 完成: {success}/{len(stocks)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
