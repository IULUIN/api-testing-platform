"""
用户认证路由
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from app.models import get_session, User

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('auth/login.html')

        db_session = get_session()
        try:
            user = db_session.query(User).filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.index'))
            else:
                flash('用户名或密码错误', 'error')
        finally:
            db_session.close()

    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('已成功登出', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('密码长度不能少于6位', 'error')
            return render_template('auth/register.html')

        db_session = get_session()
        try:
            existing_user = db_session.query(User).filter_by(username=username).first()
            if existing_user:
                flash('用户名已存在', 'error')
                return render_template('auth/register.html')

            new_user = User(username=username, role='user')
            new_user.set_password(password)
            db_session.add(new_user)
            db_session.commit()

            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db_session.rollback()
            flash(f'注册失败: {str(e)}', 'error')
        finally:
            db_session.close()

    return render_template('auth/register.html')
