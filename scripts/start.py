#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速启动脚本
使用方法: python start.py
"""
import os
import sys
import subprocess

def check_python():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("[错误] 需要 Python 3.7 或更高版本")
        print(f"当前版本: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_database():
    """检查数据库"""
    if not os.path.exists('database.db'):
        print("[提示] 数据库不存在，正在初始化...")
        result = subprocess.run([sys.executable, 'init_db.py'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("[错误] 数据库初始化失败")
            print(result.stderr)
            return False
        print("[OK] 数据库初始化完成")
    else:
        print("[OK] 数据库已存在")
    return True

def check_dependencies():
    """检查依赖"""
    try:
        import flask
        print("[OK] Flask 已安装")
        return True
    except ImportError:
        print("[提示] Flask 未安装，正在安装依赖...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 
                               '-r', 'requirements.txt'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("[错误] 依赖安装失败")
            print(result.stderr)
            return False
        print("[OK] 依赖安装完成")
        return True

def start_app():
    """启动应用"""
    import threading
    import time
    import webbrowser

    print()
    print("=" * 60)
    print("           API 自动化测试平台")
    print("=" * 60)
    print()
    print("访问地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务器")
    print()
    print("=" * 60)
    print()

    # 延迟 2 秒后自动打开浏览器，等待服务器就绪
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:5000")

    threading.Thread(target=open_browser, daemon=True).start()

    subprocess.run([sys.executable, 'run.py'])

def main():
    print()
    print("=" * 60)
    print("           快速启动向导")
    print("=" * 60)
    print()
    
    # 检查 Python
    print("[1/3] 检查 Python...")
    if not check_python():
        input("按回车键退出...")
        return
    print()
    
    # 检查数据库
    print("[2/3] 检查数据库...")
    if not check_database():
        input("按回车键退出...")
        return
    print()
    
    # 检查依赖
    print("[3/3] 检查依赖...")
    if not check_dependencies():
        input("按回车键退出...")
        return
    print()
    
    # 启动应用
    start_app()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("应用已停止")
    except Exception as e:
        print(f"[错误] {e}")
        input("按回车键退出...")
