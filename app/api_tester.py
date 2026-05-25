"""
接口测试核心模块
"""
import requests
import json
import time
import re
from app.models import TestResult, get_session
from app.smart_assertion import SmartAssertion


class APITester:
    """接口测试器"""

    def __init__(self, timeout=30, environment=None):
        self.timeout = timeout
        self.session = requests.Session()
        self.assertion_engine = SmartAssertion()
        self.environment = environment  # 环境配置

    def replace_variables(self, text, variables=None):
        """
        替换文本中的变量

        支持两种格式：
        - {{variable}}
        - ${variable}

        参数:
            text: 要替换的文本
            variables: 变量字典

        返回:
            替换后的文本
        """
        if not text or not variables:
            return text

        # 替换 {{variable}} 格式
        def replace_double_brace(match):
            var_name = match.group(1).strip()
            return str(variables.get(var_name, match.group(0)))

        text = re.sub(r'\{\{([^}]+)\}\}', replace_double_brace, text)

        # 替换 ${variable} 格式
        def replace_dollar_brace(match):
            var_name = match.group(1).strip()
            return str(variables.get(var_name, match.group(0)))

        text = re.sub(r'\$\{([^}]+)\}', replace_dollar_brace, text)

        return text

    def send_request(self, method, url, headers=None, body=None):
        """
        发送HTTP请求

        参数:
            method: 请求方法 (GET, POST, PUT, DELETE)
            url: 请求URL
            headers: 请求头 (字典或JSON字符串)
            body: 请求体 (字典或JSON字符串)

        返回:
            (response, response_time, error)
        """
        try:
            # 获取环境变量
            env_vars = {}
            if self.environment:
                env_vars['base_url'] = self.environment.get('base_url', '')
                # 解析环境变量JSON
                if self.environment.get('variables'):
                    try:
                        custom_vars = json.loads(self.environment['variables'])
                        env_vars.update(custom_vars)
                    except:
                        pass

            # 替换URL中的变量
            url = self.replace_variables(url, env_vars)

            # 解析headers
            if headers:
                if isinstance(headers, str):
                    # 替换headers中的变量
                    headers = self.replace_variables(headers, env_vars)
                    headers = json.loads(headers)
            else:
                headers = {}

            # 解析body
            if body:
                if isinstance(body, str):
                    # 替换body中的变量
                    body = self.replace_variables(body, env_vars)
                    body = json.loads(body)
            else:
                body = None

            # 记录开始时间
            start_time = time.time()

            # 发送请求
            method = method.upper()
            if method == 'GET':
                response = self.session.get(url, headers=headers, timeout=self.timeout)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, json=body, timeout=self.timeout)
            elif method == 'PUT':
                response = self.session.put(url, headers=headers, json=body, timeout=self.timeout)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers, timeout=self.timeout)
            else:
                return None, 0, f"不支持的请求方法: {method}"

            # 计算响应时间
            response_time = time.time() - start_time

            return response, response_time, None

        except requests.exceptions.Timeout:
            return None, 0, f"请求超时（超过{self.timeout}秒）"
        except requests.exceptions.ConnectionError as e:
            error_msg = str(e)
            # 提取主机和端口信息
            host_port = ""
            if "host=" in error_msg and "port=" in error_msg:
                try:
                    host = error_msg.split("host='")[1].split("'")[0]
                    port = error_msg.split("port=")[1].split(")")[0]
                    host_port = f" ({host}:{port})"
                except:
                    pass

            if "Max retries exceeded" in error_msg or "Connection refused" in error_msg:
                return None, 0, f"连接被拒绝{host_port} - 请检查目标服务是否启动"
            elif "Name or service not known" in error_msg or "nodename nor servname provided" in error_msg:
                return None, 0, f"域名解析失败{host_port} - 请检查URL是否正确"
            elif "No route to host" in error_msg:
                return None, 0, f"无法访问目标主机{host_port} - 请检查网络连接"
            elif "timed out" in error_msg.lower():
                return None, 0, f"连接超时{host_port} - 目标服务响应缓慢或不可达"
            else:
                return None, 0, f"连接失败{host_port} - {error_msg[:150]}"
        except json.JSONDecodeError as e:
            return None, 0, f"JSON解析错误: {str(e)}"
        except Exception as e:
            return None, 0, f"请求异常: {str(e)}"

    def validate_response(self, response, expected_status):
        """
        验证响应结果

        参数:
            response: 响应对象
            expected_status: 期望的状态码

        返回:
            (is_success, message)
        """
        if response is None:
            return False, "响应为空"

        actual_status = response.status_code
        if actual_status == expected_status:
            return True, "状态码匹配"
        else:
            return False, f"状态码不匹配: 期望{expected_status}, 实际{actual_status}"

    def run_test_case(self, test_case):
        """
        执行测试用例

        参数:
            test_case: TestCase对象

        返回:
            TestResult对象
        """
        # 发送请求
        response, response_time, error = self.send_request(
            method=test_case.method,
            url=test_case.url,
            headers=test_case.headers,
            body=test_case.body
        )

        # 创建测试结果
        result = TestResult(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            response_time=response_time
        )

        # 处理错误
        if error:
            result.status = 'error'
            result.error_message = error
            result.actual_status = 0
            result.response_body = ''
            result.assertion_results = None
            return result

        # 验证状态码
        is_success, message = self.validate_response(response, test_case.expected_status)

        result.actual_status = response.status_code

        # 保存响应体（限制长度）
        try:
            response_text = response.text
            if len(response_text) > 5000:
                response_text = response_text[:5000] + '...(已截断)'
            result.response_body = response_text
        except:
            result.response_body = '无法解析响应体'

        # 执行智能断言
        assertion_passed = True
        assertion_results = []

        if hasattr(test_case, 'assertions') and test_case.assertions:
            assertion_passed, assertion_results = self.assertion_engine.run_assertions(
                result.response_body,
                test_case.assertions
            )
            result.assertion_results = json.dumps(assertion_results, ensure_ascii=False)

        # 综合判断测试结果
        if is_success and assertion_passed:
            result.status = 'success'
            result.error_message = ''
        else:
            result.status = 'failed'
            error_messages = []
            if not is_success:
                error_messages.append(message)
            if not assertion_passed:
                failed_assertions = [a for a in assertion_results if not a['passed']]
                for a in failed_assertions:
                    error_messages.append(f"断言失败: {a['description'] or a['path']} - {a['message']}")
            result.error_message = '; '.join(error_messages)

        return result

    def run_multiple_cases(self, test_cases):
        """
        批量执行测试用例

        参数:
            test_cases: TestCase对象列表

        返回:
            TestResult对象列表
        """
        results = []
        for test_case in test_cases:
            result = self.run_test_case(test_case)
            results.append(result)
        return results
