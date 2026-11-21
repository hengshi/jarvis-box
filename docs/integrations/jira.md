# Jira 接入

本页面向将 Jira work item 接入 Jarvis Box 的管理员。Jira issue 不自动等同于某个代码仓库；可为一个 Jira project 关联零个、一个或多个已允许的 GitLab/GitHub 仓库，也可以让它以 zero-workspace Task 运行。

鉴权和 JSON 校验成功、投递可靠落盘后，webhook 立即返回 `202 Accepted`。`receipt_id` 表示已受理，而不是 Task 已创建。恢复与重投见[Webhook 受理与恢复](../storage-model.md#webhook-受理与恢复)。

## 支持范围

| 能力 | 行为 |
| --- | --- |
| `issue_created` | 可启动 post-check。 |
| `Done` category 或 issue 删除 | 持久化创建时绑定到该 Jira issue 的精确 Task 快照，再终态化并清理登记 workspace；retry 只重放这个快照。 |
| project allowlist | `JIRA_PROJECTS` 为空时，任何 project 的创建/命令均不受理。 |
| issue type allowlist | `JIRA_ISSUE_TYPES` 未设时只接受 `Bug`；其他 type 被收到后跳过，webhook 仍返回 `200`，并在 work ledger 记录 `jira_issue_type_not_allowed`。类型名大小写不敏感，但可能随触发者语言本地化；稳定 type ID 更可靠。 |
| 评论命令 | 支持精确 `comment_created`、评论去重、author allowlist 与 bot/self ignore。 |
| 原处结果 | 可通过 `jira` CLI 写回评论。 |

Jira 不托管代码，因此不提供 PR/MR review、follow-up 或 branch 托管；需要这些能力时关联 GitLab/GitHub 仓库。

## 配置

将以下值写入当前生效的运行时环境文件，替换示例中的范围和 ID：

```dotenv
JIRA_BASE_URL=https://jira.example.com
JIRA_PROJECTS=APP,OPS
JIRA_ISSUE_TYPES=10003,10005
JIRA_WEBHOOK_SECRET=<shared-secret>
JIRA_CMD=jira
JIRA_COMMENT_ARGS=issue,comment,add,{key},--template,{body_file},--no-input
JARVIS_JIRA_COMMAND_ALLOWED_USERS=

# provider -> source scope -> repository[]；一个 work item 可以关联多个仓库。
JARVIS_WORK_ITEM_REPOSITORIES={"jira":{"APP":[{"provider":"gitlab","project":"group/frontend","base_branch":"main"},{"provider":"github","project":"acme/mobile","base_branch":"main"}],"OPS":[{"provider":"gitlab","project":"group/backend"}]}}
```

首次接入应查询本站实际支持工作项类型的稳定 ID，并把全部需要的 ID 填进 `JIRA_ISSUE_TYPES`。不要复用示例 ID，也不要保留 Bug-only 默认值后误以为 Task/Story 已接通。type 筛选不限制评论 command，但会影响 create event 的 post-check。

关联 JSON 中的 GitLab/GitHub repository 必须已出现在 `GITLAB_PROJECTS` / `GITHUB_REPOSITORIES`。Jarvis Box 从已配 host 生成 clone URL，不接受任意 clone endpoint。若 GitHub 只用于 Jira workspace，设置 `JARVIS_GITHUB_WEBHOOK_ENABLED=false`，GitHub webhook endpoint 返回 `404` 且不需要 `GITHUB_WEBHOOK_SECRET`。旧的 `JIRA_DEFAULT_GITLAB_PROJECT` 与 `JIRA_GITLAB_PROJECT_MAP` 已删除，仍存在时服务会拒绝启动。

`@jarvis` 评论通过 webhook 触发。同一个 Jira Issue 中的后续指令[继续原任务](../execution-model.md#从同一事项继续评论指令)。Agent 会取得 `JIRA_CMD`、`INTAKE_JIRA_KEY`、`INTAKE_JIRA_URL`、`INTAKE_JIRA_PROJECT`，并必须用已认证 Jira CLI 读取实时 issue、完整评论和附件。它只输出 `comment.md`；Jarvis Box 负责最终写回。没有 `notes.json` 不代表 Jira 没有评论。

## 配置 Jira webhook

让 Jira 为 issue created、issue updated（含 changelog）和 issue deleted 发送到：

```text
https://<jarvis-public-url>/webhooks/jira
```

兼容路径 `/jira-webhook` 同样可用。Jira Cloud 管理 webhook 应设置与 `JIRA_WEBHOOK_SECRET` 相同的 Secret，并在 `X-Hub-Signature` 中发送 `sha256=<HMAC>`。Jarvis Box 用原始 request body 验签；有签名但签名无效时不会降级到 token 认证。

能自定义 header 的集成可发送 `X-Jira-Token: <JIRA_WEBHOOK_SECRET>` 或 `X-Atlassian-Webhook-Token`。这两个明文 token 只在没有签名时使用。反向代理必须保留原始 body、签名和 `X-Atlassian-Webhook-Identifier`；去掉投递身份后只能退化为 body 摘要去重，不能证明保留了平台投递 ID。

默认写回命令为：

```text
jira issue comment add {key} --template {body_file} --no-input
```

可用 `{key}`、`{body_file}`、`{url}`、`{project}` 占位符，分别代表 Jira key、Jarvis Box 生成的正文文件、issue URL 和 project key。

## 验证

1. 创建允许类型的测试 issue，例如 `APP-123`，确认只有 create event 启动自动 post-check。
2. 确认 webhook 返回 `202 Accepted`，再从 Status 和 work ledger 检查后台处理或跳过原因。
3. 在 issue 评论 `@jarvis 汇总当前证据`，确认它进入 command lane 而非再次 post-check，并确认 Agent 的 Jira CLI 审计包含实时 issue/comment read。
4. 在 `/status` 检查 Jira source work item 及关联 workspace。
5. 确认结束后原 issue 有评论，或 artifact 中有明确的写回失败原因。
