# API 自动化测试平台

一款基于 Flask 框架开发的轻量级接口测试工具，为开发和测试团队提供一站式 API 测试解决方案。

## 功能特性

| 功能 | 说明 |
|------|------|
| 测试用例管理 | 创建、编辑、删除和执行接口测试用例 |
| 批量测试 | 支持 CSV 数据导入，实现数据驱动的批量测试 |
| 场景编排 | 多接口串联测试，支持变量传递和依赖管理 |
| 压力测试 | 内置并发压测引擎，生成 TPS、响应时间等性能指标 |
| 智能断言 | 状态码、响应时间、JSONPath 等多种断言方式 |
| 定时调度 | 基于 Cron 表达式的定时任务，支持接口定期巡检 |
| 测试报告 | 自动生成测试报告，支持 Excel 导出和数据可视化 |
| Mock 服务 | 内置 Mock 服务器，模拟接口响应 |
| 用户认证 | 登录/注册功能，支持多用户协作 |

## 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装

```bash
# 克隆项目
git clone https://github.com/IULUIN/api-testing-platform.git
cd api-testing-platform

# 安装依赖
pip install -r requirements.txt
```

### 启动

**Windows 用户：**

双击 `start.bat` 或 `quick-start.bat` 即可启动。

**命令行启动：**

```bash
python run.py
```

访问 http://127.0.0.1:5000

### 默认账号

- 用户名：`admin`
- 密码：`admin123`

## 项目结构

```
api-testing-platform/
├── app/                        # 应用代码
│   ├── __init__.py            # 应用初始化
│   ├── models.py              # 数据模型
│   ├── views.py               # 路由视图
│   ├── auth.py                # 用户认证
│   ├── api_tester.py          # API 测试引擎
│   ├── batch_tester.py        # 批量测试
│   ├── scenario_runner.py     # 场景执行器
│   ├── load_test_engine.py    # 压测引擎
│   ├── smart_assertion.py     # 智能断言
│   ├── scheduler.py           # 定时任务
│   └── utils.py               # 工具函数
├── templates/                  # HTML 模板
├── sample_datasets/            # 示例数据集
├── config.py                   # 配置文件
├── run.py                      # 启动入口
├── init_db.py                  # 数据库初始化
├── start.bat                   # Windows 启动脚本
├── quick-start.bat             # Windows 快速启动脚本
└── requirements.txt            # 依赖清单
```

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | Flask 3.0 |
| 数据库 | SQLite / PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| 用户认证 | Flask-Login |
| 定时任务 | APScheduler |
| 数据可视化 | PyEcharts |
| 数据处理 | Pandas / NumPy |

## 配置说明

编辑 `config.py` 修改配置：

```python
# 数据库配置（默认 SQLite）
DATABASE_URI = 'sqlite:///database.db'

# PostgreSQL 示例
# DATABASE_URI = 'postgresql+psycopg2://user:password@localhost:5432/dbname'

# 安全配置
SECRET_KEY = 'your-secret-key-here'
```

## 使用 Docker

```bash
# 构建镜像
docker build -t api-testing-platform .

# 运行容器
docker run -p 5000:5000 api-testing-platform
```

或使用 docker-compose：

```bash
docker-compose up -d
```

## 使用场景

### API 健康检查
每 5 分钟自动检查核心 API
```
功能：定时任务
Cron：*/5 * * * *
```

### 每日回归测试
每天凌晨 2 点执行全量测试
```
功能：定时任务 + 参数化测试
Cron：0 2 * * *
```

### 性能压测
模拟高并发场景，评估接口性能
```
功能：并发压测
支持：TPS、P50/P90/P95/P99、错误率
```

## 常见问题

**Q: 端口被占用？**
A: 修改 `run.py` 中的 `port` 参数，或关闭占用 5000 端口的程序。

**Q: 数据库错误？**
A: 删除 `database.db` 文件，重新启动应用会自动重建。

**Q: 依赖安装失败？**
A: 尝试使用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

## 贡献

欢迎提交 Issue 和 Pull Request。

## 许可证

MIT License
