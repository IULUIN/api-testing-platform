"""
应用启动文件
"""
import os
import sys
import io
import threading
import time
import webbrowser
from app import create_app

# 设置标准输出为 UTF-8 编码，避免 Windows 下的编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

if __name__ == '__main__':
    app = create_app()
    print("=" * 50)
    print("API 自动化测试平台启动成功！")
    print("=" * 50)
    print("访问地址: http://127.0.0.1:5000")
    print("按 Ctrl+C 停止服务")
    print("=" * 50)

    # 仅在非 reloader 子进程中打开浏览器，避免 debug 模式下重复打开
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        def open_browser():
            time.sleep(2)
            webbrowser.open('http://127.0.0.1:5000')
        threading.Thread(target=open_browser, daemon=True).start()

    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=True)
