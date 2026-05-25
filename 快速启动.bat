@echo off
chcp 936 >nul 2>nul
title API自动化测试平台 - 快速启动
cls
echo.
echo   API自动化测试平台 - 快速启动
echo.
echo.

REM 检查Python是否安装
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% 已安装
echo.

REM 检查依赖是否安装
echo [正在安装依赖，首次运行可能需要几分钟...]
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [警告] 依赖安装失败，尝试使用现有环境...
)
echo [OK] 依赖检查完成
echo.

REM 初始化数据库
echo [正在初始化数据库...]
python -c "from app.models import init_db; init_db()"
if %errorlevel% neq 0 (
    echo [错误] 数据库初始化失败
    pause
    exit /b 1
)
echo [OK] 数据库初始化完成
echo.

echo ========================================
echo   API自动化测试平台 - 启动成功！
echo ========================================
echo.
echo   访问地址: http://127.0.0.1:5000
echo.
echo   默认账号: admin / admin123
echo.
echo.
echo   正在启动服务，请勿关闭此窗口...
echo.
echo.

REM 延迟2秒后打开浏览器
ping -n 3 127.0.0.1 >nul 2>&1
start http://127.0.0.1:5000

REM 启动Flask服务（前台运行）
python run.py
