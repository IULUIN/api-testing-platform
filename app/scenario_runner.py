"""
场景编排执行引擎
"""
import json
import time
from datetime import datetime
from app.api_tester import APITester
from app.models import (
    ScenarioResult, ScenarioStepResult, TestCase, get_session
)


def _extract_by_path(data, path):
    """
    从 JSON 数据中按路径提取值。
    支持简单点路径（如 id、data.token、items[0].id）和 $ 前缀（$.id）。
    """
    if path.startswith('$'):
        path = path[1:].lstrip('.')

    if not path:
        return data

    parts = []
    for segment in path.split('.'):
        # 处理数组下标，如 items[0]
        if '[' in segment:
            key, rest = segment.split('[', 1)
            idx = int(rest.rstrip(']'))
            parts.append(('key', key))
            parts.append(('idx', idx))
        else:
            parts.append(('key', segment))

    current = data
    for kind, val in parts:
        if current is None:
            return None
        try:
            if kind == 'key':
                current = current[val] if isinstance(current, dict) else None
            else:
                current = current[val] if isinstance(current, list) else None
        except (KeyError, IndexError, TypeError):
            return None
    return current


class ScenarioRunner:

    def __init__(self):
        self.tester = APITester()

    def run(self, scenario, steps):
        """
        执行场景。

        参数:
            scenario: Scenario 对象
            steps: 按 step_order 排序的 ScenarioStep 列表

        返回:
            (ScenarioResult, [ScenarioStepResult])
        """
        start_time = time.time()
        variables = {}          # 跨步骤共享的变量池
        step_results = []
        all_success = True

        db = get_session()
        try:
            scenario_result = ScenarioResult(
                scenario_id=scenario.id,
                scenario_name=scenario.name,
                total_steps=len(steps),
                success_steps=0,
                failed_steps=0,
                status='running',
            )
            db.add(scenario_result)
            db.flush()

            for step in steps:
                # 可选等待
                if step.wait_seconds and step.wait_seconds > 0:
                    time.sleep(step.wait_seconds)

                # 获取测试用例
                test_case = db.query(TestCase).get(step.test_case_id)
                if not test_case:
                    sr = ScenarioStepResult(
                        scenario_result_id=scenario_result.id,
                        step_order=step.step_order,
                        test_case_name=step.test_case_name or f'步骤{step.step_order}',
                        status='error',
                        error_message=f'测试用例 #{step.test_case_id} 不存在',
                        executed_at=datetime.now(),
                    )
                    db.add(sr)
                    step_results.append(sr)
                    all_success = False
                    scenario_result.failed_steps += 1
                    continue

                # 用变量池替换用例字段
                tester = APITester()
                response, response_time, error = tester.send_request(
                    method=test_case.method,
                    url=tester.replace_variables(test_case.url, variables),
                    headers=tester.replace_variables(test_case.headers, variables),
                    body=tester.replace_variables(test_case.body, variables),
                )

                step_result = ScenarioStepResult(
                    scenario_result_id=scenario_result.id,
                    step_order=step.step_order,
                    test_case_name=test_case.name,
                    response_time=response_time,
                    executed_at=datetime.now(),
                )

                if error:
                    step_result.status = 'error'
                    step_result.error_message = error
                    step_result.actual_status = 0
                    step_result.response_body = ''
                    all_success = False
                    scenario_result.failed_steps += 1
                else:
                    step_result.actual_status = response.status_code
                    try:
                        body_text = response.text
                        step_result.response_body = body_text[:5000] + ('...(已截断)' if len(body_text) > 5000 else '')
                    except Exception:
                        step_result.response_body = ''

                    # 状态码校验
                    if response.status_code == test_case.expected_status:
                        step_result.status = 'success'
                        scenario_result.success_steps += 1
                    else:
                        step_result.status = 'failed'
                        step_result.error_message = (
                            f'状态码不匹配：期望 {test_case.expected_status}，'
                            f'实际 {response.status_code}'
                        )
                        all_success = False
                        scenario_result.failed_steps += 1

                    # 变量提取
                    extracted = {}
                    if step.variable_extractions:
                        try:
                            extractions = json.loads(step.variable_extractions)
                            try:
                                resp_json = response.json()
                            except Exception:
                                resp_json = None

                            for rule in extractions:
                                var_name = rule.get('name', '').strip()
                                path = rule.get('path', '').strip()
                                if not var_name or not path:
                                    continue
                                if resp_json is not None:
                                    value = _extract_by_path(resp_json, path)
                                    if value is not None:
                                        variables[var_name] = value
                                        extracted[var_name] = value
                        except Exception:
                            pass

                    if extracted:
                        step_result.extracted_variables = json.dumps(extracted, ensure_ascii=False)

                db.add(step_result)
                step_results.append(step_result)

            # 汇总
            scenario_result.status = 'success' if all_success else 'failed'
            scenario_result.duration = time.time() - start_time
            db.commit()

            return scenario_result, step_results

        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
