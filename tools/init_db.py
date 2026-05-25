"""
数据库初始化脚本
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import init_db, get_session, TestCase
from datetime import datetime

def create_sample_data():
    """创建示例数据"""
    session = get_session()
    try:
        # 检查是否已有数据
        count = session.query(TestCase).count()
        if count > 0:
            print("数据库已有数据，跳过示例数据创建")
            return

        # 创建示例测试用例（使用中文说明）
        sample_cases = [
            TestCase(
                name="示例1：查询用户信息（GET请求）",
                url="https://jsonplaceholder.typicode.com/users/{{user_id}}",
                method="GET",
                expected_status=200,
                description="GET请求示例，获取指定用户信息。批量测试时配合「example1_query_user.csv」使用，变量：{{user_id}}"
            ),
            TestCase(
                name="示例2：查询文章列表（GET请求）",
                url="https://jsonplaceholder.typicode.com/posts?userId={{user_id}}",
                method="GET",
                expected_status=200,
                description="GET请求示例，按用户ID查询文章列表。批量测试时配合「example2_query_posts.csv」使用，变量：{{user_id}}"
            ),
            TestCase(
                name="示例3：创建文章（POST请求）",
                url="https://jsonplaceholder.typicode.com/posts",
                method="POST",
                headers='{"Content-Type": "application/json"}',
                body='{"title": "{{title}}", "body": "{{content}}", "userId": {{user_id}}}',
                expected_status=201,
                description="POST请求示例，创建新文章。批量测试时配合「example3_create_post.csv」使用，变量：{{title}}、{{content}}、{{user_id}}"
            )
        ]

        for case in sample_cases:
            session.add(case)

        session.commit()
        print(f"✓ 成功创建 {len(sample_cases)} 个示例测试用例")

    except Exception as e:
        print(f"✗ 创建示例数据失败: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    print("开始初始化数据库...")
    init_db()
    print("\n创建示例数据...")
    create_sample_data()
    print("\n✓ 数据库初始化完成！")
    print("\n现在可以运行: python run.py")
