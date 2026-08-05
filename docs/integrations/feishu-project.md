# 飞书项目接入

Jarvis Box 接收飞书项目 webhook，通过飞书项目 OpenAPI 读取工作项及其评论，执行 post-check，再把最终 `comment.md` 发布到对应工作项。API credential 只由 Jarvis Box 服务进程持有，不会传给 runtime agent。

## 配置

| 变量 | 必填 | 用途 |
| --- | --- | --- |
| `FEISHU_PROJECT_WEBHOOK_SECRET` | 是 | 与当前 webhook envelope 的 `header.token` 匹配的共享 token。 |
| `FEISHU_PROJECT_API_BASE_URL` | 否 | OpenAPI base URL；默认 `https://project.feishu.cn`。主要用于私有代理或隔离测试。 |
| `FEISHU_PROJECT_PLUGIN_ID` | 是 | 获取 OpenAPI plugin token 使用的 plugin ID。 |
| `FEISHU_PROJECT_PLUGIN_SECRET` | 是 | 仅供服务端 OpenAPI client 使用的 plugin secret。 |
| `FEISHU_PROJECT_USER_KEY` | 是 | 工作项 API 请求使用的 `X-USER-KEY`。 |
| `FEISHU_PROJECT_ALLOWED_SPACES` | 否 | 逗号分隔的 project key；为空时允许全部 project。 |

前四项构成一个完整配置组。只要其中任意一项非空，`jarvis-box serve` 就要求四项全部存在，否则拒绝启动。

## Webhook

以下两个 endpoint 等价：

- `https://<jarvis-box-host>/feishu-project-webhook`
- `https://<jarvis-box-host>/webhooks/feishu-project`

当前飞书项目 envelope 使用 `header.event_type`、`header.token` 和 `header.uuid`，工作项 identity 来自 `payload.id`、`payload.project_key` 与 `payload.work_item_type_key`。`WorkitemCreateEvent` 启动 post-check，带 `@jarvis` 的 `WorkitemCommentEvent` 启动 command Run，`WorkitemAbortedEvent`、`WorkitemFinishEvent` 与 `WorkitemDeleteEvent` 终止同一外部工作项下的 Task 并走统一 cleanup。Jarvis Box 用 UUID 原子 claim 保证幂等，并在持久化 payload 或 ledger 前删除 token。

旧的 flat `EventCreate-*` payload 和 `X-Plug-In-Token` header 仅作为兼容入口保留。

## 读写边界

每个通过校验的 create event 按以下边界执行：

1. 通过 `POST /open_api/authen/plugin_token` 获取 plugin token；
2. 把工作项与已有评论读取到私有 Run Artifact；
3. 在不携带飞书 credential 的情况下启动 runtime agent；
4. 校验 agent 生成的 `comment.md`，再由服务端 OpenAPI client 创建工作项评论；
5. 把 API 响应或可重试失败写入 Run Artifact 和工作账本。

该集成不会启动 MCP 或 Node.js 子进程。Runtime agent 不应直接调用飞书项目，也不应自行声明写回成功。
