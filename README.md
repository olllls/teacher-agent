# TeacherEval Agent

中小学教师期末评语自动生成工具。

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **AI**: DeepSeek API
- **前端**: Jinja2 模板 + Vanilla JS
- **部署**: Docker

## 快速开始

### 环境变量

```bash
export DEEPSEEK_API_KEY=your_api_key_here
```

### Docker 运行

```bash
docker compose up -d
```

访问 http://localhost:8000

### 本地开发

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

## 使用流程

1. 上传学生 Excel（字段：姓名、成绩、课堂表现、作业情况）
2. 选择评语风格
3. 一键生成个性化评语
4. 预览编辑
5. 导出带评语的 Excel

## 项目结构

```
teacher-agent/
├── backend/
│   ├── main.py           # FastAPI 入口
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── models.py         # 数据模型
│   ├── schemas.py        # Pydantic 模式
│   ├── router/           # API 路由
│   └── agent/            # Agent 业务逻辑
├── frontend/
│   ├── templates/        # Jinja2 模板
│   └── static/           # 静态资源
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
