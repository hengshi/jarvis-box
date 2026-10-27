# TAPD 接入

鉴权及 JSON 校验成功、投递可靠落盘后，Webhook 立即返回 `202 Accepted`，不等待业务读取、Git 操作或 Agent 启动。响应中的 `receipt_id` 只标识投递受理，不表示 Task 已创建；后台处理和重投规则见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

Jarvis Box 可以接收 TAPD 工作项 webhook，把缺陷/需求/任务映射成统一的 work item，执行 post-check 或 `@jarvis` command，并把最终 `comment.md` 回写到同一个 TAPD 工作项。

## 配置

| 变量 | 必填 | 用途 |
| --- | --- | --- |
| `TAPD_WEBHOOK_SECRET` | webhook 必填 | 与 TAPD webhook body 中的 `secret`/`token` 或 header token 匹配的共享密钥。 |
| `TAPD_CMD` | 否 | runtime agent 使用的官方 `tapd-cli`，默认 `tapd-cli`，需安装并可执行。 |
| `TAPD_TOKEN` | webhook 必填（除非已配置 `TAPD_API_TOKEN`） | 官方 CLI 个人令牌；未设置时使用 `TAPD_API_TOKEN`。Basic Auth 不能替代 CLI 个人令牌。 |
| `TAPD_API_TOKEN` | 二选一 | TAPD API bearer token。 |
| `TAPD_API_USER` / `TAPD_API_PASSWORD` | 二选一 | TAPD API basic auth 账号和密码。 |
| `TAPD_ALLOWED_WORKSPACES` | 否 | 逗号分隔的 workspace id；为空时允许全部 workspace。 |
| `TAPD_API_BASE_URL` | 否 | 默认 `https://api.tapd.cn`。 |
| `TAPD_BASE_URL` | 否 | 默认 `https://www.tapd.cn`，用于生成工作项页面链接。 |
| `JARVIS_TAPD_COMMAND_ALLOWED_USERS` | 否 | 允许使用 mention command 的用户标识；为空时允许所有非 bot 用户。 |
| `JARVIS_WORK_ITEM_REPOSITORIES` | 否 | provider-neutral work-item 到 GitLab/GitHub 仓库关联 JSON。 |

示例：

```dotenv
TAPD_WEBHOOK_SECRET=<random-secret>
TAPD_API_USER=<tapd-api-user>
TAPD_API_PASSWORD=<tapd-api-password>
TAPD_TOKEN=<tapd-personal-token>
TAPD_ALLOWED_WORKSPACES=12345678
JARVIS_TAPD_COMMAND_ALLOWED_USERS=alice,bob
```

启用 webhook 时，必须同时具备服务端 API 身份和可供 CLI 使用的令牌。仅配置 Basic Auth 会在启动或保存配置时被拒绝。服务地址只接受不含用户名、密码、查询参数或片段的 HTTP(S) 地址。

## Webhook

配置 TAPD webhook 请求地址：

- `https://<jarvis-box-host>/webhooks/tapd`
- 兼容入口：`https://<jarvis-box-host>/tapd-webhook`

Jarvis Box 接受 body token 和 header token 两类鉴权来源。body 字段支持 `secret`、`token`、`header.token`；header 支持 `X-TAPD-Token`、`X-Webhook-Token`。请求被持久化前会删除 body 中的 `secret`、`token`、`sign`、`signature` 字段。

TAPD 配置页面的 URL 连通性检测发送仅含 `test` 字段的 JSON 对象或空数组 `[]`。这两种请求在不携带事件头、鉴权头时返回 HTTP 200，不进入事件处理、不创建任务；正式事件仍必须携带与 `TAPD_WEBHOOK_SECRET` 匹配的密钥。

工作项 identity 读取 `workspace_id` / `workspaceId`；创建事件读取 `id`，评论事件读取所属对象字段 `entity_id`。API 评论对象中的同一关联字段名为 `entry_id`。`event` / `event_type` 中包含 `create` 时启动 post-check，包含 `comment` 时按 `JARVIS_MENTION_NAMES` 识别 command，包含 `close` / `delete` 时终止同一外部 subject 下的活跃 Task。

工作项类型从 `entity_type`、工作项类型字段或 `bug::` / `story::` / `task::` 事件前缀识别，决定读取与评论回写的对象类型。未配置关联代码仓库时，以零工作区启动，不把 TAPD 项目 ID 当作代码仓库。

评论 webhook 的扁平字段中，`id` 是评论 ID，`entity_id` 是所属工作项 ID（API 评论对象对应 `entry_id`）；类型读取 `entry_type` 或 `story_comment::` / `bug_comment::` / `task_comment::` 事件前缀。正文读取 `description`，从 HTML 中提取可见文字后识别命令；属性、引用和代码块中的 mention 不触发任务。评论按评论 ID 排重，不因投递 ID 改变而重复执行；作者 `author` 用于识别并忽略机器人自身回复。

评论 API 的 `entry_type` 使用 TAPD 要求的 `bug`、`stories`、`tasks`，与工作项内部类型分别对应；结果评论的 `author` 为 `jarvis`。

## 能力边界

TAPD adapter 支持：

- 缺陷/需求/任务工作项创建事件触发 post-check；
- 工作项评论中的 `@jarvis` command；
- 服务端读取当前工作项和评论，写入 `issue.json` / `notes.json`；
- 服务端回写最终评论；
- 通过 `JARVIS_WORK_ITEM_REPOSITORIES` 关联 GitLab/GitHub workspace。

服务端继续准备 `issue.json`、`notes.json`，并负责最终评论发布。runtime agent 通过官方 `tapd-cli` 按需读取实时工作项、完整分页评论、关联对象和附件；Jarvis Box 不自动下载全部附件。

Docker runtime base 预装固定版本的 TAPD CLI，客户部署仅配置令牌；Native 模式安装 CLI 请参照 [TAPD 官方仓库](https://cnb.cool/tapd.cn/skills/tapd-cli)。个人令牌在 [个人设置](https://www.tapd.cn/personal_settings/index?tab=personal_token) 获取。Jarvis Box 仅向 TAPD Run 注入 `TAPD_CMD`、`TAPD_TOKEN`、`TAPD_API_ENDPOINT` 和 `TAPD_WORKSPACE_IDS`；服务端 Basic Auth 密码、webhook 密钥不交付给 Agent。

Agent 用 `attachment by-entity workspaceid=<项目ID> entry-id=<工作项ID>` 查询附件，不指定 type 以保留评论附件；`attachment download` 返回短期下载链接，由 Agent 下载到当前 Run 目录并读取。正文图片使用 `attachment get-image`。缺少工具、令牌或权限时应明确报告，不能把读取失败解释成没有附件。Agent 不直接修改平台或发布评论。CLI 身份本身的权限由令牌决定；prompt 的只读约束不是权限沙箱。

## 评论格式

Agent 统一输出 Markdown。TAPD adapter 在回写时转换为 HTML，支持标题、加粗、列表、表格、代码块和链接；禁用原始 HTML 与危险链接，保留机器人回写标记。已有评论不会自动改写。
