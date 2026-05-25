"""
数据模型
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from flask_login import UserMixin
from app import config
import bcrypt

Base = declarative_base()

# 创建引擎和会话工厂
engine = create_engine(config.DATABASE_URI)
Session = sessionmaker(bind=engine)

# SQLAlchemy实例（用于relationship）
db = None  # 延迟初始化，在create_app中设置

class TestCase(Base):
    __tablename__ = 'test_cases'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    headers = Column(Text)
    body = Column(Text)
    expected_status = Column(Integer, default=200)
    assertions = Column(Text)
    description = Column(Text)
    is_example = Column(Boolean, default=False)
    is_scheduled = Column(Boolean, default=False)
    schedule_cron = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'url': self.url, 'method': self.method,
            'headers': self.headers, 'body': self.body, 'expected_status': self.expected_status,
            'assertions': self.assertions, 'description': self.description,
            'is_scheduled': self.is_scheduled, 'schedule_cron': self.schedule_cron,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class TestResult(Base):
    __tablename__ = 'test_results'
    id = Column(Integer, primary_key=True)
    test_case_id = Column(Integer, nullable=False)
    test_case_name = Column(String(200))
    status = Column(String(20))
    actual_status = Column(Integer)
    response_time = Column(Float)
    response_body = Column(Text)
    error_message = Column(Text)
    assertion_results = Column(Text)
    batch_id = Column(Integer)
    executed_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id, 'test_case_id': self.test_case_id, 'test_case_name': self.test_case_name,
            'status': self.status, 'actual_status': self.actual_status,
            'response_time': round(self.response_time, 3) if self.response_time else None,
            'response_body': self.response_body, 'error_message': self.error_message,
            'assertion_results': self.assertion_results, 'executed_at': self.executed_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class User(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(128))
    role = Column(String(20), default='user')
    created_at = Column(DateTime, default=datetime.now)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def is_admin(self):
        return self.role == 'admin'

class DataSet(Base):
    __tablename__ = 'data_sets'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    file_name = Column(String(200))
    data_count = Column(Integer, default=0)
    is_example = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class DataRow(Base):
    __tablename__ = 'data_rows'
    id = Column(Integer, primary_key=True)
    data_set_id = Column(Integer, nullable=False)
    row_number = Column(Integer, nullable=False)
    data_json = Column(Text)  # JSON object of key-value pairs
    created_at = Column(DateTime, default=datetime.now)

class BatchTestResult(Base):
    __tablename__ = 'batch_test_results'
    id = Column(Integer, primary_key=True)
    test_case_id = Column(Integer)
    test_case_name = Column(String(200))
    data_set_id = Column(Integer)
    data_set_name = Column(String(200))
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    avg_response_time = Column(Float)
    executed_at = Column(DateTime, default=datetime.now)

class ScheduledTask(Base):
    __tablename__ = 'scheduled_tasks'
    id = Column(Integer, primary_key=True)
    test_case_id = Column(Integer, nullable=False)
    test_case_name = Column(String(200))
    cron_expression = Column(String(100))
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

class Scenario(Base):
    __tablename__ = 'scenarios'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ScenarioStep(Base):
    __tablename__ = 'scenario_steps'
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, nullable=False)
    step_order = Column(Integer, nullable=False)
    test_case_id = Column(Integer, nullable=False)
    test_case_name = Column(String(200))
    variable_extractions = Column(Text)  # JSON: extract variables
    wait_seconds = Column(Integer, default=0)

class ScenarioResult(Base):
    __tablename__ = 'scenario_results'
    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, nullable=False)
    scenario_name = Column(String(200))
    status = Column(String(20))
    total_steps = Column(Integer, default=0)
    success_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    duration = Column(Float)
    executed_at = Column(DateTime, default=datetime.now)

class ScenarioStepResult(Base):
    __tablename__ = 'scenario_step_results'
    id = Column(Integer, primary_key=True)
    scenario_result_id = Column(Integer, nullable=False)
    step_order = Column(Integer, nullable=False)
    test_case_name = Column(String(200))
    status = Column(String(20))
    actual_status = Column(Integer)
    response_time = Column(Float)
    response_body = Column(Text)
    error_message = Column(Text)
    extracted_variables = Column(Text)  # JSON
    executed_at = Column(DateTime, default=datetime.now)

class LoadTest(Base):
    __tablename__ = 'load_tests'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    test_case_id = Column(Integer, nullable=False)
    test_case_name = Column(String(200))
    concurrent_users = Column(Integer, default=10)
    ramp_up_time = Column(Integer, default=0)
    duration = Column(Integer, default=60)
    description = Column(Text)
    is_scheduled = Column(Boolean, default=False)
    schedule_cron = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)

class LoadTestResult(Base):
    __tablename__ = 'load_test_results'
    id = Column(Integer, primary_key=True)
    load_test_id = Column(Integer, nullable=False)
    load_test_name = Column(String(200))
    test_case_name = Column(String(200))
    concurrent_users = Column(Integer, default=10)
    ramp_up_time = Column(Integer, default=0)
    duration = Column(Integer, default=60)
    total_requests = Column(Integer, default=0)
    success_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    avg_response_time = Column(Float)
    min_response_time = Column(Float)
    max_response_time = Column(Float)
    p50_response_time = Column(Float)
    p90_response_time = Column(Float)
    p95_response_time = Column(Float)
    p99_response_time = Column(Float)
    tps = Column(Float)
    error_rate = Column(Float)
    time_series_data = Column(Text)  # JSON
    is_scheduled = Column(Boolean, default=False)
    received_bytes_per_sec = Column(Float)
    sent_bytes_per_sec = Column(Float)
    total_received_bytes = Column(Float)
    total_sent_bytes = Column(Float)
    executed_at = Column(DateTime, default=datetime.now)

class Environment(Base):
    __tablename__ = 'environments'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    base_url = Column(String(500))
    description = Column(Text)
    variables = Column(Text)  # JSON
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

def init_db():
    Base.metadata.create_all(engine)
    print("数据库初始化成功！")

def get_session():
    return Session()
