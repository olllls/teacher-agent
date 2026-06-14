# 教师期末评语 Agent — 产品需求文档

## 1. 项目概述

| 项目 | 内容 |
|------|------|
| 项目名称 | TeacherEval Agent |
| 目标用户 | 中小学班主任、任课教师 |
| 核心价值 | 将期末评语撰写时间从 2-3 天缩短至 10 分钟 |
| 技术栈 | FastAPI + DeepSeek API + SQLite + Docker + HTML/CSS/JS |

## 2. 用户故事

| ID | 用户故事 | 优先级 |
|----|---------|--------|
| US-01 | 作为班主任，我希望能上传全班学生的 Excel 表格，以便批量生成评语 | P0 |
| US-02 | 作为班主任，我希望系统根据成绩、课堂表现、作业情况自动生成个性化评语，避免千篇一律 | P0 |
| US-03 | 作为班主任，我希望能预览和编辑每条评语，再确定导出 | P0 |
| US-04 | 作为班主任，我希望能导出带评语的 Excel 文件，直接打印或存档 | P0 |
| US-05 | 作为班主任，我希望系统自动检测评语中的敏感词（如负面标签），避免家校纠纷 | P0 |
| US-06 | 作为班主任，我可以在系统提示词中设定自己的评语风格（严厉/温和/鼓励型） | P1 |
| US-07 | 作为班主任，我可以保存本届评语模板，下学期复用时微调 | P1 |
| US-08 | 作为班主任，我希望系统记录历史评语，避免连续两年写一样的评语 | P2（V2） |

## 3. 页面设计

### 3.1 页面架构

```
[导航栏]  首页  |  生成评语  |  历史记录  |  设置
```

### 3.2 页面清单

#### P1-首页（引导页）
- 欢迎语 + 一句话操作引导
- "开始生成评语" 按钮
- 快速使用说明（三步：上传→预览→导出）

#### P2-评语生成页（核心页面）
- **步骤1：上传区域**
  - 拖拽/点击上传 Excel 文件
  - 上传后预览表格前 5 行
  - 字段映射确认（自动检测列名）

- **步骤2：风格设置**
  - 评语风格下拉：鼓励型 / 温和型 / 严厉型 / 自定义
  - 自定义风格输入框（如："我是一个严格的数学老师"）
  - 评语字数范围：50-100 / 100-150 / 150-200

- **步骤3：生成与预览**
  - "开始生成" 按钮
  - 进度条 / 逐条完成动画
  - 生成后表格展示全部学生评语（姓名 + 原始数据 + 评语）
  - 每条评语旁有编辑按钮（行内编辑）
  - 敏感词标红提示（如命中"差生""笨"等）

- **步骤4：导出**
  - 导出 Excel 按钮
  - 导出设置：评语列位置、工作表名称

#### P3-历史记录页
- 按学期/年份筛选
- 列表展示：班级名称、人数、生成时间
- 点击查看详情（只读）

#### P4-设置页
- 默认评语风格
- 敏感词词库管理（添加/删除自定义敏感词）
- DeepSeek API Key 配置
- 系统提示词模板编辑

## 4. 数据库设计

### 4.1 表结构

```sql
-- 班级表
CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,              -- 班级名称，如"三年级一班"
    grade TEXT,                      -- 年级
    semester TEXT NOT NULL,          -- 学期，如"2025-2026-上"
    style TEXT DEFAULT 'encourage',  -- 评语风格
    custom_prompt TEXT,              -- 自定义提示词
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 学生表
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER REFERENCES classes(id),
    name TEXT NOT NULL,
    score REAL,                      -- 成绩
    performance TEXT,                -- 课堂表现
    homework TEXT,                   -- 作业情况
    extra_info TEXT                  -- 其他信息（JSON）
);

-- 评语表
CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES students(id),
    content TEXT NOT NULL,           -- 评语内容
    word_count INTEGER,              -- 字数
    status TEXT DEFAULT 'pending',   -- pending/approved/edited
    sensitive_hit INTEGER DEFAULT 0, -- 敏感词命中数
    raw_response TEXT,               -- AI原始返回
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 敏感词表
CREATE TABLE sensitive_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE,
    severity TEXT DEFAULT 'warning', -- warning/block
    is_system INTEGER DEFAULT 0,     -- 是否系统内置
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 系统配置表
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 5. API 设计

### 5.1 接口列表

```
POST   /api/v1/upload-excel       上传 Excel，解析并返回预览数据
POST   /api/v1/generate           触发生成评语（批量）
GET    /api/v1/generate/{task_id}  查询生成进度与结果
PUT    /api/v1/evaluations/{id}    编辑单条评语
POST   /api/v1/export-excel       导出带评语的 Excel
GET    /api/v1/classes            班级列表
GET    /api/v1/classes/{id}/evaluations  查看某班级全部评语
DELETE /api/v1/classes/{id}       删除班级及关联数据

GET    /api/v1/sensitive-words    获取敏感词列表
POST   /api/v1/sensitive-words    添加敏感词
DELETE /api/v1/sensitive-words/{id} 删除敏感词

GET    /api/v1/config/{key}       获取配置
PUT    /api/v1/config/{key}       更新配置
```

### 5.2 关键接口详情

#### POST /api/v1/generate

请求体：
```json
{
  "class_id": 1,
  "style": "encourage",
  "custom_prompt": "我是一个严格的数学老师",
  "word_count": "100-150"
}
```

返回：
```json
{
  "task_id": "gen-xxxxx",
  "total": 45,
  "status": "processing"
}
```

查询结果 GET /api/v1/generate/{task_id}：
```json
{
  "task_id": "gen-xxxxx",
  "status": "completed",
  "total": 45,
  "completed": 45,
  "results": [
    {
      "student_id": 1,
      "name": "张三",
      "content": "你是一个...",
      "sensitive_hit": 0,
      "sensitive_words": []
    }
  ]
}
```

## 6. Agent 工作流设计

### 6.1 架构图

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Excel   │───→│  Parser  │───→│  Batch   │───→│  Sensi-  │───→  Excel
│  Upload  │    │  Agent   │    │  Eval    │    │  tive    │      Export
│          │    │          │    │  Agent   │    │  Check   │
└──────────┘    └──────────┘    │          │    │  Agent   │
                                │  ┌──────┐│    └──────────┘
                                │  │Deep- ││
                                │  │Seek  ││
                                │  │ API  ││
                                │  └──────┘│
                                └──────────┘
```

### 6.2 各 Agent 职责

| Agent | 输入 | 输出 | 说明 |
|-------|------|------|------|
| Parser Agent | 原始 Excel 字节流 | 结构化学生数据 + 字段映射 | 自动识别列名（姓名/成绩/表现/作业），处理缺失值 |
| Batch Evaluation Agent | 学生数据列表 + 风格配置 | 评语文本列表 | 分批调用 DeepSeek API（每批 5 条），含提示词组装与重试逻辑 |
| Sensitive Check Agent | 评语文本 | 标注后的评语 + 命中词列表 | 正则 + 词库匹配，标红显示 |

### 6.3 Batch Evaluation Agent 核心提示词模板

```text
你是一位有{X}年教龄的班主任，风格是{style}。
请为以下学生撰写期末评语，字数在{min}-{max}字之间。

学生信息：
- 姓名：{name}
- 期末成绩：{score}
- 课堂表现：{performance}
- 作业情况：{homework}

要求：
1. 先肯定优点，再委婉指出不足
2. 用具体事例支持评价（可从表现/作业中提取）
3. 提出下学期可操作的改进建议
4. 语言温暖，禁止出现以下词汇：{sensitive_words}
5. 每个学生独立成段，不要出现"你"以外的称呼
```

## 7. MVP 范围

### 包含

| 模块 | 具体内容 |
|------|---------|
| 上传解析 | 支持 .xlsx/.xls 上传，自动列映射，数据预览 |
| AI 生成 | 调用 DeepSeek API 批量生成，进度反馈，重试机制 |
| 预览编辑 | 表格展示全部评语，行内编辑，敏感词标红 |
| 导出 | 导出为 .xlsx，保留原始列 + 评语列 |
| 敏感词检测 | 内置 50+ 教育敏感词库，自动标注 |
| 配置 | 评语风格选择、API Key 配置、自定义提示词 |

### 不包含（MVP）

- 用户登录/权限系统（单机版）
- 历史评语查重
- 批量导出 PDF
- 短信/微信通知

### MVP 目录结构

```
teacher-agent/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── agent/
│   │   ├── parser.py        # Excel 解析 Agent
│   │   ├── evaluator.py     # 评语生成 Agent
│   │   └── sensitive.py     # 敏感词检测 Agent
│   ├── models.py            # SQLAlchemy 模型
│   ├── schemas.py           # Pydantic 模型
│   ├── database.py          # 数据库连接
│   ├── config.py            # 配置管理
│   └── requirements.txt
├── frontend/
│   └── static/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── docker-compose.yml
├── Dockerfile
└── docs/
    └── PRD.md
```

## 8. V2 — RAG 增强（历史评语避免重复）

### 改进点

```
┌─────────────────────────────────────────────┐
│  V2: RAG Knowledge Layer                     │
│                                              │
│  ┌──────────┐     ┌──────────────────┐       │
│  │ 历史评语  │────→│  Embedding →     │       │
│  │ 数据库    │     │  Vector Store    │       │
│  └──────────┘     └────────┬─────────┘       │
│                            │                  │
│  ┌──────────┐              │  ┌──────────┐    │
│  │ 当前学生  │──────────────┼─→│  Prompt  │    │
│  │ 数据     │              │  │  Assembly│    │
│  └──────────┘              │  └──────────┘    │
│                             ↓                  │
│                       ┌──────────┐             │
│                       │ DeepSeek │             │
│                       │ API      │             │
│                       └──────────┘             │
└─────────────────────────────────────────────┘
```

### V2 新增功能

| 功能 | 说明 |
|------|------|
| 向量存储 | 使用 sentence-transformers 将历史评语转为向量，存入 SQLite + sqlite-vec |
| 相似评语检索 | 生成前检索该学生上年评语，作为上下文注入提示词，附加指令"不要与去年雷同" |
| 同班去重 | 生成后计算全班评语的 cosine similarity，标记相似度 > 0.85 的对，提示教师修改 |
| 班级评语画像 | 统计全班评语的情感倾向分布、高频词云，辅助教师发现"评价盲区" |

### V2 新增依赖

```txt
sentence-transformers
sqlite-vec
scikit-learn
jieba
```

## 9. V3 — 多 Agent 协作

### V3 架构

```
                            ┌──────────────────┐
                            │  Orchestrator     │
                            │  Agent            │
                            └──┬───┬───┬───┬───┘
                               │   │   │   │
                    ┌──────────┘   │   │   └──────────┐
                    ▼              ▼   ▼              ▼
             ┌──────────┐  ┌──────────┐  ┌──────────┐
             │ Data     │  │ Eval     │  │ Quality  │
             │ Agent    │  │ Agent    │  │ Agent    │
             └──────────┘  └──────────┘  └──────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌──────────┐  ┌──────────┐  ┌──────────┐
             │ Academic │  │ Character│  │ Growth   │
             │ Agent    │  │ Agent    │  │ Agent    │
             └──────────┘  └──────────┘  └──────────┘
```

### 各 Agent 职责

| Agent | 职责 | 调用模型 |
|-------|------|---------|
| **Orchestrator Agent** | 接收用户请求，拆解任务，协调各 Agent 执行，汇总结果 | DeepSeek Chat |
| **Data Agent** | 解析 Excel，数据清洗，异常值检测（如成绩缺失），输出结构化 JSON | 规则引擎 |
| **Eval Agent（母）** | 拆分评语撰写维度，分配给子 Agent，合并结果 | DeepSeek Chat |
| ├ Academic Agent | 基于成绩与作业数据，撰写学业维度评语 | DeepSeek Chat |
| ├ Character Agent | 基于课堂表现，撰写品德/性格维度评语 | DeepSeek Chat |
| └ Growth Agent | 分析学期进步/退步趋势，撰写成长建议 | DeepSeek Chat |
| **Quality Agent** | 检查评语质量：字数、敏感词、重复度、情感一致性，返工不合格项 | DeepSeek Chat + 规则 |

### V3 工作流示例

```
用户上传 Excel → Orchestrator 启动
  → Data Agent 解析 & 校验
  → Eval Agent 收到 45 名学生数据
    → 拆为 3 个子任务，每个 15 人
    → 每个子任务并行调用 Academic / Character / Growth Agent
    → 合并子评语为完整评语
  → Quality Agent 逐条质检
    → 发现 3 条敏感词命中 → 标记并重新生成
    → 发现 2 条与其他评语重复度 > 85% → 重新生成
  → Orchestrator 汇总最终结果 → 返回前端
```

### V3 新增功能

| 功能 | 说明 |
|------|------|
| 多维度评语 | 学业 + 品德 + 成长三视角，避免单一维度评价 |
| 自动质检与返工 | Quality Agent 自动检测质量问题并触发重生成，无需人工干预 |
| 并行生成 | 子 Agent 并行调用 API，45 人评语总耗时 < 3 分钟 |
| 运行时可视化 | 前端展示各 Agent 实时状态（类似 AutoGen Studio 的 DAG 图） |
| 人工审核节点 | 每个关键步骤支持"人工确认后再继续"模式 |

---

## 附录：内置敏感词示例（50+）

```
差生、笨、智商低、脑子不好、无可救药、没救了、太差了、
倒数、拖后腿、问题学生、坏学生、不听话、捣蛋鬼、讨厌、
懒得管你、随便你、放弃、没出息、真笨、蠢、傻瓜、废物、
不认真、态度差、懒惰、消极、对抗、恶习、屡教不改、朽木、
教不会、听不懂人话、跟你说了多少遍、无可奉告、不求上进
```

*系统内置敏感词库按"warning"（建议修改）和"block"（强制拦截）两级分类。*
