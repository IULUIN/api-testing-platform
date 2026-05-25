"""
工具函数
"""
import json
from datetime import datetime


def format_json(json_str):
    """格式化JSON字符串"""
    try:
        if not json_str:
            return ''
        obj = json.loads(json_str)
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except:
        return json_str


def calculate_success_rate(results):
    """
    计算成功率

    参数:
        results: TestResult对象列表

    返回:
        成功率（百分比）
    """
    if not results:
        return 0

    success_count = sum(1 for r in results if r.status == 'success')
    return round(success_count / len(results) * 100, 2)


def get_statistics(results):
    """
    获取统计信息

    参数:
        results: TestResult对象列表

    返回:
        统计字典
    """
    if not results:
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'error': 0,
            'success_rate': 0,
            'avg_response_time': 0
        }

    total = len(results)
    success = sum(1 for r in results if r.status == 'success')
    failed = sum(1 for r in results if r.status == 'failed')
    error = sum(1 for r in results if r.status == 'error')

    # 计算平均响应时间
    response_times = [r.response_time for r in results if r.response_time]
    avg_response_time = round(sum(response_times) / len(response_times), 3) if response_times else 0

    return {
        'total': total,
        'success': success,
        'failed': failed,
        'error': error,
        'success_rate': calculate_success_rate(results),
        'avg_response_time': avg_response_time
    }


def format_datetime(dt):
    """格式化日期时间"""
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt)
