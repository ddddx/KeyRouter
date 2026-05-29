# KeyRouter - API Key 智能路由代理

> 类似 Sub2API / CLIProxyAPI 的轻量级 API Key 轮询代理，专注于多 Key 智能调度

## 功能

- **自定义 baseURL**：每个 baseURL 对应一个"渠道"，可以独立管理其下的多个 API Key
- **多 Key 轮询**：对一个 baseURL 下的多个 Key 自动轮询（Round-Robin / Weighted / Random）
- **Key 健康检测**：自动检测 Key 是否可用（余额/封禁/过期），跳过失效 Key
- **统一 API 入口**：对外暴露一个 OpenAI 兼容的 API 端点，内部路由到不同的 baseURL + Key
- **Key 管理 UI**：Web 界面管理渠道、Key、查看状态
- **实时监控**：请求日志、Key 使用统计、错误率追踪
- **Gemini 设计的 UI**：前端界面由 Gemini 协助设计，现代简洁风格

## 架构

```
客户端请求 → KeyRouter代理 → 选择可用Key → 转发到baseURL → 返回结果
                ↓
        Key池健康检测
        (自动跳过失效Key)
```

## 技术栈

- **后端**: Python + FastAPI
- **数据库**: SQLite (轻量，单文件)
- **前端**: Vue 3 + Vite + TailwindCSS (Gemini 设计)
- **缓存**: 内存缓存 (无需 Redis)

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py

# 访问管理界面
http://localhost:8000
```

## 配置示例

```json
{
  "channels": [
    {
      "name": "OpenAI",
      "base_url": "https://api.openai.com/v1",
      "keys": [
        "sk-xxx1",
        "sk-xxx2",
        "sk-xxx3"
      ],
      "strategy": "round_robin"
    },
    {
      "name": "Claude",
      "base_url": "https://api.anthropic.com/v1",
      "keys": [
        "sk-ant-xxx1",
        "sk-ant-xxx2"
      ],
      "strategy": "weighted"
    }
  ]
}
```

## API 端点

- `POST /v1/chat/completions` — OpenAI 兼容的聊天接口
- `POST /v1/completions` — OpenAI 兼容的补全接口
- `GET /admin/channels` — 渠道管理
- `POST /admin/channels/{id}/keys` — 添加 Key
- `GET /admin/keys/status` — Key 健康状态

## License

MIT