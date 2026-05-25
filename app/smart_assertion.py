"""
智能断言引擎
"""
import json
import re
from jsonpath_ng import parse


class SmartAssertion:
    """智能断言类"""

    def __init__(self):
        self.assertion_types = {
            'equals': self._assert_equals,
            'contains': self._assert_contains,
            'not_contains': self._assert_not_contains,
            'greater_than': self._assert_greater_than,
            'less_than': self._assert_less_than,
            'regex': self._assert_regex,
            'exists': self._assert_exists,
            'not_exists': self._assert_not_exists,
            'type': self._assert_type,
            'length': self._assert_length,
        }

    def run_assertions(self, response_body, assertions_json):
        """
        执行所有断言

        参数:
            response_body: 响应体（字符串）
            assertions_json: 断言规则（JSON字符串）

        返回:
            (all_passed, results)
            all_passed: 是否全部通过
            results: 断言结果列表
        """
        if not assertions_json:
            return True, []

        try:
            assertions = json.loads(assertions_json)
        except:
            return True, []

        if not isinstance(assertions, list):
            return True, []

        # 解析响应体
        try:
            response_data = json.loads(response_body)
        except:
            response_data = response_body

        results = []
        all_passed = True

        for assertion in assertions:
            result = self._run_single_assertion(response_data, assertion)
            results.append(result)
            if not result['passed']:
                all_passed = False

        return all_passed, results

    def _run_single_assertion(self, response_data, assertion):
        """执行单个断言"""
        assertion_type = assertion.get('type', 'equals')
        json_path = assertion.get('path', '')
        expected = assertion.get('expected')
        description = assertion.get('description', '')

        # 提取实际值
        actual = self._extract_value(response_data, json_path)

        # 执行断言
        assertion_func = self.assertion_types.get(assertion_type, self._assert_equals)
        passed, message = assertion_func(actual, expected)

        return {
            'type': assertion_type,
            'path': json_path,
            'expected': expected,
            'actual': actual,
            'passed': passed,
            'message': message,
            'description': description
        }

    def _extract_value(self, data, json_path):
        """使用JSONPath提取值"""
        if not json_path:
            return data

        try:
            # 使用jsonpath_ng解析
            jsonpath_expr = parse(json_path)
            matches = jsonpath_expr.find(data)
            if matches:
                if len(matches) == 1:
                    return matches[0].value
                return [match.value for match in matches]
            return None
        except:
            # 如果JSONPath失败，尝试简单的点号分隔
            try:
                keys = json_path.split('.')
                value = data
                for key in keys:
                    if isinstance(value, dict):
                        value = value.get(key)
                    elif isinstance(value, list) and key.isdigit():
                        value = value[int(key)]
                    else:
                        return None
                return value
            except:
                return None

    def _assert_equals(self, actual, expected):
        """断言：等于"""
        if actual == expected:
            return True, f"Value equals {expected}"
        return False, f"Expected {expected}, but got {actual}"

    def _assert_contains(self, actual, expected):
        """断言：包含"""
        if expected in str(actual):
            return True, f"Value contains '{expected}'"
        return False, f"Value does not contain '{expected}'"

    def _assert_not_contains(self, actual, expected):
        """断言：不包含"""
        if expected not in str(actual):
            return True, f"Value does not contain '{expected}'"
        return False, f"Value contains '{expected}'"

    def _assert_greater_than(self, actual, expected):
        """断言：大于"""
        try:
            if float(actual) > float(expected):
                return True, f"Value {actual} > {expected}"
            return False, f"Value {actual} is not greater than {expected}"
        except:
            return False, "Cannot compare values"

    def _assert_less_than(self, actual, expected):
        """断言：小于"""
        try:
            if float(actual) < float(expected):
                return True, f"Value {actual} < {expected}"
            return False, f"Value {actual} is not less than {expected}"
        except:
            return False, "Cannot compare values"

    def _assert_regex(self, actual, expected):
        """断言：正则匹配"""
        try:
            if re.match(expected, str(actual)):
                return True, f"Value matches pattern '{expected}'"
            return False, f"Value does not match pattern '{expected}'"
        except:
            return False, "Invalid regex pattern"

    def _assert_exists(self, actual, expected):
        """断言：字段存在"""
        if actual is not None:
            return True, "Field exists"
        return False, "Field does not exist"

    def _assert_not_exists(self, actual, expected):
        """断言：字段不存在"""
        if actual is None:
            return True, "Field does not exist"
        return False, "Field exists"

    def _assert_type(self, actual, expected):
        """断言：类型检查"""
        type_map = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'float': float,
            'boolean': bool,
            'array': list,
            'object': dict,
            'null': type(None)
        }

        expected_type = type_map.get(expected.lower())
        if expected_type is None:
            return False, f"Unknown type: {expected}"

        if isinstance(actual, expected_type):
            return True, f"Value is of type {expected}"
        return False, f"Expected type {expected}, but got {type(actual).__name__}"

    def _assert_length(self, actual, expected):
        """断言：长度检查"""
        try:
            actual_length = len(actual)
            expected_length = int(expected)
            if actual_length == expected_length:
                return True, f"Length is {expected_length}"
            return False, f"Expected length {expected_length}, but got {actual_length}"
        except:
            return False, "Cannot check length"
