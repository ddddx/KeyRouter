# KeyRouter 🔑

**API Key 智能路由代理** — OpenAI 兼容的多渠道 API Key 管理与智能路由系统。

## 功能特性

- **多渠道管理** — 支持多个 API 渠道（如 OpenAI 官方、Azure OpenAI、第三方转发等）
- **智能路由** — 四种策略：Round Robin、加权随机、随机、最少使用
- **Key 健康检测** — 自动定时检测 Key 有效性，标记失效 Key
- **自动重试** — 请求失败自动切换 Key 重试，支持最多 3 次重试
- **Streaming 支持** — 完整支持 SSE 流式转发（chat/completions stream）
- **OpenAI 兼容** — 兼容 `/v1/chat/completions`、`/v1/completions`、`/v1/models`
- **Web 管理面板** — Vue 3 + TailwindCSS 深色主题，渠道管理、Key 管理、请求日志
- **一键启动** — `python main.py` 启动后端 + 前端，单端口 8000

## 快速开始

### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 启动服务

```bash
cd backend
python main.py
```

服务启动后访问：
- 管理面板：http://localhost:8000
- API 代理：http://localhost:8000/v1/chat/completions

### 使用代理

将你的 OpenAI 客户端的 base_url 改为 `http://localhost:8000/v1`：

```python
import openai

client = openai.OpenAI(
    api_key="any-key",  # KeyRouter 会自动选择可用的 key
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## 环境变量配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `KEYROUTER_PORT` | 服务端口 | 8000 |
| `KEYROUTER_HOST` | 服务地址 | 0.0.0.0 |
| `KEYROUTER_HEALTH_CHECK_INTERVAL` | Key 健康检测间隔（秒） | 300 |
| `KEYROUTER_HEALTH_CHECK_MAX_ERRORS` | 标记为 error 的最大错误数 | 3 |
| `KEYROUTER_MAX_RETRY_COUNT` | 每请求最大重试次数 | 3 |
| `KEYROUTER_PROXY_URL` | 出站请求代理 | 无 |

## 管理面板

### 添加渠道

1. 进入「Channels」页面
2. 点击「Add Channel」
3. 填写名称、Base URL（如 `https://api.openai.com`）、路由策略

### 批量添加 Key

1. 进入渠道详情页
2. 点击「Batch Add Keys」
3. 粘贴 Key，逗号或换行分隔（如 `sk-xxx1,sk-xxx2` 或每行一个）

### 路由策略说明

| 策略 | 说明 |
|------|------|
| `round_robin` | 轮询，按顺序依次使用 |
| `weighted` | 加权，按 Key 权重概率选择 |
| `random` | 随机选择 |
| `least_used` | 选择使用次数最少的 Key |

## 技术架构

- **后端**：Python 3.12 + FastAPI + SQLAlchemy + SQLite + httpx
- **前端**：Vue 3 + Vite + TailwindCSS + Vue Router + Axios
- **数据库**：SQLite 单文件（`keyrouter.db`）
- **流式转发**：httpx AsyncClient + SSE StreamingResponse

## API 端点

### 代理端点（OpenAI 兼容）

- `POST /v1/chat/completions` — Chat completions（支持 stream）
- `POST /v1/completions` — Text completions
- `GET /v1/models` — 模型列表（聚合所有渠道）

### 管理端点

- `GET /api/channels/` — 渠道列表
- `POST /api/channels/` — 创建渠道
- `PUT /api/channels/{id}` — 更新渠道
- `DELETE /api/channels/{id}` — 删除渠道
- `GET /api/keys/` — Key 列表
- `POST /api/keys/` — 创建 Key
- `POST /api/keys/batch` — 批量添加 Key
- `PUT /api/keys/{id}` — 更新 Key
- `DELETE /api/keys/{id}` — 删除 Key
- `GET /api/admin/stats/dashboard` — Dashboard 统计
- `GET /api/admin/stats/channel/{id}` — 渠道统计
- `GET /api/admin/stats/key/{id}` — Key 统计
- `GET /api/admin/logs` — 请求日志
- `GET /api/admin/config` — 配置信息

## 项目结构

```
KeyRouter/
├── backend/
│   ├── main.py          # FastAPI 入口，serve 前端 + 挂载路由
│   ├── config.py        # 配置管理
│   ├── database.py      # SQLite + SQLAlchemy 初始化
│   ├── models.py        # 数据模型（Channel, Key, RequestLog）
│   ├── channel_manager.py # 渠道 CRUD API
│   ├── key_manager.py   # Key CRUD、批量添加、选择算法
│   ├── health_check.py  # Key 健康检测
│   ├── router.py        # OpenAI 兼容代理 + streaming
│   ├── admin_api.py     # 管理端点（统计、日志、配置）
│   ├── requirements.txt # Python 依赖
│   └── static/          # 前端打包产物
├── frontend/
│   ├── src/
│   │   ├── views/       # 页面（Dashboard, Channels, Logs, Settings）
│   │   ├── api.js       # API 调用封装
│   │   ├── App.vue      # 主布局（侧边栏导航）
│   │   └── main.js      # Vue 3 入口 + Router
│   └── vite.config.js   # Vite + TailwindCSS 配置
└── README.md
```

## 开发模式

前端开发（热更新）：

```bash
cd frontend
npm install
npm run dev
```

Vite dev server 会自动代理 `/api` 和 `/v1` 到后端 8000 端口。

重新构建前端：

```bash
cd frontend
npm run build
# 然后复制 dist 到 backend/static
xcopy /E /I /Y frontend\dist\* backend\static\
```

## License

MIT