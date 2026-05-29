# KeyRouter - 开发需求文档

## 项目概述
类似 Sub2API / CLIProxyAPI 的轻量级 API Key 智能路由代理。

核心价值：对于一个 baseURL，如果有多个 API Key，能对多个 Key 进行轮询，找到能用的 Key。

## 核心功能需求

### 1. 渠道管理 (Channel)
- 每个渠道 = 一个 baseURL + 其下的多个 Key
- 支持自定义 baseURL（如 OpenAI、Claude、自定义中转站）
- 渠道字段：name, base_url, strategy(round_robin/weighted/random), enabled, weight

### 2. Key 管理
- 每个 Key 属于一个渠道
- Key 字段：value, channel_id, status(active/disabled/expired/banned), weight, last_used, last_check, error_count, quota_remaining
- 支持批量添加 Key（文本框粘贴多个 key，逗号/换行分隔）

### 3. Key 健康检测
- 定期检测 Key 是否可用（发一个简单请求到 base_url 检查）
- 检测逻辑：
  - 401/403 → 标记为 disabled/banned
  - 429 → 标记为 rate_limited（临时跳过，一段时间后重试）
  - 402/quota exceeded → 标记为 expired
  - 成功 → 标记为 active
- 失效 Key 自动从轮询池中移除
- 定时自动检测（可配置间隔，如每 5 分钟）

### 4. 智能路由 (Request Proxy)
- 对外暴露 OpenAI 兼容 API 端点：
  - `/v1/chat/completions`
  - `/v1/completions`
  - `/v1/models`
- 请求进来后：
  - 根据请求中的 model 字段匹配对应渠道
  - 从该渠道的可用 Key 池中按策略选取一个 Key
  - 将请求转发到该渠道的 base_url，header 中用选中的 Key 替换
  - 支持流式响应 (streaming)
  - 请求失败时自动切换下一个 Key 重试（最多 N 次）

### 5. 轮询策略
- Round-Robin：轮流使用每个可用 Key
- Weighted：按权重分配（Key 可以设置权重）
- Random：随机选择
- Least-Used：优先使用使用次数最少的 Key

### 6. 请求日志
- 记录每个请求：时间、渠道、Key、model、token用量、响应时间、是否成功
- Key 使用统计：每个 Key 的请求次数、成功率、平均响应时间

### 7. 管理 UI（Gemini 设计）
- 渠道列表页：显示所有渠道、状态、Key数量
- 渠道详情页：显示渠道下的所有 Key、状态、使用统计
- Key 批量添加：文本框粘贴，支持逗号/换行分隔
- Dashboard：请求统计、Key 健康概览、错误率
- 设置页：代理配置、检测间隔、重试次数
- UI 风格：现代简洁，TailwindCSS，由 Gemini 协助设计

## 技术栈
- 后端：Python 3.10+ + FastAPI + SQLAlchemy + SQLite
- 前端：Vue 3 + Vite + TailwindCSS + Pinia
- 无需 Redis/PostgreSQL，单文件 SQLite 足够

## 项目结构
```
KeyRouter/
├── backend/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置
│   ├── models.py        # SQLAlchemy 模型
│   ├── database.py      # 数据库初始化
│   ├── router.py        # 请求代理路由
│   ├── key_manager.py   # Key 选取与健康检测
│   ├── channel_manager.py # 渠道管理
│   ├── health_check.py  # Key 健康检测定时任务
│   ├── admin_api.py     # 管理 API 端点
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── views/       # 页面
│   │   ├── components/  # 组件
│   │   ├── stores/      # Pinia stores
│   │   ├── api/         # API 调用
│   │   └── assets/
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── README.md
├── SPEC.md
└── .gitignore
```

## GitHub 仓库
https://github.com/ddddx/KeyRouter