"""
Mock服务模块
用于模拟API响应，解决接口依赖问题
"""
from flask import Flask, jsonify, request
import random
import time
import threading
from typing import Dict, Any, Optional

app = Flask(__name__)

# Mock数据存储
MOCK_DATA: Dict[str, Any] = {
    'users': [
        {'id': 1, 'name': '张三', 'email': 'zhangsan@example.com', 'phone': '13800138000'},
        {'id': 2, 'name': '李四', 'email': 'lisi@example.com', 'phone': '13800138001'},
        {'id': 3, 'name': '王五', 'email': 'wangwu@example.com', 'phone': '13800138002'}
    ],
    'products': [
        {'id': 1, 'name': '商品A', 'price': 99.9, 'stock': 100, 'category': '电子产品'},
        {'id': 2, 'name': '商品B', 'price': 199.9, 'stock': 50, 'category': '服装'},
        {'id': 3, 'name': '商品C', 'price': 299.9, 'stock': 25, 'category': '食品'}
    ],
    'orders': [
        {'id': 1, 'user_id': 1, 'product_id': 1, 'quantity': 2, 'status': 'pending'},
        {'id': 2, 'user_id': 2, 'product_id': 2, 'quantity': 1, 'status': 'shipped'}
    ]
}

# Mock规则配置
MOCK_RULES: Dict[str, Dict] = {
    '/api/users/<int:user_id>': {
        'methods': ['GET'],
        'response': lambda user_id: random.choice(MOCK_DATA['users']) if user_id in [u['id'] for u in MOCK_DATA['users']] else None,
        'delay': 0.1,
        'status_code': 200
    },
    '/api/products': {
        'methods': ['GET'],
        'response': lambda: MOCK_DATA['products'],
        'delay': 0.05,
        'status_code': 200
    },
    '/api/login': {
        'methods': ['POST'],
        'response': lambda: {'token': f'mock-token-{random.randint(1000, 9999)}', 'user_id': 1},
        'delay': 0.2,
        'status_code': 200
    },
    '/api/orders': {
        'methods': ['POST'],
        'response': lambda: {'order_id': f'ORD{int(time.time() * 1000)}', 'status': 'created'},
        'delay': 0.1,
        'status_code': 201
    }
}

# 全局状态
_mock_enabled: bool = True
_mock_lock = threading.Lock()

def enable_mock(enabled: bool = True):
    """启用/禁用Mock服务"""
    global _mock_enabled
    with _mock_lock:
        _mock_enabled = enabled

def is_mock_enabled() -> bool:
    """检查Mock服务是否启用"""
    with _mock_lock:
        return _mock_enabled

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'mock_enabled': _mock_enabled,
        'timestamp': time.time()
    })

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def mock_api(path):
    """处理所有API请求的Mock"""
    if not is_mock_enabled():
        return jsonify({'error': 'Mock服务未启用'}), 403

    # 查找匹配的规则
    rule = None
    for pattern, config in MOCK_RULES.items():
        if path.startswith(pattern.replace('<int:user_id>', r'\d+')):
            rule = config
            break

    if not rule:
        # 如果没有找到规则，返回默认响应
        return jsonify({'message': 'Mock响应', 'data': {}}), 200

    # 检查方法是否允许
    if request.method not in rule['methods']:
        return jsonify({'error': 'Method not allowed'}), 405

    # 模拟延迟
    time.sleep(rule.get('delay', 0.1))

    # 获取响应数据
    try:
        response_data = rule['response'](request)
        status_code = rule.get('status_code', 200)
        return jsonify(response_data), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/<path:path>/<int:param>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def mock_api_with_param(path, param):
    """处理带参数的API请求"""
    if not is_mock_enabled():
        return jsonify({'error': 'Mock服务未启用'}), 403

    # 构建完整路径
    full_path = f"/api/{path}/{param}"
    return mock_api(full_path)

@app.route('/api/<path:path>/<string:param>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def mock_api_with_string_param(path, param):
    """处理带字符串参数的API请求"""
    if not is_mock_enabled():
        return jsonify({'error': 'Mock服务未启用'}), 403

    # 构建完整路径
    full_path = f"/api/{path}/{param}"
    return mock_api(full_path)

@app.route('/api/<path:path>', methods=['GET'])
def mock_get(path):
    """处理GET请求"""
    if not is_mock_enabled():
        return jsonify({'error': 'Mock服务未启用'}), 403

    rule = None
    for pattern, config in MOCK_RULES.items():
        if path.startswith(pattern.replace('<int:user_id>', r'\d+')):
            rule = config
            break

    if not rule:
        return jsonify({'message': 'Mock响应'}), 200

    if 'GET' not in rule['methods']:
        return jsonify({'error': 'Method not allowed'}), 405

    time.sleep(rule.get('delay', 0.1))

    try:
        response_data = rule['response']()
        status_code = rule.get('status_code', 200)
        return jsonify(response_data), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Mock服务启动中...")
    print("=" * 50)
    print(f"📍 地址: http://localhost:8080")
    print(f"📋 可用端点:")
    print(f"   GET  /api/health - 健康检查")
    print(f"   GET  /api/products - 获取商品列表")
    print(f"   GET  /api/users/<id> - 获取用户信息")
    print(f"   POST /api/login - 登录")
    print(f"   POST /api/orders - 创建订单")
    print(f"\n💡 提示: 访问 http://localhost:8080/api/health 查看状态")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8080, debug=True)
