# KeyRouter 🔑

**API Key 智能路由代理** — OpenAI 兼容的多渠道 API Key 管理与智能路由系统。

## 功能特性

- **多渠道管理** — 支持多个 API 渠道（如 OpenAI 官方、Azure OpenAI、第三方转发等）
- **智能路由** — 四种策略：Round Robin、加权随机、随机、最少使用
- **Key 健康检测** — 自动定时检测 Key 有效性，标记失效 Key
- **429 自动冷却** — 上游 Key 触发限速后进入冷却，到期自动恢复可用
- **自动重试** — 请求失败自动切换 Key 重试，支持最多 3 次重试
- **Streaming 支持** — 完整支持 SSE 流式转发（chat/completions stream）
- **OpenAI 兼容** — 兼容 `/v1/chat/completions`、`/v1/completions`、`/v1/models`
- **完整日志记录** — 每个请求完整记录（时间、渠道、Key脱敏、model、tokens、响应时间ms、状态码、成功/失败、错误信息、来源IP）
- **丰富的统计** — 全局/渠道/Key/Model 四级统计，成功率、平均响应时间、token用量
- **趋势图表** — 每小时/每天请求量趋势，成功/失败对比
- **CSV 导出** — 支持按条件筛选导出请求日志 CSV
- **日志自动清理** — 可配置保留天数，自动清理过期日志
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
    api_key=***  # KeyRouter 会自动选择可用的 key
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
| `KEYROUTER_KEY_COOLDOWN_SECONDS` | 上游 Key 遇到 429 后的默认冷却秒数，后台设置页可覆盖 | 900 |
| `KEYROUTER_PROXY_URL` | 出站请求代理 | 无 |
| `KEYROUTER_LOG_RETENTION_DAYS` | 日志保留天数（自动清理） | 30 |

## 请求日志与统计

### 请求日志（完整记录）
每个请求记录：
- **时间戳** — 精确到秒
- **渠道名** — 请求使用的渠道
- **Key（脱敏）** — 前8位 + ***（如 `sk-abc12***`）
- **Model** — 请求的模型名
- **Tokens** — prompt_tokens + completion_tokens + total_tokens
- **响应时间(ms)** — 毫秒级精确记录
- **HTTP状态码** — 上游返回的状态码
- **是否成功** — is_success 标记
- **错误信息** — 失败时记录具体错误
- **来源IP** — 请求客户端IP（支持 x-forwarded-for）

### Key 使用统计
每个 Key 统计：
- 总请求次数、成功次数、失败次数、成功率
- 平均响应时间(ms)
- 累计 token 用量（prompt + completion）
- 最近一次使用时间

### 渠道统计
每个渠道统计：
- 总请求量、成功/失败数、成功率
- 可用 Key 数 vs 总 Key 数 vs 错误 Key 数
- 平均响应时间、累计 token 用量
- 每个渠道下所有 Key 的详细统计表格

### 全局统计
- 总请求量、成功率、平均响应时间
- 按 Model 分类的使用统计（请求量、成功率、token用量）
- 每小时/每天请求量趋势图表

### CSV 导出
支持按渠道/Model/状态/时间范围筛选后导出 CSV 文件。

### 日志保留策略
默认保留 30 天，通过 `KEYROUTER_LOG_RETENTION_DAYS` 配置。后台每天自动清理过期日志。

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
- `GET /api/keys/` — Key 列表（含脱敏、统计）
- `POST /api/keys/` — 创建 Key
- `POST /api/keys/batch` — 批量添加 Key
- `PUT /api/keys/{id}` — 更新 Key
- `DELETE /api/keys/{id}` — 删除 Key
- `GET /api/admin/stats/dashboard` — Dashboard 统计（含趋势、Model统计）
- `GET /api/admin/stats/channel/{id}` — 渠道统计（含 Key 统计表格）
- `GET /api/admin/stats/key/{id}` — Key 统计
- `GET /api/admin/logs` — 请求日志（支持多种筛选）
- `GET /api/admin/logs/export/csv` — CSV 导出
- `GET /api/admin/config` — 配置信息

## 项目结构

```
KeyRouter/
├── backend/
│   ├── main.py            # FastAPI 入口，serve 前端 + 挂载路由 + 启动后台任务
│   ├── config.py          # 配置管理（含日志保留天数）
│   ├── database.py        # SQLite + SQLAlchemy async 初始化
│   ├── models.py          # 数据模型（Channel, Key含token统计, RequestLog含IP/ms/is_success）
│   ├── channel_manager.py # 渠道 CRUD API
│   ├── key_manager.py     # Key CRUD、批量添加、选择算法、脱敏显示
│   ├── health_check.py    # Key 健康检测
│   ├── router.py          # OpenAI 兼容代理 + streaming + IP提取
│   ├── admin_api.py       # 管理端点（四级统计、趋势、CSV导出、日志筛选）
│   ├── log_cleanup.py     # 日志自动清理后台任务
│   ├── requirements.txt   # Python 依赖
│   └── static/            # 前端打包产物
├── frontend/
│   ├── src/
│   │   ├── views/         # 页面（Dashboard含趋势图、Logs含CSV导出、ChannelDetail含统计）
│   │   ├── api.js         # API 调用封装
│   │   ├── App.vue        # 主布局（侧边栏导航）
│   │   └── main.js        # Vue 3 入口 + Router
│   └── vite.config.js     # Vite + TailwindCSS 配置
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
xcopy /E /I /Y frontend\dist\* backend\static\
```

## License

MIT
