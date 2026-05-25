"""
并发压测引擎
支持多线程并发、Ramp-up加压、实时统计
"""
import time
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import numpy as np
from app.api_tester import APITester
from app.models import TestCase, LoadTestResult, get_session
import json


class LoadTestEngine:
    """并发压测引擎"""

    def __init__(self, load_test, test_case):
        """
        初始化压测引擎
        :param load_test: LoadTest对象
        :param test_case: TestCase对象
        """
        self.load_test = load_test
        self.test_case = test_case
        self.concurrent_users = load_test.concurrent_users
        self.duration = load_test.duration
        self.ramp_up_time = load_test.ramp_up_time

        # 结果收集（线程安全）
        self.lock = threading.Lock()
        self.results = []  # 存储每个请求的结果
        self.time_series = []  # 时序数据
        self.start_time = None
        self.stop_flag = False

    def execute_single_request(self, user_id, request_time):
        """
        执行单个请求
        :param user_id: 虚拟用户ID
        :param request_time: 请求时间戳
        :return: 请求结果字典
        """
        try:
            # 生成随机变量用于替换URL中的占位符
            variables = {
                'user_id': random.randint(1, 10),  # 随机用户ID 1-10
                'id': random.randint(1, 100),      # 随机ID 1-100
                'page': random.randint(1, 10),     # 随机页码 1-10
                'limit': random.choice([10, 20, 50]),  # 随机限制数
            }

            # 创建APITester并传入变量（APITester支持变量替换）
            tester = APITester()

            # 使用replace_variables方法替换URL和body中的变量
            test_url = tester.replace_variables(self.test_case.url, variables)
            test_body = tester.replace_variables(self.test_case.body, variables) if self.test_case.body else None

            # 创建临时的test_case副本（避免线程安全问题）
            from copy import copy
            temp_case = copy(self.test_case)
            temp_case.url = test_url
            temp_case.body = test_body

            # 计算发送字节数（请求体大小）
            sent_bytes = len(test_body.encode('utf-8')) if test_body else 0
            # 添加请求头大小的估算（粗略估计）
            sent_bytes += 200  # 估算请求头大小

            # 执行测试
            result = tester.run_test_case(temp_case)

            # 计算接收字节数（响应体大小）
            received_bytes = len(result.response_body.encode('utf-8')) if result.response_body else 0

            # 从TestResult对象提取数据
            request_result = {
                'user_id': user_id,
                'timestamp': request_time,
                'elapsed_time': time.time() - request_time,
                'response_time': result.response_time if result.response_time else 0,
                'status_code': result.actual_status if result.actual_status else 0,
                'success': result.status == 'success',
                'error': result.error_message if result.error_message else None,
                'sent_bytes': sent_bytes,
                'received_bytes': received_bytes
            }

            return request_result

        except Exception as e:
            return {
                'user_id': user_id,
                'timestamp': request_time,
                'elapsed_time': time.time() - request_time,
                'response_time': 0,
                'status_code': 0,
                'success': False,
                'error': str(e),
                'sent_bytes': 0,
                'received_bytes': 0
            }

    def calculate_active_users(self, elapsed_time):
        """
        计算当前时刻应该有多少活跃用户（Ramp-up逻辑）
        :param elapsed_time: 已经过的时间（秒）
        :return: 当前应该活跃的用户数
        """
        if self.ramp_up_time == 0:
            # 没有Ramp-up，直接返回全部并发数
            return self.concurrent_users

        if elapsed_time >= self.ramp_up_time:
            # Ramp-up时间已过，返回全部并发数
            return self.concurrent_users

        # 线性增长：根据时间比例计算当前用户数
        # 例如：10个用户，20秒Ramp-up，第10秒时应该有5个用户
        progress = elapsed_time / self.ramp_up_time
        active_users = int(self.concurrent_users * progress)
        return max(1, active_users)  # 至少1个用户

    def user_worker(self, user_id):
        """
        单个虚拟用户的工作线程
        :param user_id: 用户ID
        """
        while not self.stop_flag:
            elapsed_time = time.time() - self.start_time

            # 检查是否超过持续时间
            if elapsed_time >= self.duration:
                break

            # 检查当前用户是否应该活跃（Ramp-up控制）
            active_users = self.calculate_active_users(elapsed_time)
            if user_id >= active_users:
                # 当前用户还未到激活时间，等待
                time.sleep(0.1)
                continue

            # 执行请求
            request_time = time.time()
            result = self.execute_single_request(user_id, request_time)

            # 线程安全地添加结果
            with self.lock:
                self.results.append(result)

            # 短暂休息，避免过于密集（可选）
            time.sleep(0.01)

    def collect_time_series_data(self):
        """
        收集时序数据（每秒统计）
        在单独的线程中运行
        """
        last_count = 0
        while not self.stop_flag:
            time.sleep(1)  # 每秒统计一次

            elapsed_time = time.time() - self.start_time
            if elapsed_time >= self.duration:
                break

            with self.lock:
                current_count = len(self.results)
                requests_this_second = current_count - last_count
                last_count = current_count

                # 计算当前活跃用户数
                active_users = self.calculate_active_users(elapsed_time)

                # 记录时序数据点
                self.time_series.append({
                    'timestamp': int(elapsed_time),
                    'active_users': active_users,
                    'requests': requests_this_second,
                    'total_requests': current_count
                })

    def calculate_statistics(self):
        """
        计算统计数据
        :return: 统计结果字典
        """
        if not self.results:
            return None

        # 提取响应时间列表
        response_times = [r['response_time'] for r in self.results]
        success_count = sum(1 for r in self.results if r['success'])
        failed_count = len(self.results) - success_count

        # 计算基本统计
        total_requests = len(self.results)
        avg_response_time = np.mean(response_times)
        min_response_time = np.min(response_times)
        max_response_time = np.max(response_times)

        # 计算百分位数
        p50 = np.percentile(response_times, 50)
        p90 = np.percentile(response_times, 90)
        p95 = np.percentile(response_times, 95)
        p99 = np.percentile(response_times, 99)

        # 计算TPS（每秒事务数）
        actual_duration = time.time() - self.start_time
        tps = total_requests / actual_duration if actual_duration > 0 else 0

        # 计算错误率
        error_rate = failed_count / total_requests if total_requests > 0 else 0

        # 计算网络吞吐量
        total_sent_bytes = sum(r.get('sent_bytes', 0) for r in self.results)
        total_received_bytes = sum(r.get('received_bytes', 0) for r in self.results)
        sent_kb_per_sec = (total_sent_bytes / 1024) / actual_duration if actual_duration > 0 else 0
        received_kb_per_sec = (total_received_bytes / 1024) / actual_duration if actual_duration > 0 else 0

        return {
            'total_requests': total_requests,
            'success_requests': success_count,
            'failed_requests': failed_count,
            'avg_response_time': avg_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'p50_response_time': p50,
            'p90_response_time': p90,
            'p95_response_time': p95,
            'p99_response_time': p99,
            'tps': tps,
            'error_rate': error_rate,
            'actual_duration': actual_duration,
            'total_sent_bytes': total_sent_bytes,
            'total_received_bytes': total_received_bytes,
            'sent_kb_per_sec': sent_kb_per_sec,
            'received_kb_per_sec': received_kb_per_sec
        }

    def run(self):
        """
        执行压测
        :return: LoadTestResult对象
        """
        print(f"开始压测: {self.load_test.name}")
        print(f"  并发用户: {self.concurrent_users}")
        print(f"  持续时间: {self.duration}秒")
        print(f"  Ramp-up: {self.ramp_up_time}秒")

        # 记录开始时间
        self.start_time = time.time()
        self.stop_flag = False

        # 启动时序数据收集线程
        time_series_thread = threading.Thread(target=self.collect_time_series_data)
        time_series_thread.daemon = True
        time_series_thread.start()

        # 使用线程池执行并发请求
        with ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
            # 为每个虚拟用户创建一个工作线程
            futures = []
            for user_id in range(self.concurrent_users):
                future = executor.submit(self.user_worker, user_id)
                futures.append(future)

            # 等待所有线程完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"线程执行错误: {e}")

        # 设置停止标志
        self.stop_flag = True
        time_series_thread.join(timeout=2)

        print(f"压测完成，共执行 {len(self.results)} 个请求")

        # 计算统计数据
        stats = self.calculate_statistics()
        if not stats:
            raise Exception("压测未产生任何结果")

        # 保存结果到数据库
        session = get_session()
        try:
            result = LoadTestResult(
                load_test_id=self.load_test.id,
                load_test_name=self.load_test.name,
                test_case_name=self.test_case.name,
                concurrent_users=self.concurrent_users,
                ramp_up_time=self.ramp_up_time,
                duration=self.duration,
                total_requests=stats['total_requests'],
                success_requests=stats['success_requests'],
                failed_requests=stats['failed_requests'],
                avg_response_time=stats['avg_response_time'],
                min_response_time=stats['min_response_time'],
                max_response_time=stats['max_response_time'],
                p50_response_time=stats['p50_response_time'],
                p90_response_time=stats['p90_response_time'],
                p95_response_time=stats['p95_response_time'],
                p99_response_time=stats['p99_response_time'],
                tps=stats['tps'],
                error_rate=stats['error_rate'],
                time_series_data=json.dumps(self.time_series),
                # 网络吞吐量
                total_sent_bytes=stats['total_sent_bytes'],
                total_received_bytes=stats['total_received_bytes'],
                sent_bytes_per_sec=stats['sent_kb_per_sec'],
                received_bytes_per_sec=stats['received_kb_per_sec']
            )
            session.add(result)
            session.commit()

            print(f"结果已保存，ID: {result.id}")
            return result

        except Exception as e:
            session.rollback()
            raise Exception(f"保存结果失败: {e}")
        finally:
            session.close()


