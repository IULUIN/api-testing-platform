"""
Flask应用初始化 - 简化版，避免循环依赖
"""
from flask import Flask
from flask_login import LoginManager
import config
import os
import atexit
import json
from datetime import datetime
from app.models import db, init_db, get_session, Base as _Base, User, bcrypt

login_manager = LoginManager()

def create_app():
    """创建Flask应用"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'templates')

    app = Flask(__name__, template_folder=template_dir)

    # 加载配置
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.DEBUG
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME

    # 初始化数据库
    init_db()

    # 初始化SQLAlchemy - 直接使用engine和session
    from app.models import engine, Base, User, bcrypt, get_session
    # 创建会话
    session = get_session()
    # 绑定到app（通过models.db）
    import app.models as models
    models.db = session

    # 初始化Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'

    @login_manager.user_loader
    def load_user(user_id):
        session = get_session()
        return session.query(User).get(int(user_id))

    # 自定义Jinja2过滤器
    @app.template_filter('fromjson')
    def fromjson_filter(s):
        try:
            return json.loads(s) if s else {}
        except Exception:
            return {}

    # 注册路由
    from app import views, auth, models
    app.register_blueprint(views.bp)
    app.register_blueprint(auth.bp, url_prefix='/auth')

    # 初始化并启动定时任务调度器
    from app import scheduler
    scheduler.init_scheduler()
    scheduler.start_scheduler()

    # 注册应用关闭时的清理函数
    atexit.register(lambda: scheduler.shutdown_scheduler())

    # 确保所有表已创建，并创建默认管理员账户
    session = get_session()
    try:
        if not session.query(User).filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            session.add(admin)
            session.commit()
            print("[OK] 已创建默认管理员账户: admin / admin123")
    except Exception as e:
        session.rollback()
        print(f"[警告] 创建管理员账户时出错: {e}")
    finally:
        session.close()

    return app
