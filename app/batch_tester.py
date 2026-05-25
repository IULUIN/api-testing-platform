"""
批量测试执行器
"""
import json
from app.api_tester import APITester
from app.data_parser import DataSetParser
from app.models import TestResult, BatchTestResult


class BatchTester:
    """批量测试执行器"""

    def __init__(self):
        self.tester = APITester()
        self.parser = DataSetParser()

    def run_batch_test(self, test_case, data_rows):
        """
        执行批量测试

        参数:
            test_case: TestCase对象
            data_rows: 数据行列表 [DataRow对象, ...]

        返回:
            (results, summary)
            results: TestResult对象列表
            summary: 汇总信息字典
        """
        results = []
        summary = {
            'total': len(data_rows),
            'success': 0,
            'failed': 0,
            'error': 0
        }

        for idx, data_row in enumerate(data_rows, start=1):
            try:
                # 解析数据
                data_dict = json.loads(data_row.data_json)

                # 执行单个测试
                result = self._run_single_test(test_case, data_dict, idx)

                # 统计结果
                if result.status == 'success':
                    summary['success'] += 1
                elif result.status == 'failed':
                    summary['failed'] += 1
                else:
                    summary['error'] += 1

                results.append(result)

            except Exception as e:
                # 创建错误结果
                error_result = TestResult(
                    test_case_id=test_case.id,
                    test_case_name=f"{test_case.name} [数据{idx}]",
                    status='error',
                    actual_status=0,
                    response_time=0,
                    response_body='',
                    error_message=f"数据处理错误: {str(e)}"
                )
                summary['error'] += 1
                results.append(error_result)

        return results, summary

    def _run_single_test(self, test_case, data_dict, row_number):
        """
        执行单个测试（带变量替换）

        参数:
            test_case: TestCase对象
            data_dict: 数据字典
            row_number: 行号

        返回:
            TestResult对象
        """
        # 替换URL中的变量
        url = self.parser.replace_variables(test_case.url, data_dict)

        # 替换headers中的变量
        headers = test_case.headers
        if headers:
            headers = self.parser.replace_variables(headers, data_dict)

        # 替换body中的变量
        body = test_case.body
        if body:
            body = self.parser.replace_variables(body, data_dict)

        # 发送请求
        response, response_time, error = self.tester.send_request(
            method=test_case.method,
            url=url,
            headers=headers,
            body=body
        )

        # 创建测试结果
        result = TestResult(
            test_case_id=test_case.id,
            test_case_name=f"{test_case.name} [数据{row_number}]",
            response_time=response_time
        )

        # 处理错误
        if error:
            result.status = 'error'
            result.error_message = error
            result.actual_status = 0
            result.response_body = ''
            return result

        # 验证状态码
        is_success, message = self.tester.validate_response(response, test_case.expected_status)

        result.actual_status = response.status_code

        # 保存响应体
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
            try:
                assertion_passed, assertion_results = self.tester.assertion_engine.run_assertions(
                    result.response_body,
                    test_case.assertions
                )
                result.assertion_results = json.dumps(assertion_results, ensure_ascii=False)
            except Exception as e:
                # 断言执行失败，记录错误但不影响测试
                result.assertion_results = json.dumps([{
                    'passed': False,
                    'message': f'断言执行错误: {str(e)}'
                }], ensure_ascii=False)
                assertion_passed = False

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
                failed_assertions = [a for a in assertion_results if not a.get('passed', False)]
                for a in failed_assertions:
                    error_messages.append(f"断言失败: {a.get('description', a.get('path', ''))} - {a.get('message', '')}")
            result.error_message = '; '.join(error_messages)

        return result
