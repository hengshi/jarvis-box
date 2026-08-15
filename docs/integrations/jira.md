# Jira 接入

Jira 是 work-item provider，与飞书项目、GitLab Issues 和 GitHub Issues 位于同一逻辑层。Jira issue 本身不隐含代码仓库所属；operator 可以为一个 Jira project 关联零个、一个或多个 GitLab/GitHub 仓库。

## 当前支持

| 能力 | 状态 |
| --- | --- |
| issue-created webhook | 已支持 |
| issue 状态进入 Done category / issue deleted | 先持久化创建时绑定到该 Jira issue 的精确 Task 快照，再终态化并清理登记 Workspace；retry 只重放该快照 |
| 按 Jira project allowlist 过滤 | 已支持 |
| 按 issue type 过滤 | 已支持 |
| Jira project 到 GitLab/GitHub 仓库关联 | 已支持，可同时关联多个 |
| Jira 评论写回 | 通过 `jira` CLI 可配置 |
| Jira `@jarvis` command lane | 已支持 `comment_created` 精确事件、评论去重、author allowlist、bot/self ignore，以及 Agent 通过 `JIRA_CMD` 实时读取 issue、完整评论历史和附件清单 |

## 配置运行时 env

```bash
JIRA_BASE_URL=https://jira.example.com
JIRA_PROJECTS=APP,OPS
JIRA_ISSUE_TYPES=Bug,故障
JIRA_WEBHOOK_SECRET=<shared-secret>
JIRA_CMD=jira
JIRA_COMMENT_ARGS=issue,comment,add,{key},--body-file,{body_file}
JARVIS_JIRA_COMMAND_ALLOWED_USERS=alice,bob

# JSON 为 provider -> source scope -> repository[]。一个 work item 可同时关联 GitLab 和 GitHub。
JARVIS_WORK_ITEM_REPOSITORIES={"jira":{"APP":[{"provider":"gitlab","project":"group/frontend","base_branch":"main"},{"provider":"github","project":"acme/mobile","base_branch":"main"}],"OPS":[{"provider":"gitlab","project":"group/backend"}]}}
```

JSON 中的 GitLab/GitHub repository 必须分别在 `GITLAB_PROJECTS` / `GITHUB_REPOSITORIES` allowlist 中；Jarvis Box 根据已配置 host 生成 clone URL，不接受配置传入任意 clone endpoint。没有仓库关联时，Jira create/command 仍可以作为 zero-workspace Task 运行和回写原 issue，不会猜测某个 GitLab 项目。旧的 `JIRA_DEFAULT_GITLAB_PROJECT` / `JIRA_GITLAB_PROJECT_MAP` 已移除，存在时服务拒绝启动并给出迁移提示。

若 `GITHUB_REPOSITORIES` 仅用于 Jira 工作项的 Workspace 关联，设置 `JARVIS_GITHUB_WEBHOOK_ENABLED=false`；GitHub webhook endpoint 将返回 `404`，且不要求 `GITHUB_WEBHOOK_SECRET`。

`@jarvis` command 的 webhook payload 只负责触发和提供 issue identity。Jarvis Box 向匹配的 command Agent 注入 `JIRA_CMD`、`INTAKE_JIRA_KEY`、`INTAKE_JIRA_URL` 与 `INTAKE_JIRA_PROJECT`，并要求 Agent 在执行前通过已认证 Jira CLI 读取实时 issue、评论和附件。command Run 不创建伪造的空 `notes.json`；缺少该文件不代表 Jira 没有评论。Agent 只负责生成 `comment.md`，Jarvis Box 负责最终写回。

## 配置 Jira webhook

在 Jira webhook 中发送 issue created、issue updated（包含 changelog）和 issue deleted 事件到：

```text
https://<jarvis-public-url>/webhooks/jira
```

兼容路径 `/jira-webhook` 也可用。

请求头设置：

```text
X-Jira-Token: <JIRA_WEBHOOK_SECRET>
```

Atlassian 风格请求也可以使用 `X-Atlassian-Webhook-Token`。

## 写回 Jira

Jarvis Box 通过可配置 CLI 写回 Jira 评论。默认参数：

```text
jira issue comment add {key} --body-file {body_file}
```

可用占位符：

| 占位符 | 含义 |
| --- | --- |
| `{key}` | Jira issue key，例如 `APP-123` |
| `{body_file}` | Jarvis Box 生成的评论正文文件 |
| `{url}` | Jira issue URL |
| `{project}` | Jira project key |

## 验证

1. 创建测试 Jira bug，例如 `APP-123`，确认只有 create 事件启动自动 post-check。
2. 确认 webhook 返回 accepted 或 ignored reason。
3. 在 issue 评论 `@jarvis 汇总当前证据`，确认 `comment_created` 进入 command lane，而非再次自动 post-check；同时确认 Agent 的 Jira CLI 审计记录包含 live issue/comment read。
4. 在 `/status` 查看 Jira source 的 work item 及全部已关联 workspace。
5. 确认 agent 完成后 Jira issue 获得评论，或 artifact 中记录明确写回失败原因。

Jira 不是 repository host，因此不提供 PR/MR review、follow-up 或 branch 托管能力；这些能力由关联的 GitLab/GitHub 仓库提供。
