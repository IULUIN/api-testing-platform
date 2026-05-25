"""
定时任务调度器
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app.models import ScheduledTask, TestCase, TestResult, get_session
from app.api_tester import APITester
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建调度器实例
scheduler = BackgroundScheduler()


def execute_scheduled_test(task_id):
    """执行定时测试任务"""
    session = get_session()
    try:
        # 获取任务信息
        task = session.query(ScheduledTask).filter_by(id=task_id).first()
        if not task or not task.is_active:
            logger.warning(f"任务 {task_id} 不存在或已禁用")
            return

        # 获取测试用例
        test_case = session.query(TestCase).filter_by(id=task.test_case_id).first()
        if not test_case:
            logger.error(f"测试用例 {task.test_case_id} 不存在")
            return

        logger.info(f"开始执行定时任务: {task.test_case_name}")

        # 执行测试
        tester = APITester()
        result = tester.run_test(test_case)

        # 保存测试结果
        test_result = TestResult(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            status=result['status'],
            actual_status=result.get('actual_status'),
            response_time=result.get('response_time'),
            response_body=result.get('response_body'),
            error_message=result.get('error_message'),
            assertion_results=result.get('assertion_results')
        )
        session.add(test_result)

        # 更新任务的最后执行时间
        task.last_run_at = datetime.now()
        session.commit()

        logger.info(f"定时任务执行完成: {task.test_case_name}, 状态: {result['status']}")

    except Exception as e:
        logger.error(f"执行定时任务失败: {str(e)}")
        session.rollback()
    finally:
        session.close()


def add_scheduled_task(task_id, test_case_id, test_case_name, cron_expression):
    """添加定时任务到调度器"""
    try:
        # 解析cron表达式
        trigger = CronTrigger.from_crontab(cron_expression)

        # 添加任务到调度器
        job_id = f"task_{task_id}"
        scheduler.add_job(
            func=execute_scheduled_test,
            trigger=trigger,
            args=[task_id],
            id=job_id,
            name=test_case_name,
            replace_existing=True
        )

        logger.info(f"添加定时任务成功: {test_case_name} ({cron_expression})")
        return True
    except Exception as e:
        logger.error(f"添加定时任务失败: {str(e)}")
        return False


def remove_scheduled_task(task_id):
    """从调度器中移除定时任务"""
    try:
        job_id = f"task_{task_id}"
        scheduler.remove_job(job_id)
        logger.info(f"移除定时任务成功: {job_id}")
        return True
    except Exception as e:
        logger.error(f"移除定时任务失败: {str(e)}")
        return False


def pause_scheduled_task(task_id):
    """暂停定时任务"""
    try:
        job_id = f"task_{task_id}"
        scheduler.pause_job(job_id)
        logger.info(f"暂停定时任务成功: {job_id}")
        return True
    except Exception as e:
        logger.error(f"暂停定时任务失败: {str(e)}")
        return False


def resume_scheduled_task(task_id):
    """恢复定时任务"""
    try:
        job_id = f"task_{task_id}"
        scheduler.resume_job(job_id)
        logger.info(f"恢复定时任务成功: {job_id}")
        return True
    except Exception as e:
        logger.error(f"恢复定时任务失败: {str(e)}")
        return False


def get_next_run_time(cron_expression):
    """获取下次执行时间"""
    try:
        trigger = CronTrigger.from_crontab(cron_expression)
        next_time = trigger.get_next_fire_time(None, datetime.now())
        return next_time
    except Exception as e:
        logger.error(f"计算下次执行时间失败: {str(e)}")
        return None


def init_scheduler():
    """初始化调度器，加载所有活动的定时任务"""
    session = get_session()
    try:
        # 获取所有活动的定时任务
        tasks = session.query(ScheduledTask).filter_by(is_active=True).all()

        for task in tasks:
            # 计算下次执行时间
            next_run = get_next_run_time(task.cron_expression)
            if next_run:
                task.next_run_at = next_run
                # 添加到调度器
                add_scheduled_task(
                    task.id,
                    task.test_case_id,
                    task.test_case_name,
                    task.cron_expression
                )

        session.commit()
        logger.info(f"初始化调度器成功，加载了 {len(tasks)} 个定时任务")
    except Exception as e:
        logger.error(f"初始化调度器失败: {str(e)}")
        session.rollback()
    finally:
        session.close()


def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
        scheduler.start()
        logger.info("调度器已启动")


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("调度器已关闭")

