"""
配置文件 - 支持PostgreSQL和用户认证
"""
import os
from datetime import timedelta

# 基础配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Flask配置
SECRET_KEY = os.environ.get('SECRET_KEY') or 'api-test-platform-secret-key-change-in-production'
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# 数据库配置 - 优先使用环境变量，默认使用SQLite（开发环境）
DATABASE_URI = os.environ.get(
    'DATABASE_URI',
    f'sqlite:///{os.path.join(BASE_DIR, "database.db")}'
)

# PostgreSQL连接字符串格式: postgresql+psycopg2://user:password@host:port/database
# 示例: postgresql+psycopg2://testuser:password@localhost:5432/api_test_platform

# 应用配置
APP_NAME = '智能接口测试平台'
VERSION = '1.0.0'

# Session配置
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

# 测试配置
DEFAULT_TIMEOUT = 30  # 请求超时时间（秒）
MAX_RETRIES = 3       # 最大重试次数
