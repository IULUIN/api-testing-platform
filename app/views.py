"""
路由视图
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_file, session, flash, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
from app.models import (TestCase, TestResult, DataSet, DataRow, BatchTestResult,
                        ScheduledTask, Scenario, ScenarioStep, ScenarioResult,
                        ScenarioStepResult, LoadTest, LoadTestResult, get_session, User)
from app.api_tester import APITester
from app.batch_tester import BatchTester
from app.data_parser import DataSetParser
from app.utils import get_statistics, format_json
from app import scheduler as task_scheduler
from app.report_generator import ReportGenerator
import json
import os
import tempfile
from flask_login import login_required, current_user

bp = Blueprint('main', __name__)

# 配置上传文件夹
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}


@bp.route('/examples')
def examples():
    """教程中心导航页"""
    return render_template('examples_index.html')


@bp.route('/examples/smart-assertions')
def smart_assertions_tutorial():
    """智能断言教程页"""
    session = get_session()
    try:
        # 获取示例数据
        try:
            examples = session.query(TestCase).filter_by(is_example=True).order_by(TestCase.id).limit(3).all()
        except:
            # 如果is_example字段不存在，返回空列表
            examples = []

        # 如果没有示例，创建示例
        if len(examples) < 3:
            try:
                create_assertion_examples(session)
                examples = session.query(TestCase).filter_by(is_example=True).order_by(TestCase.id).limit(3).all()
            except Exception as e:
                print(f"Failed to create examples: {e}")
                examples = []

        return render_template('smart_assertions_tutorial.html',
                             example1=examples[0] if len(examples) > 0 else None,
                             example2=examples[1] if len(examples) > 1 else None,
                             example3=examples[2] if len(examples) > 2 else None)
    finally:
        session.close()


def create_assertion_examples(session):
    """创建智能断言示例"""
    # 清除旧示例
    session.query(TestCase).filter_by(is_example=True).delete()

    examples = [
        TestCase(
            name="[示例] 基础断言 - 用户信息验证",
            url="https://jsonplaceholder.typicode.com/users/1",
            method="GET",
            expected_status=200,
            assertions=json.dumps([
                {
                    "type": "equals",
                    "path": "id",
                    "expected": 1,
                    "description": "用户ID应该是1"
                },
                {
                    "type": "exists",
                    "path": "name",
                    "description": "name字段应该存在"
                },
                {
                    "type": "type",
                    "path": "email",
                    "expected": "string",
                    "description": "email应该是字符串类型"
                }
            ], ensure_ascii=False),
            description="基础断言示例：验证用户信息API的基本字段",
            is_example=True
        ),
        TestCase(
            name="[示例] 进阶断言 - 数组验证",
            url="https://jsonplaceholder.typicode.com/posts",
            method="GET",
            expected_status=200,
            assertions=json.dumps([
                {
                    "type": "type",
                    "path": "$",
                    "expected": "array",
                    "description": "响应应该是数组"
                },
                {
                    "type": "length",
                    "path": "$",
                    "expected": 100,
                    "description": "应该返回100条数据"
                },
                {
                    "type": "exists",
                    "path": "[0].id",
                    "description": "第一条数据应该有id字段"
                },
                {
                    "type": "type",
                    "path": "[0].userId",
                    "expected": "integer",
                    "description": "userId应该是整数"
                }
            ], ensure_ascii=False),
            description="进阶断言示例：验证数组响应的类型、长度和内容",
            is_example=True
        ),
        TestCase(
            name="[示例] 高级断言 - 正则匹配",
            url="https://jsonplaceholder.typicode.com/users/1",
            method="GET",
            expected_status=200,
            assertions=json.dumps([
                {
                    "type": "regex",
                    "path": "email",
                    "expected": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                    "description": "邮箱格式应该正确"
                },
                {
                    "type": "contains",
                    "path": "address.street",
                    "expected": "Light",
                    "description": "地址应该包含Light"
                },
                {
                    "type": "greater_than",
                    "path": "id",
                    "expected": 0,
                    "description": "ID应该大于0"
                }
            ], ensure_ascii=False),
            description="高级断言示例：使用正则表达式验证邮箱格式",
            is_example=True
        )
    ]

    for example in examples:
        session.add(example)

    session.commit()


@bp.route('/')
@login_required
def index():
    """首页"""
    session = get_session()
    try:
        # 获取统计数据（排除示例，如果字段存在的话）
        try:
            total_cases = session.query(TestCase).filter_by(is_example=False).count()
        except:
            # 如果is_example字段不存在，统计所有用例
            total_cases = session.query(TestCase).count()

        total_results = session.query(TestResult).count()

        # 获取最近的测试结果
        recent_results = session.query(TestResult).order_by(
            TestResult.executed_at.desc()
        ).limit(10).all()

        stats = get_statistics(recent_results)

        # 当前用户信息
        current_user_info = {
            'username': current_user.username,
            'role': '管理员' if current_user.is_admin() else '普通用户'
        }

        return render_template('index.html',
                             total_cases=total_cases,
                             total_results=total_results,
                             stats=stats,
                             recent_results=recent_results,
                             current_user=current_user_info)
    finally:
        session.close()


@bp.route('/test-cases')
def test_cases():
    """测试用例列表（排除示例）"""
    session = get_session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = 20  # 每页显示20条

        # 尝试排除示例，如果字段不存在则显示所有
        try:
            query = session.query(TestCase).filter_by(is_example=False).order_by(TestCase.id.asc())
        except:
            query = session.query(TestCase).order_by(TestCase.id.asc())

        # 计算总数和总页数
        total = query.count()
        total_pages = (total + per_page - 1) // per_page

        # 获取当前页数据
        cases = query.offset((page - 1) * per_page).limit(per_page).all()

        return render_template('test_cases.html',
                             cases=cases,
                             page=page,
                             total_pages=total_pages,
                             total=total)
    finally:
        session.close()


@bp.route('/test-cases/add', methods=['GET', 'POST'])
def add_test_case():
    """添加测试用例"""
    if request.method == 'POST':
        session = get_session()
        try:
            # 获取表单数据
            name = request.form.get('name')
            url = request.form.get('url')
            method = request.form.get('method')
            headers = request.form.get('headers', '')
            body = request.form.get('body', '')
            expected_status = int(request.form.get('expected_status', 200))
            assertions = request.form.get('assertions', '')
            description = request.form.get('description', '')

            # 创建测试用例
            test_case = TestCase(
                name=name,
                url=url,
                method=method,
                headers=headers,
                body=body,
                expected_status=expected_status,
                assertions=assertions,
                description=description
            )

            session.add(test_case)
            session.commit()

            return redirect(url_for('main.test_cases'))
        finally:
            session.close()

    return render_template('add_test_case.html')


@bp.route('/test-cases/<int:case_id>/edit', methods=['GET', 'POST'])
def edit_test_case(case_id):
    """编辑测试用例"""
    session = get_session()
    try:
        test_case = session.query(TestCase).get(case_id)
        if not test_case:
            return "测试用例不存在", 404

        if request.method == 'POST':
            # 更新数据
            test_case.name = request.form.get('name')
            test_case.url = request.form.get('url')
            test_case.method = request.form.get('method')
            test_case.headers = request.form.get('headers', '')
            test_case.body = request.form.get('body', '')
            test_case.expected_status = int(request.form.get('expected_status', 200))
            test_case.description = request.form.get('description', '')

            session.commit()
            return redirect(url_for('main.test_cases'))

        return render_template('edit_test_case.html', case=test_case)
    finally:
        session.close()


@bp.route('/test-cases/<int:case_id>/delete', methods=['POST'])
def delete_test_case(case_id):
    """删除测试用例"""
    session = get_session()
    try:
        test_case = session.query(TestCase).get(case_id)
        if test_case:
            session.delete(test_case)
            session.commit()
        return redirect(url_for('main.test_cases'))
    finally:
        session.close()


@bp.route('/test-cases/<int:case_id>/run', methods=['POST'])
def run_test_case(case_id):
    """执行测试用例"""
    session = get_session()
    try:
        test_case = session.query(TestCase).get(case_id)
        if not test_case:
            return jsonify({'error': '测试用例不存在'}), 404

        # 获取环境ID（如果提供）
        env_id = request.json.get('env_id') if request.is_json else None

        # 获取环境配置
        environment = None
        if env_id:
            try:
                env = session.query(Environment).get(env_id)
                if env:
                    environment = env.to_dict()
            except:
                pass
        else:
            # 使用默认环境
            try:
                default_env = session.query(Environment).filter_by(is_default=True).first()
                if default_env:
                    environment = default_env.to_dict()
            except:
                pass

        # 执行测试
        tester = APITester(environment=environment)
        result = tester.run_test_case(test_case)

        # 保存结果
        session.add(result)
        session.commit()

        return jsonify({
            'success': True,
            'result': result.to_dict()
        })
    finally:
        session.close()


@bp.route('/reports')
def reports():
    """测试报告"""
    session = get_session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = 50  # 每页显示50条

        # 查询测试结果
        query = session.query(TestResult).order_by(TestResult.executed_at.desc())

        # 计算总数和总页数
        total = query.count()
        total_pages = (total + per_page - 1) // per_page

        # 获取当前页数据
        results = query.offset((page - 1) * per_page).limit(per_page).all()

        stats = get_statistics(results)

        # 转换为字典列表，供JavaScript使用
        results_dict = [result.to_dict() for result in results]

        return render_template('reports.html',
                             results=results,
                             results_json=results_dict,
                             stats=stats,
                             page=page,
                             per_page=per_page,
                             total_pages=total_pages,
                             total=total)
    finally:
        session.close()


@bp.route('/api/test-cases')
def api_test_cases():
    """API: 获取测试用例列表"""
    session = get_session()
    try:
        cases = session.query(TestCase).all()
        return jsonify([case.to_dict() for case in cases])
    finally:
        session.close()


@bp.route('/api/test-results')
def api_test_results():
    """API: 获取测试结果列表"""
    session = get_session()
    try:
        results = session.query(TestResult).order_by(
            TestResult.executed_at.desc()
        ).limit(100).all()
        return jsonify([result.to_dict() for result in results])
    finally:
        session.close()


# ==================== 数据集管理路由 ====================

@bp.route('/data-sets')
def data_sets():
    """数据集列表"""
    session = get_session()
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = 20

        # 获取所有数据集（排除示例）
        try:
            query = session.query(DataSet).filter_by(is_example=False).order_by(DataSet.id.asc())
        except:
            # 如果表不存在，返回空列表
            return render_template('data_sets.html', data_sets=[], page=1, total_pages=1, total=0)

        # 计算总数和总页数
        total = query.count()
        total_pages = (total + per_page - 1) // per_page

        # 获取当前页数据
        data_sets = query.offset((page - 1) * per_page).limit(per_page).all()

        return render_template('data_sets.html',
                             data_sets=data_sets,
                             page=page,
                             total_pages=total_pages,
                             total=total)
    finally:
        session.close()


@bp.route('/data-sets/upload', methods=['GET', 'POST'])
def upload_data_set():
    """上传数据集"""
    if request.method == 'POST':
        session = get_session()
        parser = DataSetParser()

        try:
            # 获取表单数据
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            file = request.files.get('file')

            # 验证必填字段
            if not name:
                return render_template('upload_data_set.html',
                                     error="请输入数据集名称")

            if not file:
                return render_template('upload_data_set.html',
                                     error="请选择文件")

            # 验证文件
            is_valid, error_msg = parser.validate_file(file)
            if not is_valid:
                return render_template('upload_data_set.html',
                                     error=error_msg)

            # 保存文件到临时目录
            filename = secure_filename(file.filename)
            temp_path = os.path.join(UPLOAD_FOLDER, filename)

            try:
                file.save(temp_path)

                # 解析文件
                success, data, error_msg = parser.parse_file(temp_path)

                if not success:
                    return render_template('upload_data_set.html',
                                         error=f"文件解析失败: {error_msg}")

                # 验证数据
                is_valid, error_msg = parser.validate_data(data)
                if not is_valid:
                    return render_template('upload_data_set.html',
                                         error=f"数据验证失败: {error_msg}")

                # 创建数据集
                data_set = DataSet(
                    name=name,
                    description=description,
                    file_name=filename,
                    data_count=len(data)
                )
                session.add(data_set)
                session.flush()  # 获取ID

                # 保存数据行
                for idx, row_data in enumerate(data, start=1):
                    data_row = DataRow(
                        data_set_id=data_set.id,
                        row_number=idx,
                        data_json=json.dumps(row_data, ensure_ascii=False)
                    )
                    session.add(data_row)

                session.commit()

                return redirect(url_for('main.data_sets'))

            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass

        except Exception as e:
            session.rollback()
            return render_template('upload_data_set.html',
                                 error=f"上传失败: {str(e)}")
        finally:
            session.close()

    return render_template('upload_data_set.html')


@bp.route('/data-sets/<int:ds_id>/view')
def view_data_set(ds_id):
    """查看数据集详情"""
    session = get_session()
    try:
        data_set = session.query(DataSet).get(ds_id)
        if not data_set:
            return redirect(url_for('main.data_sets'))

        # 获取数据行
        data_rows = session.query(DataRow).filter_by(
            data_set_id=ds_id
        ).order_by(DataRow.row_number).all()

        # 解析数据
        parsed_data = []
        headers = []

        for row in data_rows:
            try:
                row_dict = json.loads(row.data_json)
                parsed_data.append(row_dict)

                # 收集所有列名
                for key in row_dict.keys():
                    if key not in headers:
                        headers.append(key)
            except:
                pass

        return render_template('view_data_set.html',
                             data_set=data_set,
                             headers=headers,
                             data=parsed_data)
    finally:
        session.close()


@bp.route('/data-sets/<int:ds_id>/use')
def use_data_set(ds_id):
    """选择测试用例使用数据集"""
    session = get_session()
    try:
        data_set = session.query(DataSet).get(ds_id)
        if not data_set:
            return redirect(url_for('main.data_sets'))

        # 获取所有测试用例（排除示例）
        try:
            test_cases = session.query(TestCase).filter_by(
                is_example=False
            ).order_by(TestCase.created_at.desc()).all()
        except:
            test_cases = session.query(TestCase).order_by(
                TestCase.created_at.desc()
            ).all()

        return render_template('use_data_set.html',
                             data_set=data_set,
                             test_cases=test_cases)
    finally:
        session.close()


@bp.route('/data-sets/<int:ds_id>/run/<int:case_id>', methods=['POST'])
def run_batch_test(ds_id, case_id):
    """执行批量测试"""
    session = get_session()
    batch_tester = BatchTester()

    try:
        # 获取数据集和测试用例
        data_set = session.query(DataSet).get(ds_id)
        test_case = session.query(TestCase).get(case_id)

        if not data_set or not test_case:
            return jsonify({
                'success': False,
                'error': '数据集或测试用例不存在'
            }), 404

        # 获取数据行
        data_rows = session.query(DataRow).filter_by(
            data_set_id=ds_id
        ).order_by(DataRow.row_number).all()

        if not data_rows:
            return jsonify({
                'success': False,
                'error': '数据集为空'
            }), 400

        # 执行批量测试
        results, summary = batch_tester.run_batch_test(test_case, data_rows)

        # 计算平均响应时间
        total_response_time = sum(r.response_time for r in results if r.response_time)
        avg_response_time = round(total_response_time / len(results) * 1000, 2) if results else 0  # 转换为毫秒

        # 保存测试结果
        for result in results:
            session.add(result)

        # 保存批量测试汇总
        batch_result = BatchTestResult(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            data_set_id=data_set.id,
            data_set_name=data_set.name,
            total_count=summary['total'],
            success_count=summary['success'],
            failed_count=summary['failed'],
            error_count=summary['error'],
            avg_response_time=avg_response_time
        )
        session.add(batch_result)

        session.commit()

        return jsonify({
            'success': True,
            'batch_result_id': batch_result.id,
            'summary': summary
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@bp.route('/batch-results/<int:batch_id>')
def view_batch_result(batch_id):
    """查看批量测试结果"""
    session = get_session()
    try:
        batch_result = session.query(BatchTestResult).get(batch_id)
        if not batch_result:
            return redirect(url_for('main.data_sets'))

        # 获取详细结果
        results = session.query(TestResult).filter(
            TestResult.test_case_id == batch_result.test_case_id,
            TestResult.executed_at >= batch_result.executed_at
        ).order_by(TestResult.executed_at).limit(batch_result.total_count).all()

        return render_template('batch_result.html',
                             batch_result=batch_result,
                             results=[r.to_dict() for r in results])
    finally:
        session.close()


@bp.route('/data-sets/<int:ds_id>/delete', methods=['POST'])
def delete_data_set(ds_id):
    """删除数据集"""
    session = get_session()
    try:
        # 删除数据集
        data_set = session.query(DataSet).get(ds_id)
        if data_set:
            # 删除关联的数据行
            session.query(DataRow).filter_by(data_set_id=ds_id).delete()
            # 删除数据集
            session.delete(data_set)
            session.commit()

        return redirect(url_for('main.data_sets'))
    except Exception as e:
        session.rollback()
        return redirect(url_for('main.data_sets'))
    finally:
        session.close()


@bp.route('/examples/parameterized-testing')
def parameterized_testing_tutorial():
    """参数化测试教程页"""
    session = get_session()
    try:
        # 获取示例数据集
        try:
            example_datasets = session.query(DataSet).filter_by(is_example=True).all()
        except:
            example_datasets = []

        # 如果没有示例，创建示例
        if len(example_datasets) < 2:
            try:
                create_example_data_sets(session)
                example_datasets = session.query(DataSet).filter_by(is_example=True).all()
            except Exception as e:
                print(f"Failed to create example datasets: {e}")
                example_datasets = []

        # 获取每个数据集的数据
        datasets_with_data = []
        for ds in example_datasets:
            try:
                rows = session.query(DataRow).filter_by(data_set_id=ds.id).order_by(DataRow.row_number).all()
                data = []
                headers = []
                for row in rows:
                    row_dict = json.loads(row.data_json)
                    data.append(row_dict)
                    for key in row_dict.keys():
                        if key not in headers:
                            headers.append(key)
                datasets_with_data.append({
                    'dataset': ds,
                    'headers': headers,
                    'data': data
                })
            except:
                pass

        return render_template('parameterized_tutorial.html',
                             datasets_with_data=datasets_with_data)
    finally:
        session.close()


@bp.route('/examples/scheduled-tasks')
def scheduled_tasks_tutorial():
    """定时任务教程页"""
    return render_template('scheduled_tasks_tutorial.html')


@bp.route('/examples/scenario-orchestration')
def scenario_orchestration_tutorial():
    """场景编排教程页"""
    return render_template('scenario_orchestration_tutorial.html')


@bp.route('/examples/load-testing')
def load_testing_tutorial():
    """并发压测教程页"""
    return render_template('load_testing_tutorial.html')


@bp.route('/examples/performance-monitoring')
def performance_monitoring_tutorial():
    """性能监控教程页"""
    return render_template('performance_monitoring_tutorial.html')



def create_example_data_sets(session):
    """创建示例数据集"""
    # 清除旧示例
    session.query(DataSet).filter_by(is_example=True).delete()
    session.query(DataRow).filter(
        DataRow.data_set_id.in_(
            session.query(DataSet.id).filter_by(is_example=True)
        )
    ).delete()

    # 示例1：用户测试数据
    example1_data = [
        {"user_id": "1", "username": "test1", "email": "test1@example.com"},
        {"user_id": "2", "username": "test2", "email": "test2@example.com"},
        {"user_id": "3", "username": "test3", "email": "test3@example.com"},
    ]

    dataset1 = DataSet(
        name="[示例] 用户测试数据",
        description="用于测试用户API的示例数据集，包含3个用户的信息",
        file_name="users_example.xlsx",
        data_count=len(example1_data),
        is_example=True
    )
    session.add(dataset1)
    session.flush()

    for idx, row_data in enumerate(example1_data, start=1):
        data_row = DataRow(
            data_set_id=dataset1.id,
            row_number=idx,
            data_json=json.dumps(row_data, ensure_ascii=False)
        )
        session.add(data_row)

    # 示例2：登录测试数据
    example2_data = [
        {"username": "admin", "password": "admin123", "expected_code": "200"},
        {"username": "test", "password": "test123", "expected_code": "200"},
        {"username": "invalid", "password": "wrong", "expected_code": "401"},
    ]

    dataset2 = DataSet(
        name="[示例] 登录测试数据",
        description="用于测试登录功能的示例数据集，包含正常和异常情况",
        file_name="login_example.xlsx",
        data_count=len(example2_data),
        is_example=True
    )
    session.add(dataset2)
    session.flush()

    for idx, row_data in enumerate(example2_data, start=1):
        data_row = DataRow(
            data_set_id=dataset2.id,
            row_number=idx,
            data_json=json.dumps(row_data, ensure_ascii=False)
        )
        session.add(data_row)

    session.commit()


@bp.route('/test-cases/smart-create-page')
def smart_create_page():
    """智能创建测试用例页面"""
    return render_template('smart_create.html')


@bp.route('/test-cases/smart-create', methods=['POST'])
def smart_create():
    """智能创建测试用例（保存）"""
    session = get_session()
    try:
        data = request.get_json()

        # 创建测试用例
        test_case = TestCase(
            name=data.get('name'),
            url=data.get('url'),
            method=data.get('method'),
            headers=data.get('headers', ''),
            body=data.get('body', ''),
            expected_status=data.get('expected_status', 200),
            assertions=data.get('assertions', ''),
            description=data.get('description', '')
        )

        session.add(test_case)
        session.commit()

        return jsonify({
            'success': True,
            'case_id': test_case.id
        })

    except Exception as e:
        session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        session.close()


@bp.route('/test-cases/doc-generator')
def doc_generator_page():
    """测试用例文档生成器页面"""
    return render_template('doc_generator.html')


@bp.route('/test-cases/generate-doc', methods=['POST'])
def generate_doc():
    """生成测试用例文档"""
    try:
        from app.doc_generator import TestCaseDocGenerator

        data = request.get_json()

        # 创建生成器
        generator = TestCaseDocGenerator()

        # 生成测试用例
        cases = generator.generate_test_cases(data)

        # 根据格式导出
        file_format = data.get('format', 'excel')
        save_path = data.get('save_path', '')

        if file_format == 'excel':
            file_path = generator.export_to_excel(cases, data, save_path if save_path else None)
        else:
            file_path = generator.export_to_markdown(cases, data, save_path if save_path else None)

        return jsonify({
            'success': True,
            'file_path': file_path,
            'case_count': len(cases),
            'download_url': f'/download/{os.path.basename(file_path)}'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/download/<filename>')
def download_file(filename):
    """下载生成的文件"""
    from flask import send_from_directory
    output_dir = os.path.join(os.getcwd(), 'outputs')
    return send_from_directory(output_dir, filename, as_attachment=True)


# ==================== 环境管理路由 ====================

@bp.route('/environments')
def environments():
    """环境管理页面"""
    session = get_session()
    try:
        try:
            envs = session.query(Environment).order_by(Environment.is_default.desc(), Environment.created_at.desc()).all()
        except:
            envs = []
        return render_template('environments.html', environments=envs)
    finally:
        session.close()


@bp.route('/environments/add', methods=['POST'])
def add_environment():
    """添加环境"""
    session = get_session()
    try:
        name = request.form.get('name')
        base_url = request.form.get('base_url')
        description = request.form.get('description', '')
        variables = request.form.get('variables', '')
        is_default = request.form.get('is_default') == 'on'

        # 如果设为默认，取消其他环境的默认状态
        if is_default:
            session.query(Environment).update({'is_default': False})

        env = Environment(
            name=name,
            base_url=base_url,
            description=description,
            variables=variables,
            is_default=is_default
        )

        session.add(env)
        session.commit()

        return redirect(url_for('main.environments'))
    except Exception as e:
        session.rollback()
        return redirect(url_for('main.environments'))
    finally:
        session.close()


@bp.route('/environments/<int:env_id>/edit', methods=['POST'])
def edit_environment(env_id):
    """编辑环境"""
    session = get_session()
    try:
        env = session.query(Environment).get(env_id)
        if env:
            env.name = request.form.get('name')
            env.base_url = request.form.get('base_url')
            env.description = request.form.get('description', '')
            env.variables = request.form.get('variables', '')
            is_default = request.form.get('is_default') == 'on'

            # 如果设为默认，取消其他环境的默认状态
            if is_default and not env.is_default:
                session.query(Environment).filter(Environment.id != env_id).update({'is_default': False})
                env.is_default = True

            session.commit()

        return redirect(url_for('main.environments'))
    except Exception as e:
        session.rollback()
        return redirect(url_for('main.environments'))
    finally:
        session.close()


@bp.route('/environments/<int:env_id>/delete', methods=['POST'])
def delete_environment(env_id):
    """删除环境"""
    session = get_session()
    try:
        env = session.query(Environment).get(env_id)
        if env:
            session.delete(env)
            session.commit()
        return redirect(url_for('main.environments'))
    except Exception as e:
        session.rollback()
        return redirect(url_for('main.environments'))
    finally:
        session.close()


@bp.route('/environments/<int:env_id>/set-default', methods=['POST'])
def set_default_environment(env_id):
    """设置默认环境"""
    session = get_session()
    try:
        # 取消所有环境的默认状态
        session.query(Environment).update({'is_default': False})

        # 设置指定环境为默认
        env = session.query(Environment).get(env_id)
        if env:
            env.is_default = True
            session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '环境不存在'}), 404
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@bp.route('/api/environments')
def api_environments():
    """获取环境列表API"""
    session = get_session()
    try:
        try:
            envs = session.query(Environment).order_by(Environment.is_default.desc(), Environment.created_at.desc()).all()
            return jsonify({
                'success': True,
                'environments': [env.to_dict() for env in envs]
            })
        except:
            return jsonify({
                'success': True,
                'environments': []
            })
    finally:
        session.close()


# ==================== 定时任务管理 ====================

@bp.route('/scheduled-tasks')
def scheduled_tasks():
    """定时任务列表页"""
    session = get_session()
    try:
        tasks = session.query(ScheduledTask).order_by(ScheduledTask.created_at.desc()).all()

        # 添加cron描述的辅助函数
        def get_cron_description(cron_expr):
            """将cron表达式转换为中文描述"""
            descriptions = {
                '*/5 * * * *': '每5分钟',
                '*/10 * * * *': '每10分钟',
                '*/15 * * * *': '每15分钟',
                '*/30 * * * *': '每30分钟',
                '0 * * * *': '每小时',
                '0 */2 * * *': '每2小时',
                '0 */6 * * *': '每6小时',
                '0 0 * * *': '每天0:00',
                '0 9 * * *': '每天9:00',
                '0 12 * * *': '每天12:00',
                '0 18 * * *': '每天18:00',
                '0 9 * * 1-5': '工作日9:00',
                '0 0 * * 0': '每周日0:00',
                '0 0 1 * *': '每月1号0:00',
            }
            return descriptions.get(cron_expr, '自定义')

        return render_template('scheduled_tasks.html', tasks=tasks, get_cron_description=get_cron_description)
    finally:
        session.close()


@bp.route('/scheduled-tasks/add', methods=['GET', 'POST'])
def add_scheduled_task():
    """添加定时任务"""
    if request.method == 'POST':
        session = get_session()
        try:
            test_case_id = int(request.form.get('test_case_id'))
            cron_expression = request.form.get('cron_expression')

            # 获取测试用例信息
            test_case = session.query(TestCase).get(test_case_id)
            if not test_case:
                return jsonify({'success': False, 'error': '测试用例不存在'}), 404

            # 计算下次执行时间
            next_run = task_scheduler.get_next_run_time(cron_expression)
            if not next_run:
                return jsonify({'success': False, 'error': 'Cron表达式格式错误'}), 400

            # 创建定时任务
            task = ScheduledTask(
                test_case_id=test_case_id,
                test_case_name=test_case.name,
                cron_expression=cron_expression,
                is_active=True,
                next_run_at=next_run
            )
            session.add(task)
            session.commit()

            # 添加到调度器
            task_scheduler.add_scheduled_task(
                task.id,
                test_case_id,
                test_case.name,
                cron_expression
            )

            return jsonify({'success': True, 'task_id': task.id})
        except Exception as e:
            session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            session.close()

    # GET请求，显示添加表单
    session = get_session()
    try:
        # 获取所有非示例的测试用例
        test_cases = session.query(TestCase).filter_by(is_example=False).order_by(TestCase.created_at.desc()).all()
        return render_template('add_scheduled_task.html', test_cases=test_cases)
    finally:
        session.close()


@bp.route('/scheduled-tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_scheduled_task(task_id):
    """启用/禁用定时任务"""
    session = get_session()
    try:
        task = session.query(ScheduledTask).get(task_id)
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404

        # 切换状态
        task.is_active = not task.is_active
        session.commit()

        # 更新调度器
        if task.is_active:
            # 启用任务
            next_run = task_scheduler.get_next_run_time(task.cron_expression)
            if next_run:
                task.next_run_at = next_run
                session.commit()
            task_scheduler.add_scheduled_task(
                task.id,
                task.test_case_id,
                task.test_case_name,
                task.cron_expression
            )
        else:
            # 禁用任务
            task_scheduler.pause_scheduled_task(task.id)

        return jsonify({'success': True, 'is_active': task.is_active})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@bp.route('/scheduled-tasks/<int:task_id>/delete', methods=['POST'])
def delete_scheduled_task(task_id):
    """删除定时任务"""
    session = get_session()
    try:
        task = session.query(ScheduledTask).get(task_id)
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404

        # 从调度器中移除
        task_scheduler.remove_scheduled_task(task.id)

        # 从数据库中删除
        session.delete(task)
        session.commit()

        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@bp.route('/scheduled-tasks/<int:task_id>/run', methods=['POST'])
def run_scheduled_task_now(task_id):
    """立即执行定时任务"""
    session = get_session()
    try:
        task = session.query(ScheduledTask).get(task_id)
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404

        # 立即执行任务
        task_scheduler.execute_scheduled_test(task.id)

        return jsonify({'success': True, 'message': '任务已执行'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


# ==================== 性能报告 ====================

@bp.route('/performance-report')
def performance_report_list():
    """性能报告列表"""
    session = get_session()
    try:
        # 获取所有批量测试结果
        batch_results = session.query(BatchTestResult).order_by(BatchTestResult.executed_at.desc()).all()
        return render_template('performance_report_list.html', batch_results=batch_results)
    finally:
        session.close()


@bp.route('/performance-report/<int:batch_id>')
def view_performance_report(batch_id):
    """查看性能报告"""
    session = get_session()
    try:
        # 获取批量测试结果
        batch_result = session.query(BatchTestResult).get(batch_id)
        if not batch_result:
            return "Batch result not found", 404

        # 获取该批次的所有测试结果
        test_results = session.query(TestResult).filter_by(
            test_case_id=batch_result.test_case_id
        ).order_by(TestResult.executed_at.desc()).limit(batch_result.total_count).all()

        # 转换为字典列表
        results_data = []
        for result in test_results:
            results_data.append({
                'response_time': result.response_time,
                'status': result.status,
                'executed_at': result.executed_at
            })

        # 生成报告
        generator = ReportGenerator(results_data)
        report_data = generator.generate_report_data()

        return render_template('performance_report.html',
                             summary=report_data['summary'],
                             chart_data=report_data['chart_data'],
                             batch_result=batch_result)
    finally:
        session.close()


@bp.route('/test-results/<int:case_id>/performance-report')
def test_case_performance_report(case_id):
    """测试用例的性能报告"""
    session = get_session()
    try:
        # 获取测试用例
        test_case = session.query(TestCase).get(case_id)
        if not test_case:
            return "Test case not found", 404

        # 获取该用例的所有测试结果（最近100条）
        test_results = session.query(TestResult).filter_by(
            test_case_id=case_id
        ).order_by(TestResult.executed_at.desc()).limit(100).all()

        if not test_results:
            return render_template('no_data.html', message="No test results available for this test case")

        # 转换为字典列表
        results_data = []
        for result in test_results:
            results_data.append({
                'response_time': result.response_time,
                'status': result.status,
                'executed_at': result.executed_at
            })

        # 生成报告
        generator = ReportGenerator(results_data)
        report_data = generator.generate_report_data()

        return render_template('performance_report.html',
                             summary=report_data['summary'],
                             chart_data=report_data['chart_data'],
                             test_case=test_case)
    finally:
        session.close()


# ==================== 场景编排 ====================

@bp.route('/scenarios')
def scenarios():
    """场景列表"""
    session = get_session()
    try:
        items = session.query(Scenario).order_by(Scenario.created_at.desc()).all()
        # 为每个场景附加步骤数和最近执行结果
        data = []
        for s in items:
            step_count = session.query(ScenarioStep).filter_by(scenario_id=s.id).count()
            last_result = session.query(ScenarioResult).filter_by(
                scenario_id=s.id
            ).order_by(ScenarioResult.executed_at.desc()).first()
            data.append({
                'scenario': s,
                'step_count': step_count,
                'last_result': last_result,
            })
        return render_template('scenarios.html', data=data)
    finally:
        session.close()


@bp.route('/scenarios/add', methods=['GET', 'POST'])
def add_scenario():
    """新建场景"""
    session = get_session()
    try:
        if request.method == 'POST':
            payload = request.get_json()
            name = payload.get('name', '').strip()
            description = payload.get('description', '').strip()
            steps_raw = payload.get('steps', [])

            if not name:
                return jsonify({'success': False, 'error': '场景名称不能为空'}), 400
            if not steps_raw:
                return jsonify({'success': False, 'error': '至少需要一个步骤'}), 400

            scenario = Scenario(name=name, description=description)
            session.add(scenario)
            session.flush()

            for idx, s in enumerate(steps_raw, start=1):
                tc_id = s.get('test_case_id')
                if not tc_id:
                    continue
                tc = session.query(TestCase).get(int(tc_id))
                step = ScenarioStep(
                    scenario_id=scenario.id,
                    step_order=idx,
                    test_case_id=int(tc_id),
                    test_case_name=tc.name if tc else f'用例#{tc_id}',
                    variable_extractions=json.dumps(
                        s.get('variable_extractions', []), ensure_ascii=False
                    ),
                    wait_seconds=float(s.get('wait_seconds', 0) or 0),
                )
                session.add(step)

            session.commit()
            return jsonify({'success': True, 'scenario_id': scenario.id})

        # GET — 渲染表单
        try:
            test_cases = session.query(TestCase).filter_by(
                is_example=False
            ).order_by(TestCase.created_at.desc()).all()
        except Exception:
            test_cases = session.query(TestCase).order_by(TestCase.created_at.desc()).all()
        return render_template('add_scenario.html',
                               test_cases=[tc.to_dict() for tc in test_cases],
                               steps=[])
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@bp.route('/scenarios/<int:scenario_id>/edit', methods=['GET', 'POST'])
def edit_scenario(scenario_id):
    """编辑场景"""
    session = get_session()
    try:
        scenario = session.query(Scenario).get(scenario_id)
        if not scenario:
            return redirect(url_for('main.scenarios'))

        if request.method == 'POST':
            payload = request.get_json()
            scenario.name = payload.get('name', scenario.name).strip()
            scenario.description = payload.get('description', '').strip()
            steps_raw = payload.get('steps', [])

            # 删除旧步骤
            session.query(ScenarioStep).filter_by(scenario_id=scenario_id).delete()

            for idx, s in enumerate(steps_raw, start=1):
                tc_id = s.get('test_case_id')
                if not tc_id:
                    continue
                tc = session.query(TestCase).get(int(tc_id))
                step = ScenarioStep(
                    scenario_id=scenario.id,
                    step_order=idx,
                    test_case_id=int(tc_id),
                    test_case_name=tc.name if tc else f'用例#{tc_id}',
                    variable_extractions=json.dumps(
                        s.get('variable_extractions', []), ensure_ascii=False
                    ),
                    wait_seconds=float(s.get('wait_seconds', 0) or 0),
                )
                session.add(step)

            session.commit()
            return jsonify({'success': True})

        steps = session.query(ScenarioStep).filter_by(
            scenario_id=scenario_id
        ).order_by(ScenarioStep.step_order).all()
        try:
            test_cases = session.query(TestCase).filter_by(
                is_example=False
            ).order_by(TestCase.created_at.desc()).all()
        except Exception:
            test_cases = session.query(TestCase).order_by(TestCase.created_at.desc()).all()
        return render_template('add_scenario.html',
                               scenario=scenario,
                               steps=[s.to_dict() for s in steps],
                               test_cases=[tc.to_dict() for tc in test_cases])
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@bp.route('/scenarios/<int:scenario_id>/delete', methods=['POST'])
def delete_scenario(scenario_id):
    """删除场景"""
    session = get_session()
    try:
        scenario = session.query(Scenario).get(scenario_id)
        if scenario:
            session.query(ScenarioStep).filter_by(scenario_id=scenario_id).delete()
            session.query(ScenarioResult).filter_by(scenario_id=scenario_id).delete()
            session.delete(scenario)
            session.commit()
        return redirect(url_for('main.scenarios'))
    except Exception as e:
        session.rollback()
        return redirect(url_for('main.scenarios'))
    finally:
        session.close()


@bp.route('/scenarios/<int:scenario_id>/run', methods=['POST'])
def run_scenario(scenario_id):
    """执行场景"""
    from app.scenario_runner import ScenarioRunner
    session = get_session()
    try:
        scenario = session.query(Scenario).get(scenario_id)
        if not scenario:
            return jsonify({'success': False, 'error': '场景不存在'}), 404

        steps = session.query(ScenarioStep).filter_by(
            scenario_id=scenario_id
        ).order_by(ScenarioStep.step_order).all()

        if not steps:
            return jsonify({'success': False, 'error': '场景没有步骤'}), 400

        runner = ScenarioRunner()
        scenario_result, _ = runner.run(scenario, steps)

        return jsonify({
            'success': True,
            'result_id': scenario_result.id,
            'status': scenario_result.status,
            'success_steps': scenario_result.success_steps,
            'failed_steps': scenario_result.failed_steps,
            'total_steps': scenario_result.total_steps,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()


@bp.route('/scenarios/results/<int:result_id>')
def view_scenario_result(result_id):
    """查看场景执行结果"""
    session = get_session()
    try:
        result = session.query(ScenarioResult).get(result_id)
        if not result:
            return redirect(url_for('main.scenarios'))

        step_results = session.query(ScenarioStepResult).filter_by(
            scenario_result_id=result_id
        ).order_by(ScenarioStepResult.step_order).all()

        return render_template('scenario_result.html',
                               result=result,
                               step_results=[sr.to_dict() for sr in step_results])
    finally:
        session.close()


@bp.route('/scenarios/<int:scenario_id>/history')
def scenario_history(scenario_id):
    """场景执行历史"""
    session = get_session()
    try:
        scenario = session.query(Scenario).get(scenario_id)
        if not scenario:
            return redirect(url_for('main.scenarios'))

        history = session.query(ScenarioResult).filter_by(
            scenario_id=scenario_id
        ).order_by(ScenarioResult.executed_at.desc()).limit(50).all()

        return render_template('scenario_history.html',
                               scenario=scenario,
                               history=history)
    finally:
        session.close()


# ==================== 并发压测路由 ====================

@bp.route('/load-tests')
def load_tests():
    """并发压测列表"""
    session = get_session()
    try:
        tests = session.query(LoadTest).order_by(LoadTest.created_at.desc()).all()
        return render_template('load_tests.html', tests=tests)
    finally:
        session.close()


@bp.route('/load-tests/add', methods=['GET', 'POST'])
def add_load_test():
    """新建压测任务"""
    session = get_session()
    try:
        if request.method == 'POST':
            # 获取表单数据
            name = request.form.get('name')
            test_case_id = request.form.get('test_case_id')
            concurrent_users = int(request.form.get('concurrent_users', 10))
            duration = int(request.form.get('duration', 60))
            ramp_up_time = int(request.form.get('ramp_up_time', 0))
            description = request.form.get('description', '')

            # 获取测试用例名称
            test_case = session.query(TestCase).get(test_case_id)
            if not test_case:
                return "测试用例不存在", 400

            # 获取定时配置
            is_scheduled = request.form.get('is_scheduled') == '1'
            schedule_cron = request.form.get('schedule_cron', '').strip()

            # 创建压测任务
            load_test = LoadTest(
                name=name,
                test_case_id=test_case_id,
                test_case_name=test_case.name,
                concurrent_users=concurrent_users,
                duration=duration,
                ramp_up_time=ramp_up_time,
                description=description,
                is_scheduled=is_scheduled,
                schedule_cron=schedule_cron if is_scheduled else None
            )
            session.add(load_test)
            session.commit()

            # 如果启用了定时，注册定时任务
            if is_scheduled and schedule_cron:
                register_scheduled_load_test(load_test.id, schedule_cron)

            return redirect(url_for('main.load_tests'))

        # GET请求，显示表单
        test_cases = session.query(TestCase).filter_by(is_example=False).all()
        return render_template('add_load_test.html', test_cases=test_cases)
    finally:
        session.close()


@bp.route('/load-tests/<int:test_id>/delete', methods=['POST'])
def delete_load_test(test_id):
    """删除压测任务"""
    session = get_session()
    try:
        load_test = session.query(LoadTest).get(test_id)
        if load_test:
            session.delete(load_test)
            session.commit()
        return redirect(url_for('main.load_tests'))
    finally:
        session.close()


@bp.route('/load-tests/<int:test_id>/edit', methods=['GET', 'POST'])
def edit_load_test(test_id):
    """编辑压测任务"""
    session = get_session()
    try:
        load_test = session.query(LoadTest).get(test_id)
        if not load_test:
            return "压测任务不存在", 404

        if request.method == 'POST':
            # 更新表单数据
            load_test.name = request.form.get('name')
            load_test.test_case_id = request.form.get('test_case_id')
            load_test.concurrent_users = int(request.form.get('concurrent_users', 10))
            load_test.duration = int(request.form.get('duration', 60))
            load_test.ramp_up_time = int(request.form.get('ramp_up_time', 0))
            load_test.description = request.form.get('description', '')

            # 获取测试用例名称
            test_case = session.query(TestCase).get(load_test.test_case_id)
            if test_case:
                load_test.test_case_name = test_case.name

            # 更新定时配置
            is_scheduled = request.form.get('is_scheduled') == '1'
            schedule_cron = request.form.get('schedule_cron', '').strip()
            load_test.is_scheduled = is_scheduled
            load_test.schedule_cron = schedule_cron if is_scheduled else None

            session.commit()

            # 如果启用了定时，注册定时任务
            if is_scheduled and schedule_cron:
                register_scheduled_load_test(load_test.id, schedule_cron)

            return redirect(url_for('main.load_tests'))

        # GET请求，显示编辑表单
        test_cases = session.query(TestCase).filter_by(is_example=False).all()
        return render_template('edit_load_test.html', load_test=load_test, test_cases=test_cases)
    finally:
        session.close()


@bp.route('/load-tests/<int:test_id>/run', methods=['POST'])
def run_load_test(test_id):
    """执行压测任务"""
    session = get_session()
    try:
        # 获取压测任务
        load_test = session.query(LoadTest).get(test_id)
        if not load_test:
            return jsonify({'success': False, 'error': '压测任务不存在'}), 404

        # 获取测试用例
        test_case = session.query(TestCase).get(load_test.test_case_id)
        if not test_case:
            return jsonify({'success': False, 'error': '测试用例不存在'}), 404

        # 导入并执行压测引擎
        from app.load_test_engine import LoadTestEngine

        try:
            engine = LoadTestEngine(load_test, test_case)
            result = engine.run()

            return jsonify({
                'success': True,
                'result_id': result.id,
                'message': '压测执行成功'
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'压测执行失败: {str(e)}'
            }), 500

    finally:
        session.close()


@bp.route('/load-tests/<int:test_id>/results')
def load_test_results(test_id):
    """查看压测任务的所有结果"""
    session = get_session()
    try:
        load_test = session.query(LoadTest).get(test_id)
        if not load_test:
            return redirect(url_for('main.load_tests'))

        # 获取该任务的所有结果
        results = session.query(LoadTestResult).filter_by(
            load_test_id=test_id
        ).order_by(LoadTestResult.executed_at.desc()).all()

        return render_template('load_test_results.html',
                               load_test=load_test,
                               results=results)
    finally:
        session.close()


@bp.route('/load-tests/results/<int:result_id>')
def load_test_result_detail(result_id):
    """查看单个压测结果详情"""
    session = get_session()
    try:
        result = session.query(LoadTestResult).get(result_id)
        if not result:
            return redirect(url_for('main.load_tests'))

        return render_template('load_test_result_detail.html', result=result)
    finally:
        session.close()


@bp.route('/load-tests/results/<int:result_id>/export/excel')
def export_load_test_excel(result_id):
    """导出压测结果为Excel"""
    session = get_session()
    try:
        result = session.query(LoadTestResult).get(result_id)
        if not result:
            return "结果不存在", 404

        # 导入Excel导出器
        from app.excel_exporter import ExcelReportExporter
        import tempfile
        import os
        from flask import send_file

        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        filename = f"load_test_report_{result_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(temp_dir, filename)

        # 导出Excel
        exporter = ExcelReportExporter(result)
        if exporter.export(filepath):
            return send_file(
                filepath,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            return "导出失败", 500

    finally:
        session.close()


@bp.route('/load-tests/<int:test_id>/compare', methods=['GET', 'POST'])
def compare_load_test_results(test_id):
    """对比压测结果"""
    session = get_session()
    try:
        load_test = session.query(LoadTest).get(test_id)
        if not load_test:
            return redirect(url_for('main.load_tests'))

        if request.method == 'POST':
            # 获取选中的结果ID
            result_ids = request.form.getlist('result_ids')
            if len(result_ids) < 2:
                return "至少选择2个结果进行对比", 400

            # 获取结果数据
            results = session.query(LoadTestResult).filter(
                LoadTestResult.id.in_(result_ids)
            ).order_by(LoadTestResult.executed_at).all()

            return render_template('load_test_compare_result.html',
                                   load_test=load_test,
                                   results=results)

        # GET请求，显示选择页面
        results = session.query(LoadTestResult).filter_by(
            load_test_id=test_id
        ).order_by(LoadTestResult.executed_at.desc()).limit(20).all()

        return render_template('load_test_compare.html',
                               load_test=load_test,
                               results=results)
    finally:
        session.close()


# ==================== 定时压测辅助函数 ====================

def register_scheduled_load_test(load_test_id, cron_expression):
    """
    注册定时压测任务
    :param load_test_id: 压测任务ID
    :param cron_expression: Cron表达式
    """
    from app import scheduler

    job_id = f'load_test_{load_test_id}'

    # 删除已存在的任务
    try:
        scheduler.remove_job(job_id)
    except:
        pass

    # 解析Cron表达式
    parts = cron_expression.split()
    if len(parts) != 5:
        raise ValueError("Cron表达式格式错误，应为：分 时 日 月 周")

    minute, hour, day, month, day_of_week = parts

    # 添加定时任务
    scheduler.add_job(
        func=execute_scheduled_load_test,
        trigger='cron',
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        id=job_id,
        args=[load_test_id],
        replace_existing=True
    )

    print(f"定时压测任务已注册: {job_id}, Cron: {cron_expression}")


def execute_scheduled_load_test(load_test_id):
    """
    执行定时压测任务
    :param load_test_id: 压测任务ID
    """
    print(f"开始执行定时压测: load_test_id={load_test_id}")

    session = get_session()
    try:
        # 获取压测任务
        load_test = session.query(LoadTest).get(load_test_id)
        if not load_test:
            print(f"压测任务不存在: {load_test_id}")
            return

        # 获取测试用例
        test_case = session.query(TestCase).get(load_test.test_case_id)
        if not test_case:
            print(f"测试用例不存在: {load_test.test_case_id}")
            return

        # 执行压测
        from app.load_test_engine import LoadTestEngine
        engine = LoadTestEngine(load_test, test_case)
        result = engine.run()

        # 标记为定时执行
        result.is_scheduled = True
        session.commit()

        print(f"定时压测执行完成: result_id={result.id}")

    except Exception as e:
        print(f"定时压测执行失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


@bp.route('/load-tests/results/<int:result_id>/print')
def print_load_test_report(result_id):
    """打印/导出PDF页面"""
    session = get_session()
    try:
        result = session.query(LoadTestResult).get(result_id)
        if not result:
            return "结果不存在", 404

        return render_template('load_test_report_print.html', result=result)
    finally:
        session.close()





