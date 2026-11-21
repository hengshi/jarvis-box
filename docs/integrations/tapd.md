# TAPD 接入

本页面向接入 TAPD 缺陷、需求和任务的管理员。Jarvis Box 可以把 webhook 映射为统一 work item，执行 post-check 或评论中的 `@jarvis` command，并把 Agent 的 `comment.md` 写回同一个 TAPD 工作项。

鉴权、JSON 校验和可靠落盘成功后，webhook 立即返回 `202 Accepted`。`receipt_id` 只证明受理，不证明 Task 已创建或已完成；恢复规则见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

## 1. 配置身份和允许范围

| 变量 | 是否需要 | 用途 |
| --- | --- | --- |
| `TAPD_WEBHOOK_SECRET` | webhook 必填 | 与 webhook body/header 的 token 匹配。 |
| `TAPD_CMD` | 可选 | Runtime Agent 的 `tapd-cli`，默认 `tapd-cli`。 |
| `TAPD_TOKEN` | 必填，除非有 `TAPD_API_TOKEN` | Agent CLI 的个人令牌。Basic Auth 不能代替它。 |
| `TAPD_API_TOKEN` | 与 Basic Auth 二选一 | 服务端 bearer token。 |
| `TAPD_API_USER` / `TAPD_API_PASSWORD` | 与 API token 二选一 | 服务端 Basic Auth。 |
| `TAPD_ALLOWED_WORKSPACES` | 可选 | 逗号分隔 workspace ID；留空允许所有。 |
| `TAPD_API_BASE_URL` / `TAPD_BASE_URL` | 可选 | 默认分别为 `https://api.tapd.cn`、`https://www.tapd.cn`。 |
| `JARVIS_TAPD_COMMAND_ALLOWED_USERS` | 可选 | command 作者 allowlist；留空允许非 bot 用户。 |
| `JARVIS_WORK_ITEM_REPOSITORIES` | 可选 | 关联 GitLab/GitHub workspace 的 JSON。 |

例如：

```dotenv
TAPD_WEBHOOK_SECRET=<random-secret>
TAPD_API_USER=<tapd-api-user>
TAPD_API_PASSWORD=<tapd-api-password>
TAPD_TOKEN=<tapd-personal-token>
TAPD_ALLOWED_WORKSPACES=12345678
JARVIS_TAPD_COMMAND_ALLOWED_USERS=
```

启用 webhook 必须同时具备服务端 API 身份与 CLI 可用令牌。仅配置 Basic Auth 会在启动或保存时被拒绝。服务地址只能是没有用户名、密码、query 或 fragment 的 HTTP(S) 地址。

## 2. 创建 webhook

在 TAPD 中配置：

- `https://<jarvis-box-host>/webhooks/tapd`
- 兼容：`https://<jarvis-box-host>/tapd-webhook`

Jarvis Box 接受 body 中的 `secret`、`token`、`header.token`，以及 `X-TAPD-Token`、`X-Webhook-Token`。持久化前会删除 body 的 `secret`、`token`、`sign`、`signature` 字段。

TAPD 的 URL 连通性测试可能发送仅有 `test` 的 JSON 或空数组 `[]`。这两种请求在没有 event/auth header 时返回 `200`，但不会创建 Task；真实事件仍必须带匹配 `TAPD_WEBHOOK_SECRET` 的密钥。

create 事件启动 post-check；comment event 从 HTML 可见正文识别 `JARVIS_MENTION_NAMES` command；close/delete 事件终止同一外部 subject 的活跃 Task。评论按评论 ID 去重，不能因投递 ID 改变重复执行；bot 的自身回复被忽略。

## 3. 运行、读取和写回边界

TAPD adapter 支持缺陷/需求/任务创建、评论 command、服务端快照 `issue.json` / `notes.json`、最终评论写回与仓库关联。没有仓库关联时创建合法 zero-workspace Task，绝不把 TAPD project ID 猜成仓库。

服务端负责准备快照和发布结果。Runtime Agent 通过官方 `tapd-cli` 按需读取实时工作项、全部分页评论、关联对象和附件；Jarvis Box 不自动下载全部附件。Docker image 已固定 TAPD CLI；Native 安装见 [TAPD 官方仓库](https://cnb.cool/tapd.cn/skills/tapd-cli)。运行时只给 TAPD Run 注入 `TAPD_CMD`、`TAPD_TOKEN`、`TAPD_API_ENDPOINT`、`TAPD_WORKSPACE_IDS`；服务端 Basic Auth 密码和 webhook secret 不会交给 Agent。

Agent 可用 `attachment by-entity workspaceid=<项目ID> entry-id=<工作项ID>` 查询附件，使用 `attachment download` 取得短期链接下载到当前 Run，正文图片用 `attachment get-image`。读不到工具、令牌或权限时必须说明失败，不能解释为没有附件。Agent 不直接发布评论；其 CLI 身份的实际权限仍由令牌决定，prompt 的只读约束不是权限沙箱。

Agent 输出 Markdown。adapter 回写时转换为 HTML，支持标题、加粗、列表、表格、代码块和链接；禁用原始 HTML 与危险链接，保留机器人回写标记，且不改写已有评论。
