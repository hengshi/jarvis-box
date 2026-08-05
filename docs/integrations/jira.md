# Jira 接入

Jira provider loop 当前定位为 bug bridge：Jira 创建的 bug issue 进入 Jarvis Box，Jarvis Box 选择候选 GitLab 代码交付项目，再由 agent 判断复现、修复、更新 MR 或阻塞等待证据。

## 当前支持

| 能力 | 状态 |
| --- | --- |
| issue-created webhook | 已支持 |
| issue 状态进入 Done category / issue deleted | 先持久化创建时绑定到该 Jira issue 的精确 Task 快照，再终态化并清理登记 Workspace；retry 只重放该快照 |
| 按 Jira project allowlist 过滤 | 已支持 |
| 按 issue type 过滤 | 已支持 |
| Jira project 到 GitLab project 映射 | 已支持 |
| Jira 评论写回 | 通过 `jira` CLI 可配置 |
| Jira `@jarvis` command lane | 尚未内置 |

## 配置运行时 env

```bash
JIRA_BASE_URL=https://jira.example.com
JIRA_PROJECTS=APP,OPS
JIRA_ISSUE_TYPES=Bug,故障
JIRA_GITLAB_PROJECT_MAP=APP=group/frontend,OPS=group/backend
JIRA_WEBHOOK_SECRET=<shared-secret>
JIRA_CMD=jira
JIRA_COMMENT_ARGS=issue,comment,add,{key},--body-file,{body_file}
```

如果没有 `JIRA_GITLAB_PROJECT_MAP`，Jarvis Box 会使用 `GITLAB_PROJECTS` 作为候选代码交付项目。候选项目为空时，Jira webhook 会被跳过。

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

1. 创建测试 Jira bug，例如 `APP-123`。
2. 确认 webhook 返回 accepted 或 ignored reason。
3. 在 `/status` 查看 Jira source 的 work item。
4. 确认 agent 完成后 Jira issue 获得评论，或 artifact 中记录明确写回失败原因。

## 限制

Jira 还不是通用 command provider。当前不会因为 Jira 评论里出现 `@jarvis` 就进入 command lane。要支持这个能力，需要新增 Jira comment webhook adapter、comment 去重、command parser 和 Jira comment writeback 的完整闭环。
